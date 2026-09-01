"""Write and reopen a planner job TOML from a device record plus defaults."""

import os
import sys
import tempfile
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from parch import ConfigError
from parch.config import load
from parch.devices import DEVICES, get_device, known_device_ids
from parch.services.job_file import (
    CANONICAL_SECTIONS,
    DEFAULT_FROM,
    JobSpec,
    _PAPERS,
    _WEEK_RAIL_NONE,
    _WEEK_RAIL_OMIT,
    emit_job,
    spec_from_data,
    spec_from_device,
    with_overrides,
)

_CANONICAL_SET = frozenset(CANONICAL_SECTIONS)


def device_help() -> str:
    return ", ".join(device.name for device in DEVICES)


def shipped_help() -> str:
    """Help label for known devices (no lined siblings)."""
    return device_help()


def _unknown_device(spec: str) -> ConfigError:
    names = ", ".join(known_device_ids())
    return ConfigError(f"unknown device {spec!r}; expected a device id ({names})")


def _packaged_or_path(spec: str) -> Path | str:
    given = Path(spec)
    if given.is_file():
        return given
    try:
        return get_device(spec).id
    except KeyError:
        raise _unknown_device(spec) from None


@contextmanager
def open_resolved(spec: str) -> Iterator[Path]:
    """Yield a live path for a job file or a device id (temp complete job)."""
    resolved = _packaged_or_path(spec)
    if isinstance(resolved, Path):
        yield resolved
        return
    tmp: Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(suffix=".toml")
        tmp = Path(tmp_name)
        try:
            handle = os.fdopen(fd, "w", encoding="utf-8")
        except Exception:
            os.close(fd)
            raise
        with handle:
            handle.write(emit_job(spec_from_device(resolved)))
        yield tmp
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def parse_sections(raw: str) -> list[str]:
    names = [part.strip() for part in raw.split(",") if part.strip()]
    if not names:
        raise ConfigError("sections must be non-empty")
    for name in names:
        if name not in _CANONICAL_SET:
            raise ConfigError(f"unknown section: {name}")
    selected = set(names)
    return [name for name in CANONICAL_SECTIONS if name in selected]


def run_new(
    *,
    outfile: str | Path | None,
    from_profile: str | None,
    year: int | None,
    sections: str | None,
    yes: bool,
    force: bool,
    hand: str | None = None,
) -> int:
    interactive = (not yes) and sys.stdin.isatty()

    if from_profile is None and interactive:
        from_profile = _prompt_device()
    if from_profile is None:
        from_profile = DEFAULT_FROM
    if Path(from_profile).is_file():
        raise ConfigError("--from is a device id, not a job file; use parch edit to reopen a file")
    try:
        spec = spec_from_device(from_profile)
    except KeyError as exc:
        raise _unknown_device(from_profile) from exc

    if year is None and interactive:
        year = _prompt_year(spec.year)
    if year is None:
        year = spec.year
    if not (isinstance(year, int) and not isinstance(year, bool) and 1 <= year <= 9999):
        raise ConfigError("year must be between 1 and 9999")
    spec.year = year

    if sections is not None:
        spec.sections = parse_sections(sections)
    elif interactive:
        spec.sections = _prompt_sections(spec.resolved_sections())

    dest = _coerce_outfile(outfile)
    if dest is None and interactive:
        dest = _prompt_outfile()
    if dest is None:
        raise ConfigError("outfile is required with --yes (or when stdin is not a TTY)")

    if dest.exists() and not force:
        raise ConfigError(f"{dest} already exists (use --force to overwrite)")

    extras: dict[str, Any] = {}
    if interactive:
        extras = _prompt_overlays(spec, hand=hand)
        if hand is None:
            hand = extras.pop("hand", None)
    if hand is not None:
        extras["hand"] = hand.lower()
        if extras["hand"] not in {"left", "right"}:
            raise ConfigError("hand: expected left or right")
    spec = with_overrides(spec, **extras)
    return _write_job(dest, spec)


