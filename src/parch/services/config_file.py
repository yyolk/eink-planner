"""Write a planner TOML by copying a shipped profile and overlaying fields."""

import os
import re
import sys
import tempfile
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from parch import ConfigError
from parch.config import load

DEFAULT_FROM = "supernote-nomad"

# Wizard + help labels (not stems). --from still takes a stem or path.
SHIPPED_PROFILES: tuple[tuple[str, str], ...] = (
    ("SuperNote Nomad", "supernote-nomad"),
    ("SuperNote Nomad (left-handed)", "supernote-nomad-mos-right"),
    ("Kindle Scribe", "kindle-scribe"),
    ("158×210", "158x210-mos-left"),
    ("158×210 lined", "158x210-mos-left-lined"),
    ("158×210 (left-handed)", "158x210-mos-right"),
)

CANONICAL_SECTIONS: tuple[str, ...] = (
    "cover",
    "index",
    "annual",
    "quarterly",
    "monthly",
    "weekly",
    "daily",
    "daily_notes",
    "projects",
    "habits",
    "review",
    "tasks",
    "meetings",
    "colophon",
)

_CANONICAL_SET = frozenset(CANONICAL_SECTIONS)
_YEAR_TITLE = re.compile(r"^\d{4}$")
_CALENDAR_TABLE = re.compile(
    r"(?ms)^[ \t]*\[[ \t]*calendar[ \t]*\][ \t]*(#[^\n]*)?\n(?:(?!^[ \t]*\[).)*"
)
_COVER_TABLE = re.compile(
    r"(?ms)^[ \t]*\[[ \t]*section\.cover[ \t]*\][ \t]*(#[^\n]*)?\n(?:(?!^[ \t]*\[).)*"
)
_SECTIONS_ARRAY = re.compile(r"(?ms)^[ \t]*sections\s*=\s*\[.*?\]")
_YEAR_ASSIGN = re.compile(r"(?m)^[ \t]*year\s*=\s*\d+")
_TITLE_ASSIGN = re.compile(r'(?m)^[ \t]*title\s*=\s*"([^"]*)"')


def shipped_help() -> str:
    return ", ".join(label for label, _stem in SHIPPED_PROFILES)


def _unknown_profile(spec: str) -> ConfigError:
    names = ", ".join(stem for _label, stem in SHIPPED_PROFILES)
    return ConfigError(
        f"unknown profile {spec!r}; expected a path or shipped name ({names})"
    )


def _packaged_config(spec: str):
    given = Path(spec)
    if given.is_file():
        return given
    resource = files("parch.data") / "configs" / f"{spec}.toml"
    if not resource.is_file():
        raise _unknown_profile(spec)
    return resource


@contextmanager
def open_resolved(spec: str) -> Iterator[Path]:
    """Yield a live path for spec; zip temps stay open through the with."""
    resource = _packaged_config(spec)
    if isinstance(resource, Path):
        yield resource
        return
    with as_file(resource) as path:
        yield Path(path)


def resolve_from(spec: str) -> Path:
    """Resolve spec as an existing path, else a disk-backed packaged config."""
    resource = _packaged_config(spec)
    if isinstance(resource, Path):
        return resource
    raise ConfigError(
        f"profile {spec!r} is zip-backed; use open_resolved to keep the temp file alive"
    )


def parse_sections(raw: str) -> list[str]:
    names = [part.strip() for part in raw.split(",") if part.strip()]
    if not names:
        raise ConfigError("sections must be non-empty")
    for name in names:
        if name not in _CANONICAL_SET:
            raise ConfigError(f"unknown section: {name}")
    selected = set(names)
    return [name for name in CANONICAL_SECTIONS if name in selected]


def overlay_toml(
    text: str,
    *,
    year: int | None = None,
    sections: list[str] | None = None,
    source_sections: list[str] | None = None,
) -> str:
    """Copy source text and surgically overlay year / cover title / sections."""
    if year is not None:
        text = _replace_calendar_year(text, year)
        text = _replace_cover_title_year(text, year)
    if sections is not None and sections != source_sections:
        text = _replace_sections(text, sections)
    return text


