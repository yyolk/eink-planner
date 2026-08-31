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
    ("SuperNote Nomad lined", "supernote-nomad-lined"),
    ("Kindle Scribe", "kindle-scribe"),
    ("Kindle Scribe lined", "kindle-scribe-lined"),
    ("158×210", "158x210"),
    ("158×210 lined", "158x210-lined"),
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
_MOS_TABLE = re.compile(
    r"(?ms)^[ \t]*\[[ \t]*mos[ \t]*\][ \t]*(#[^\n]*)?\n(?:(?!^[ \t]*\[).)*"
)
_STYLE_TABLE = re.compile(
    r"(?ms)^[ \t]*\[[ \t]*style[ \t]*\][ \t]*(#[^\n]*)?\n(?:(?!^[ \t]*\[).)*"
)
_MONTHLY_TABLE = re.compile(
    r"(?ms)^[ \t]*\[[ \t]*section\.monthly[ \t]*\][ \t]*(#[^\n]*)?\n(?:(?!^[ \t]*\[).)*"
)
_DAILY_NOTES_TABLE = re.compile(
    r"(?ms)^[ \t]*\[[ \t]*section\.daily_notes[ \t]*\][ \t]*(#[^\n]*)?\n(?:(?!^[ \t]*\[).)*"
)
_PROJECTS_TABLE = re.compile(
    r"(?ms)^[ \t]*\[[ \t]*section\.projects[ \t]*\][ \t]*(#[^\n]*)?\n(?:(?!^[ \t]*\[).)*"
)
_HABITS_TABLE = re.compile(
    r"(?ms)^[ \t]*\[[ \t]*section\.habits[ \t]*\][ \t]*(#[^\n]*)?\n(?:(?!^[ \t]*\[).)*"
)
_MEETINGS_TABLE = re.compile(
    r"(?ms)^[ \t]*\[[ \t]*section\.meetings[ \t]*\][ \t]*(#[^\n]*)?\n(?:(?!^[ \t]*\[).)*"
)
_SCHEDULE_TABLE = re.compile(
    r"(?ms)^[ \t]*\[[ \t]*section\.daily\.[^\n\]]*\.schedule[ \t]*\][ \t]*(#[^\n]*)?\n(?:(?!^[ \t]*\[).)*"
)
_PRIORITIES_TABLE = re.compile(
    r"(?ms)^[ \t]*\[[ \t]*section\.daily\.[^\n\]]*\.priorities[ \t]*\][ \t]*(#[^\n]*)?\n(?:(?!^[ \t]*\[).)*"
)
_SIDE_MENU_ASSIGN = re.compile(r'(?m)^[ \t]*side_menu\s*=\s*"[^"]*"')
_SCRATCH_PAD_ASSIGN = re.compile(r'(?m)^[ \t]*scratch_pad\s*=\s*"[^"]*"')
_WEEK_PLACEMENT_ASSIGN = re.compile(r'(?m)^[ \t]*week_placement\s*=\s*"[^"]*"')
_WEEK_PLACEMENT_LINE = re.compile(
    r"(?m)^[ \t]*week_placement\s*=\s*\"[^\"]*\"[ \t]*(#[^\n]*)?\n?"
)
_PATTERN_ASSIGN = re.compile(r'(?m)^[ \t]*pattern\s*=\s*"[^"]*"')
_STYLE_NESTED = re.compile(r"(?m)^[ \t]*\[[ \t]*style\.")
_PAPERS = frozenset({"dotted", "lined"})
_WEEK_RAIL_NONE = "none"
_WEEK_RAIL_OMIT = "omit"


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
    hand: str | None = None,
    paper: str | None = None,
    week_placement: str | None = None,
    hour_from: int | None = None,
    hour_to: int | None = None,
    priorities_count: int | None = None,
    daily_notes_pages: int | None = None,
    projects_pages: int | None = None,
    projects_card_rows: int | None = None,
    habit_columns: int | None = None,
    meetings_index_pages: int | None = None,
) -> str:
    """Copy source text and surgically overlay keys. Does not dump a new file."""
    if year is not None:
        text = _replace_calendar_year(text, year)
        text = _replace_cover_title_year(text, year)
    if sections is not None and sections != source_sections:
        text = _replace_sections(text, sections)
    if hand is not None:
        text = _replace_mos_side_menu(text, hand)
    if paper is not None:
        text = _replace_paper(text, paper)
    if week_placement is not None:
        text = _replace_week_placement(text, week_placement)
    if hour_from is not None or hour_to is not None:
        text = _replace_hours(text, hour_from=hour_from, hour_to=hour_to)
    if priorities_count is not None:
        text = _replace_int_in_tables(
            text, _PRIORITIES_TABLE, "count", priorities_count
        )
    if daily_notes_pages is not None:
        text = _replace_int_in_table(
            text, _DAILY_NOTES_TABLE, "section.daily_notes", "pages", daily_notes_pages
        )
    if projects_pages is not None:
        text = _replace_int_in_table(
            text, _PROJECTS_TABLE, "section.projects", "pages", projects_pages
        )
    if projects_card_rows is not None:
        text = _replace_int_in_table(
            text, _PROJECTS_TABLE, "section.projects", "card_rows", projects_card_rows
        )
    if habit_columns is not None:
        text = _replace_int_in_table(
            text, _HABITS_TABLE, "section.habits", "habit_columns", habit_columns
        )
    if meetings_index_pages is not None:
        text = _replace_int_in_table(
            text,
            _MEETINGS_TABLE,
            "section.meetings",
            "index_pages",
            meetings_index_pages,
        )
    return text


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

    extras: dict[str, Any] = {}
    if interactive:
        extras = _prompt_overlays(
            data,
            chosen_sections if chosen_sections is not None else source_sections,
            hand=hand,
        )
        if hand is None:
            hand = extras.pop("hand", None)

    written = overlay_toml(
        text,
        year=year,
        sections=chosen_sections,
        source_sections=source_sections,
        hand=hand,
        **extras,
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


def _replace_mos_side_menu(text: str, hand: str) -> str:
    side = hand.lower()
    if side not in {"left", "right"}:
        raise ConfigError("hand: expected left or right")

    def repl_block(match: re.Match[str]) -> str:
        block = match.group(0)
        new_block, n = _SIDE_MENU_ASSIGN.subn(f'side_menu = "{side}"', block, count=1)
        if n:
            return new_block
        if block.endswith("\n"):
            return f'{block}side_menu = "{side}"\n'
        return f'{block}\nside_menu = "{side}"\n'

    new_text, n = _MOS_TABLE.subn(repl_block, text, count=1)
    if n:
        return new_text
    new_text, n = _SIDE_MENU_ASSIGN.subn(f'side_menu = "{side}"', text, count=1)
    return new_text if n else text


def _replace_sections(text: str, names: list[str]) -> str:
    inner = "\n".join(f'  "{name}",' for name in names)
    formatted = f"sections = [\n{inner}\n]"
    new_text, n = _SECTIONS_ARRAY.subn(formatted, text, count=1)
    if n:
        return new_text
    return f"{formatted}\n\n{text}"


def _append_line(block: str, line: str) -> str:
    stripped = block.rstrip("\n")
    trailing = block[len(stripped) :]
    extra = trailing[1:] if trailing else "\n"
    return f"{stripped}\n{line}\n{extra}"


def _append_table(text: str, name: str, body: str) -> str:
    block = f"[{name}]\n{body}"
    if not block.endswith("\n"):
        block += "\n"
    if text and not text.endswith("\n"):
        text += "\n"
    if text and not text.endswith("\n\n"):
        text += "\n"
    return text + block


def _int_assign(key: str) -> re.Pattern[str]:
    return re.compile(rf"(?m)^[ \t]*{re.escape(key)}\s*=\s*-?\d+")


def _coerce_paper(paper: str) -> str:
    lowered = paper.lower()
    if lowered not in _PAPERS:
        raise ConfigError("paper: expected dotted or lined")
    return lowered


def _replace_paper(text: str, paper: str) -> str:
    paper = _coerce_paper(paper)
    text = _replace_scratch_pad(text, paper)
    return _replace_existing_pattern(text, _DAILY_NOTES_TABLE, paper)


def _replace_scratch_pad(text: str, paper: str) -> str:
    def repl_block(match: re.Match[str]) -> str:
        block = match.group(0)
        new_block, n = _SCRATCH_PAD_ASSIGN.subn(f'scratch_pad = "{paper}"', block, count=1)
        if n:
            return new_block
        return _append_line(block, f'scratch_pad = "{paper}"')

    new_text, n = _STYLE_TABLE.subn(repl_block, text, count=1)
    if n:
        return new_text
    insert = f'[style]\nscratch_pad = "{paper}"\n\n'
    nested = _STYLE_NESTED.search(text)
    if nested:
        return text[: nested.start()] + insert + text[nested.start() :]
    mos = _MOS_TABLE.search(text)
    if mos:
        return text[: mos.start()] + insert + text[mos.start() :]
    return _append_table(text, "style", f'scratch_pad = "{paper}"\n')


def _replace_existing_pattern(text: str, table_re: re.Pattern[str], paper: str) -> str:
    def repl_block(match: re.Match[str]) -> str:
        block = match.group(0)
        new_block, n = _PATTERN_ASSIGN.subn(f'pattern = "{paper}"', block, count=1)
        return new_block if n else block

    return table_re.sub(repl_block, text)


def _replace_week_placement(text: str, week_placement: str) -> str:
    choice = week_placement.lower()
    if choice == _WEEK_RAIL_OMIT:
        return _omit_week_placement(text)
    if choice != _WEEK_RAIL_NONE:
        raise ConfigError("week_placement: none or omit")

    def repl_block(match: re.Match[str]) -> str:
        block = match.group(0)
        new_block, n = _WEEK_PLACEMENT_ASSIGN.subn(
            'week_placement = "none"', block, count=1
        )
        if n:
            return new_block
        return _append_line(block, 'week_placement = "none"')

    new_text, n = _MONTHLY_TABLE.subn(repl_block, text, count=1)
    return new_text if n else text


def _omit_week_placement(text: str) -> str:
    def repl_block(match: re.Match[str]) -> str:
        return _WEEK_PLACEMENT_LINE.sub("", match.group(0), count=1)

    new_text, n = _MONTHLY_TABLE.subn(repl_block, text, count=1)
    return new_text if n else text


def _replace_hours(
    text: str, *, hour_from: int | None, hour_to: int | None
) -> str:
    if hour_from is not None:
        hour_from = _require_int(hour_from, "hour_from")
    if hour_to is not None:
        hour_to = _require_int(hour_to, "hour_to")
    if (
        hour_from is not None
        and hour_to is not None
        and hour_from >= hour_to
    ):
        raise ConfigError("hour_from must be < hour_to")

    def repl_block(match: re.Match[str]) -> str:
        block = match.group(0)
        if hour_from is not None:
            new_block, n = _int_assign("hour_from").subn(
                f"hour_from = {hour_from}", block, count=1
            )
            block = new_block if n else _append_line(block, f"hour_from = {hour_from}")
        if hour_to is not None:
            new_block, n = _int_assign("hour_to").subn(
                f"hour_to = {hour_to}", block, count=1
            )
            block = new_block if n else _append_line(block, f"hour_to = {hour_to}")
        return block

    new_text, n = _SCHEDULE_TABLE.subn(repl_block, text)
    return new_text if n else text


def _replace_int_in_tables(
    text: str, table_re: re.Pattern[str], key: str, value: int
) -> str:
    value = _require_positive_int(value, key)

    def repl_block(match: re.Match[str]) -> str:
        block = match.group(0)
        new_block, n = _int_assign(key).subn(f"{key} = {value}", block, count=1)
        if n:
            return new_block
        return _append_line(block, f"{key} = {value}")

    new_text, n = table_re.subn(repl_block, text)
    return new_text if n else text


def _replace_int_in_table(
    text: str,
    table_re: re.Pattern[str],
    table_name: str,
    key: str,
    value: int,
) -> str:
    value = _require_positive_int(value, key)

    def repl_block(match: re.Match[str]) -> str:
        block = match.group(0)
        new_block, n = _int_assign(key).subn(f"{key} = {value}", block, count=1)
        if n:
            return new_block
        return _append_line(block, f"{key} = {value}")

    new_text, n = table_re.subn(repl_block, text, count=1)
    if n:
        return new_text
    return _append_table(text, table_name, f"{key} = {value}\n")


def _require_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{name}: expected integer")
    return value


def _require_positive_int(value: Any, name: str) -> int:
    number = _require_int(value, name)
    if number < 1:
        raise ConfigError(f"{name} must be at least 1")
    return number


def _section_table(data: dict[str, Any], name: str) -> dict[str, Any] | None:
    section = data.get("section")
    if isinstance(section, dict):
        table = section.get(name)
        if isinstance(table, dict):
            return table
    return None


def _side_from_data(data: dict[str, Any]) -> str:
    mos = data.get("mos")
    if isinstance(mos, dict):
        raw = mos.get("side_menu")
        if isinstance(raw, str) and raw.lower() in {"left", "right"}:
            return raw.lower()
    return "left"


def _paper_from_data(data: dict[str, Any]) -> str:
    style = data.get("style")
    if isinstance(style, dict):
        raw = style.get("scratch_pad")
        if isinstance(raw, str) and raw in _PAPERS:
            return raw
    return "dotted"


def _week_placement_from_data(data: dict[str, Any]) -> str:
    monthly = _section_table(data, "monthly")
    if monthly is not None and monthly.get("week_placement") == _WEEK_RAIL_NONE:
        return _WEEK_RAIL_NONE
    return _WEEK_RAIL_OMIT


def _hours_from_data(data: dict[str, Any]) -> tuple[int, int]:
    daily = _section_table(data, "daily")
    if daily is not None:
        for side in ("left", "right"):
            track = daily.get(side)
            if not isinstance(track, dict):
                continue
            schedule = track.get("schedule")
            if not isinstance(schedule, dict):
                continue
            hour_from = schedule.get("hour_from")
            hour_to = schedule.get("hour_to")
            if isinstance(hour_from, int) and isinstance(hour_to, int):
                return hour_from, hour_to
    return 8, 20


def _priorities_count_from_data(data: dict[str, Any]) -> int:
    daily = _section_table(data, "daily")
    if daily is not None:
        for side in ("left", "right"):
            track = daily.get(side)
            if not isinstance(track, dict):
                continue
            priorities = track.get("priorities")
            if isinstance(priorities, dict):
                count = priorities.get("count")
                if isinstance(count, int) and not isinstance(count, bool) and count >= 1:
                    return count
    return 5


def _int_from_section(data: dict[str, Any], section: str, key: str, default: int) -> int:
    table = _section_table(data, section)
    if table is not None:
        raw = table.get(key)
        if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 1:
            return raw
    return default


def _habit_names_len(data: dict[str, Any]) -> int:
    table = _section_table(data, "habits")
    if table is None:
        return 0
    names = table.get("names")
    if isinstance(names, list):
        return len(names)
    return 0


def _prompt_overlays(
    data: dict[str, Any],
    selected: list[str],
    *,
    hand: str | None,
) -> dict[str, Any]:
    """Questionary overlays for existing keys. No title_height / daily_cell_height."""
    overlays: dict[str, Any] = {}
    if hand is None:
        overlays["hand"] = _prompt_side_menu(_side_from_data(data))
    overlays["paper"] = _prompt_paper(_paper_from_data(data))
    names = set(selected)
    if "monthly" in names:
        overlays["week_placement"] = _prompt_week_rail(_week_placement_from_data(data))
    if "daily" in names:
        hour_from, hour_to = _hours_from_data(data)
        overlays["hour_from"], overlays["hour_to"] = _prompt_hours(hour_from, hour_to)
        overlays["priorities_count"] = _prompt_positive_int(
            "Priority rows", _priorities_count_from_data(data)
        )
    if "daily_notes" in names:
        overlays["daily_notes_pages"] = _prompt_positive_int(
            "Daily notes pages", _int_from_section(data, "daily_notes", "pages", 2)
        )
    if "projects" in names:
        overlays["projects_pages"] = _prompt_positive_int(
            "Project pages", _int_from_section(data, "projects", "pages", 16)
        )
        overlays["projects_card_rows"] = _prompt_positive_int(
            "Project card rows", _int_from_section(data, "projects", "card_rows", 5)
        )
    if "habits" in names:
        minimum = max(1, _habit_names_len(data))
        overlays["habit_columns"] = _prompt_positive_int(
            "Habit columns",
            _int_from_section(data, "habits", "habit_columns", 4),
            minimum=minimum,
        )
    if "meetings" in names:
        overlays["meetings_index_pages"] = _prompt_positive_int(
            "Meeting index pages",
            _int_from_section(data, "meetings", "index_pages", 1),
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
    answer = questionary.text(
        "Hour to", default=str(default_to), validate=_range
    ).ask()
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