def run_edit(*, infile: str | Path, hand: str | None = None) -> int:
    """Reopen a job file in Questionary and write complete resume state back."""
    if not sys.stdin.isatty():
        raise ConfigError("parch edit needs a TTY")
    dest = _coerce_outfile(infile)
    if dest is None or not dest.is_file():
        raise ConfigError(f"{infile}: job file not found")
    _text, data = _read_source(dest)
    try:
        spec = spec_from_data(data)
    except KeyError as exc:
        raise ConfigError(str(exc)) from exc
    spec.year = _prompt_year(spec.year)
    spec.sections = _prompt_sections(spec.resolved_sections())
    extras = _prompt_overlays(spec, hand=hand)
    if hand is None:
        hand = extras.pop("hand", None)
    if hand is not None:
        extras["hand"] = hand.lower()
        if extras["hand"] not in {"left", "right"}:
            raise ConfigError("hand: expected left or right")
    spec = with_overrides(spec, **extras)
    return _write_job(dest, spec)


def _write_job(dest: Path, spec: JobSpec) -> int:
    written = emit_job(spec)
    tmp: Path | None = None
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=dest.parent, suffix=".toml")
        tmp = Path(tmp_name)
        try:
            handle = os.fdopen(fd, "w", encoding="utf-8")
        except Exception:
            os.close(fd)
            raise
        with handle:
            handle.write(written)
        load(tmp)
        tmp.replace(dest)
    except OSError as exc:
        raise ConfigError(f"{dest}: {exc}") from exc
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    print(f"Wrote {dest}")
    return 0