def run_new(
    *,
    outfile: str | Path | None,
    from_profile: str | None,
    year: int | None,
    sections: str | None,
    yes: bool,
    force: bool,
) -> int:
    interactive = (not yes) and sys.stdin.isatty()

    if from_profile is None and interactive:
        from_profile = _prompt_profile()
    if from_profile is None:
        from_profile = DEFAULT_FROM

    with open_resolved(from_profile) as source:
        text, data = _read_source(source)
    source_year = _year_from_data(data)
    source_sections = _sections_from_data(data)

    if year is None and interactive:
        year = _prompt_year(source_year)
    if year is None:
        year = source_year
    if year is not None and not (
        isinstance(year, int) and not isinstance(year, bool) and 1 <= year <= 9999
    ):
        raise ConfigError("year must be between 1 and 9999")

    chosen_sections: list[str] | None
    if sections is not None:
        chosen_sections = parse_sections(sections)
    elif interactive:
        chosen_sections = _prompt_sections(source_sections)
    else:
        chosen_sections = None

    dest = _coerce_outfile(outfile)
    if dest is None and interactive:
        dest = _prompt_outfile()
    if dest is None:
        raise ConfigError("outfile is required with --yes (or when stdin is not a TTY)")

    if dest.exists() and not force:
        raise ConfigError(f"{dest} already exists (use --force to overwrite)")

    written = overlay_toml(
        text,
        year=year,
        sections=chosen_sections,
        source_sections=source_sections,
    )
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


def _year_from_data(data: dict[str, Any]) -> int:
    calendar = data.get("calendar")
    if isinstance(calendar, dict):
        raw = calendar.get("year")
        if isinstance(raw, int) and not isinstance(raw, bool) and 1 <= raw <= 9999:
            return raw
    return date.today().year


def _sections_from_data(data: dict[str, Any]) -> list[str]:
    raw = data.get("sections")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, str)]


def _coerce_outfile(outfile: str | Path | None) -> Path | None:
    if outfile is None:
        return None
    text = str(outfile).strip()
    if not text:
        return None
    return Path(text).expanduser()


def _replace_calendar_year(text: str, year: int) -> str:
    def repl_block(match: re.Match[str]) -> str:
        block = match.group(0)
        new_block, n = _YEAR_ASSIGN.subn(f"year = {year}", block, count=1)
        if n:
            return new_block
        if block.endswith("\n"):
            return f"{block}year = {year}\n"
        return f"{block}\nyear = {year}\n"

    new_text, n = _CALENDAR_TABLE.subn(repl_block, text, count=1)
    if n:
        return new_text
    new_text, n = _YEAR_ASSIGN.subn(f"year = {year}", text, count=1)
    return new_text if n else text


def _replace_cover_title_year(text: str, year: int) -> str:
    def repl_block(match: re.Match[str]) -> str:
        block = match.group(0)

        def repl_title(title_match: re.Match[str]) -> str:
            if _YEAR_TITLE.fullmatch(title_match.group(1)):
                return f'title = "{year}"'
            return title_match.group(0)

        return _TITLE_ASSIGN.sub(repl_title, block, count=1)

    new_text, n = _COVER_TABLE.subn(repl_block, text, count=1)
    return new_text if n else text


def _replace_sections(text: str, names: list[str]) -> str:
    inner = "\n".join(f'  "{name}",' for name in names)
    formatted = f"sections = [\n{inner}\n]"
    new_text, n = _SECTIONS_ARRAY.subn(formatted, text, count=1)
    if n:
        return new_text
    return f"{formatted}\n\n{text}"


def _prompt_profile() -> str:
    questionary = _questionary()
    answer = questionary.select(
        "Starting profile",
        choices=[
            questionary.Choice(title=label, value=stem) for label, stem in SHIPPED_PROFILES
        ],
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