def _read_source(path: Path) -> tuple[str, dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: expected a TOML table")
    return text, data


def _coerce_outfile(outfile: str | Path | None) -> Path | None:
    if outfile is None:
        return None
    text = str(outfile).strip()
    if not text:
        return None
    return Path(text).expanduser()


def _coerce_paper(paper: str) -> str:
    lowered = paper.lower()
    if lowered not in _PAPERS:
        raise ConfigError("paper: expected dotted or lined")
    return lowered


def _prompt_overlays(spec: JobSpec, *, hand: str | None) -> dict[str, Any]:
    """Questionary overlays for existing keys. No title_height / daily_cell_height."""
    overlays: dict[str, Any] = {}
    if hand is None:
        overlays["hand"] = _prompt_side_menu(spec.hand)
    overlays["paper"] = _prompt_paper(spec.paper)
    names = set(spec.resolved_sections())
    if "monthly" in names:
        overlays["week_placement"] = _prompt_week_rail(spec.week_placement)
    if "daily" in names:
        overlays["hour_from"], overlays["hour_to"] = _prompt_hours(spec.hour_from, spec.hour_to)
        overlays["priorities_count"] = _prompt_positive_int("Priority rows", spec.priorities_count)
    if "daily_notes" in names:
        overlays["daily_notes_pages"] = _prompt_positive_int(
            "Daily notes pages", spec.daily_notes_pages
        )
    if "projects" in names:
        overlays["projects_pages"] = _prompt_positive_int("Project pages", spec.projects_pages)
        overlays["projects_card_rows"] = _prompt_positive_int(
            "Project card rows", spec.projects_card_rows
        )
    if "habits" in names:
        minimum = max(1, spec.habit_names_len)
        overlays["habit_columns"] = _prompt_positive_int(
            "Habit columns", spec.habit_columns, minimum=minimum
        )
    if "meetings" in names:
        overlays["meetings_index_pages"] = _prompt_positive_int(
            "Meeting index pages", spec.meetings_index_pages
        )
    return overlays


def _prompt_side_menu(default: str) -> str:
    questionary = _questionary()
    answer = questionary.select(
        "MOS side",
        choices=["left", "right"],
        default=default,
    ).ask()
    if answer is None:
        raise ConfigError("cancelled")
    side = str(answer).lower()
    if side not in {"left", "right"}:
        raise ConfigError("hand: expected left or right")
    return side


def _prompt_paper(default: str) -> str:
    questionary = _questionary()
    answer = questionary.select(
        "Paper",
        choices=["dotted", "lined"],
        default=default,
    ).ask()
    if answer is None:
        raise ConfigError("cancelled")
    return _coerce_paper(str(answer))


def _prompt_week_rail(default: str) -> str:
    questionary = _questionary()
    answer = questionary.select(
        "Week rail",
        choices=[
            questionary.Choice("Keep (seated from MOS side)", value=_WEEK_RAIL_OMIT),
            questionary.Choice("None", value=_WEEK_RAIL_NONE),
        ],
        default=_WEEK_RAIL_OMIT if default != _WEEK_RAIL_NONE else _WEEK_RAIL_NONE,
    ).ask()
    if answer is None:
        raise ConfigError("cancelled")
    choice = str(answer).lower()
    if choice not in {_WEEK_RAIL_NONE, _WEEK_RAIL_OMIT}:
        raise ConfigError("week_placement: none or omit")
    return choice


def _prompt_hours(default_from: int, default_to: int) -> tuple[int, int]:
    hour_from = _prompt_int("Hour from", default_from)

    def _range(text: str) -> bool | str:
        try:
            value = int(text.strip())
        except ValueError:
            return "hour_to must be an integer"
        if value <= hour_from:
            return "hour_from must be < hour_to"
        return True

    questionary = _questionary()
    answer = questionary.text("Hour to", default=str(default_to), validate=_range).ask()
    if answer is None:
        raise ConfigError("cancelled")
    hour_to = int(answer.strip())
    if hour_from >= hour_to:
        raise ConfigError("hour_from must be < hour_to")
    return hour_from, hour_to


def _prompt_int(message: str, default: int) -> int:
    questionary = _questionary()

    def _ok(text: str) -> bool | str:
        try:
            int(text.strip())
        except ValueError:
            return f"{message} must be an integer"
        return True

    answer = questionary.text(message, default=str(default), validate=_ok).ask()
    if answer is None:
        raise ConfigError("cancelled")
    return int(answer.strip())


def _prompt_positive_int(message: str, default: int, *, minimum: int = 1) -> int:
    questionary = _questionary()

    def _ok(text: str) -> bool | str:
        try:
            value = int(text.strip())
        except ValueError:
            return f"{message} must be an integer"
        if value < minimum:
            return f"{message} must be at least {minimum}"
        return True

    answer = questionary.text(message, default=str(default), validate=_ok).ask()
    if answer is None:
        raise ConfigError("cancelled")
    return int(answer.strip())


def _prompt_device() -> str:
    questionary = _questionary()
    answer = questionary.select(
        "Device",
        choices=[questionary.Choice(title=device.name, value=device.id) for device in DEVICES],
        default=DEFAULT_FROM,
    ).ask()
    if answer is None:
        raise ConfigError("cancelled")
    return str(answer)


def _prompt_year(default: int) -> int:
    questionary = _questionary()

    def _ok(text: str) -> bool | str:
        try:
            value = int(text.strip())
        except ValueError:
            return "year must be an integer"
        if value < 1 or value > 9999:
            return "year must be between 1 and 9999"
        return True

    answer = questionary.text("Year", default=str(default), validate=_ok).ask()
    if answer is None:
        raise ConfigError("cancelled")
    return int(answer.strip())


def _prompt_sections(source: list[str]) -> list[str]:
    questionary = _questionary()
    checked = set(source)

    def _ok(picked: list[str]) -> bool | str:
        return True if picked else "pick at least one section"

    answer = questionary.checkbox(
        "Sections",
        choices=[
            questionary.Choice(name, checked=name in checked) for name in CANONICAL_SECTIONS
        ],
        validate=_ok,
    ).ask()
    if answer is None:
        raise ConfigError("cancelled")
    selected = set(answer)
    return [name for name in CANONICAL_SECTIONS if name in selected]


def _prompt_outfile() -> Path:
    questionary = _questionary()
    answer = questionary.path("Output path").ask()
    if answer is None:
        raise ConfigError("cancelled")
    dest = _coerce_outfile(answer)
    if dest is None:
        raise ConfigError("outfile is required")
    return dest


def _questionary() -> Any:
    try:
        import questionary
    except ImportError as exc:
        raise ConfigError("questionary is required for interactive parch new") from exc
    return questionary
