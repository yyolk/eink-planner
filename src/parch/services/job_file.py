"""Emit a complete planner job TOML from a device record plus defaults."""

from dataclasses import dataclass, replace
from typing import Any

from parch.devices import Device, get_device

DEFAULT_YEAR = 2026
DEFAULT_DEVICE = "supernote-nomad"
_WEEK_RAIL_NONE = "none"
_WEEK_RAIL_OMIT = "omit"
_PAPERS = frozenset({"dotted", "lined"})

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

DEFAULT_SECTIONS: tuple[str, ...] = (
    "cover",
    "index",
    "annual",
    "quarterly",
    "monthly",
    "weekly",
    "daily",
    "daily_notes",
    "colophon",
)


@dataclass(frozen=True)
class StyleDefaults:
    stroke_regular: str
    stroke_thick: str
    type_body: str
    type_h1: str
    gutter_column: str
    mos_column_gutter: str
    mos_row_gutter: str
    cover_font_size: str
    annual_row_gutter: str
    monthly_daily_cell_height: str
    weekly_column_gutter: str
    daily_item_spacing: str
    daily_little_cal_inset: str
    notes_title_height: str


NOMAD_STYLE = StyleDefaults(
    stroke_regular="0.3pt",
    stroke_thick="0.6pt",
    type_body="8pt",
    type_h1="8mm",
    gutter_column="8pt",
    mos_column_gutter="1.5mm",
    mos_row_gutter="1.5mm",
    cover_font_size="36pt",
    annual_row_gutter="4pt",
    monthly_daily_cell_height="16mm",
    weekly_column_gutter="4pt",
    daily_item_spacing="4mm",
    daily_little_cal_inset="3pt",
    notes_title_height="4mm",
)

COMPACT_STYLE = StyleDefaults(
    stroke_regular="0.4pt",
    stroke_thick="0.8pt",
    type_body="10pt",
    type_h1="10mm",
    gutter_column="10pt",
    mos_column_gutter="2mm",
    mos_row_gutter="2mm",
    cover_font_size="48pt",
    annual_row_gutter="5pt",
    monthly_daily_cell_height="2.5cm",
    weekly_column_gutter="5pt",
    daily_item_spacing="5mm",
    daily_little_cal_inset="5pt",
    notes_title_height="5mm",
)


@dataclass(frozen=True)
class DeviceJobDefaults:
    sections: tuple[str, ...]
    style: StyleDefaults


JOB_DEFAULTS: dict[str, DeviceJobDefaults] = {
    "supernote-nomad": DeviceJobDefaults(DEFAULT_SECTIONS, NOMAD_STYLE),
    "kindle-scribe": DeviceJobDefaults(DEFAULT_SECTIONS, COMPACT_STYLE),
    "158x210": DeviceJobDefaults(DEFAULT_SECTIONS, COMPACT_STYLE),
    "supernote-manta": DeviceJobDefaults(DEFAULT_SECTIONS, COMPACT_STYLE),
    "remarkable-1": DeviceJobDefaults(DEFAULT_SECTIONS, COMPACT_STYLE),
    "remarkable-2": DeviceJobDefaults(DEFAULT_SECTIONS, COMPACT_STYLE),
    "remarkable-paper-pure": DeviceJobDefaults(DEFAULT_SECTIONS, COMPACT_STYLE),
    "remarkable-paper-pro": DeviceJobDefaults(DEFAULT_SECTIONS, COMPACT_STYLE),
    "remarkable-paper-pro-move": DeviceJobDefaults(DEFAULT_SECTIONS, NOMAD_STYLE),
    "supernote-a5": DeviceJobDefaults(DEFAULT_SECTIONS, COMPACT_STYLE),
    "supernote-a5x": DeviceJobDefaults(DEFAULT_SECTIONS, COMPACT_STYLE),
    "supernote-a6": DeviceJobDefaults(DEFAULT_SECTIONS, NOMAD_STYLE),
    "supernote-a6x": DeviceJobDefaults(DEFAULT_SECTIONS, NOMAD_STYLE),
    "kindle-scribe-11": DeviceJobDefaults(DEFAULT_SECTIONS, COMPACT_STYLE),
    "kindle-scribe-colorsoft": DeviceJobDefaults(DEFAULT_SECTIONS, COMPACT_STYLE),
}


@dataclass
class JobSpec:
    """Complete resume state for a planner job file."""

    device_id: str
    year: int = DEFAULT_YEAR
    week_starts: str = "Monday"
    sections: list[str] | None = None
    hand: str = "left"
    paper: str = "dotted"
    week_placement: str = _WEEK_RAIL_OMIT
    hour_from: int = 8
    hour_to: int = 20
    time_format: str = "%k"
    trailing_half_hour: bool = True
    priorities_count: int = 5
    daily_notes_pages: int = 2
    projects_pages: int = 16
    projects_card_rows: int = 5
    habit_columns: int = 4
    meetings_index_pages: int = 1
    habit_names_len: int = 0
    reverse_months_quarters: bool = True

    def device(self) -> Device:
        return get_device(self.device_id)

    def defaults(self) -> DeviceJobDefaults:
        return JOB_DEFAULTS[self.device().id]

    def resolved_sections(self) -> list[str]:
        if self.sections is not None:
            return list(self.sections)
        return list(self.defaults().sections)


def spec_from_device(device_id: str, **overrides: Any) -> JobSpec:
    device = get_device(device_id)
    cleaned = {key: value for key, value in overrides.items() if value is not None}
    return JobSpec(device_id=device.id, **cleaned)


def spec_from_data(data: dict[str, Any]) -> JobSpec:
    """Resume a job file. Missing keys take device defaults."""
    raw_name = ""
    device_table = data.get("device")
    if isinstance(device_table, dict) and isinstance(device_table.get("name"), str):
        raw_name = device_table["name"]
    device = get_device(raw_name)
    spec = spec_from_device(device.id)
    calendar = data.get("calendar") if isinstance(data.get("calendar"), dict) else {}
    year = calendar.get("year")
    if isinstance(year, int) and not isinstance(year, bool) and 1 <= year <= 9999:
        spec.year = year
    week_starts = calendar.get("week_starts")
    if isinstance(week_starts, str) and week_starts.strip():
        spec.week_starts = week_starts
    raw_sections = data.get("sections")
    if isinstance(raw_sections, list):
        spec.sections = [item for item in raw_sections if isinstance(item, str)]
    mos = data.get("mos") if isinstance(data.get("mos"), dict) else {}
    side = mos.get("side_menu")
    if isinstance(side, str) and side.lower() in {"left", "right"}:
        spec.hand = side.lower()
    reverse = mos.get("reverse_months_quarters")
    if isinstance(reverse, bool):
        spec.reverse_months_quarters = reverse
    style = data.get("style") if isinstance(data.get("style"), dict) else {}
    paper = style.get("scratch_pad")
    if isinstance(paper, str) and paper in _PAPERS:
        spec.paper = paper
    monthly = _section_table(data, "monthly")
    if monthly is not None and monthly.get("week_placement") == _WEEK_RAIL_NONE:
        spec.week_placement = _WEEK_RAIL_NONE
    hour_from, hour_to = _hours_from_data(data)
    spec.hour_from = hour_from
    spec.hour_to = hour_to
    spec.priorities_count = _int_from_track(data, "priorities", "count", spec.priorities_count)
    spec.daily_notes_pages = _int_from_section(data, "daily_notes", "pages", spec.daily_notes_pages)
    spec.projects_pages = _int_from_section(data, "projects", "pages", spec.projects_pages)
    spec.projects_card_rows = _int_from_section(
        data, "projects", "card_rows", spec.projects_card_rows
    )
    spec.habit_columns = _int_from_section(data, "habits", "habit_columns", spec.habit_columns)
    spec.meetings_index_pages = _int_from_section(
        data, "meetings", "index_pages", spec.meetings_index_pages
    )
    habits = _section_table(data, "habits")
    if habits is not None and isinstance(habits.get("names"), list):
        spec.habit_names_len = len(habits["names"])
    return spec


def emit_job(spec: JobSpec) -> str:
    """Write a complete job TOML. Not a dump of a Pydantic model."""
    device = spec.device()
    style = spec.defaults().style
    sections = spec.resolved_sections()
    names = set(sections)
    paper = spec.paper if spec.paper in _PAPERS else "dotted"
    year = spec.year
    parts: list[str] = [
        f"# {device.name}",
        f"# {device.page_width} × {device.page_height} @ {device.ppi} PPI.",
        _toolbar_comment(device),
        "",
        "sections = [",
        *[f'  "{name}",' for name in sections],
        "]",
        "",
        "[device]",
        f'name = "{device.id}"',
        f"ppi = {device.ppi}",
        "",
        "[calendar]",
        f"year = {year}",
        f'week_starts = "{spec.week_starts}"',
        "",
        "[style]",
        f'scratch_pad = "{paper}"',
        "",
        "[style.stroke]",
        f'regular = "{style.stroke_regular}"',
        f'thick = "{style.stroke_thick}"',
        "",
        "[style.type]",
        f'body = "{style.type_body}"',
        f'h1 = "{style.type_h1}"',
        "",
        "[style.gutter]",
        f'column = "{style.gutter_column}"',
        "",
        "[mos]",
        f'side_menu = "{spec.hand}"',
        f"reverse_months_quarters = {_toml_bool(spec.reverse_months_quarters)}",
        'menu_rotate = "270deg"',
        f'column_gutter = "{style.mos_column_gutter}"',
        f'row_gutter = "{style.mos_row_gutter}"',
    ]
    if "cover" in names:
        parts += [
            "",
            "[section.cover]",
            f'title = "{year}"',
            f'font_size = "{style.cover_font_size}"',
        ]
    if "annual" in names:
        parts += [
            "",
            "[section.annual]",
            "show_month_name = true",
            f'row_gutter = "{style.annual_row_gutter}"',
        ]
    if "quarterly" in names:
        parts += [
            "",
            "[section.quarterly]",
            "show_month_name = true",
        ]
    if "monthly" in names:
        parts += [
            "",
            "[section.monthly]",
            'week_label_rotation = "90deg"',
            f'daily_cell_height = "{style.monthly_daily_cell_height}"',
        ]
        if spec.week_placement == _WEEK_RAIL_NONE:
            parts.append('week_placement = "none"')
    if "weekly" in names:
        parts += [
            "",
            "[section.weekly]",
            f'column_gutter = "{style.weekly_column_gutter}"',
        ]
    if "daily" in names:
        parts += [
            "",
            "[section.daily]",
            f'item_spacing = "{style.daily_item_spacing}"',
            "",
            "[section.daily.left.schedule]",
            f"hour_from = {spec.hour_from}",
            f"hour_to = {spec.hour_to}",
            f'time_format = "{spec.time_format}"',
            f"trailing_half_hour = {_toml_bool(spec.trailing_half_hour)}",
            "",
            "[section.daily.left.little_calendar]",
            f'inset = "{style.daily_little_cal_inset}"',
            "",
            "[section.daily.right.priorities]",
            f"count = {spec.priorities_count}",
            "",
            "[section.daily.right.notes]",
            'pattern = "dotted"',
            f'title_height = "{style.notes_title_height}"',
        ]
    if "daily_notes" in names:
        parts += [
            "",
            "[section.daily_notes]",
            f"pages = {spec.daily_notes_pages}",
            f'pattern = "{paper}"',
        ]
    if "projects" in names:
        parts += [
            "",
            "[section.projects]",
            f"pages = {spec.projects_pages}",
            f"card_rows = {spec.projects_card_rows}",
        ]
    if "habits" in names:
        parts += [
            "",
            "[section.habits]",
            f"habit_columns = {spec.habit_columns}",
        ]
    if "review" in names:
        parts += [
            "",
            "[section.review]",
            "weeks_per_page = 13",
            'pattern = "lined"',
        ]
    if "tasks" in names:
        parts += [
            "",
            "[section.tasks]",
            "weeks_per_page = 13",
        ]
    if "meetings" in names:
        parts += [
            "",
            "[section.meetings]",
            f"index_pages = {spec.meetings_index_pages}",
        ]
    return "\n".join(parts) + "\n"


def _toolbar_comment(device: Device) -> str:
    if device.toolbar_edge == "top":
        return f"# Toolbar top {device.toolbar_clearance}."
    return "# No toolbar."


def _toml_bool(value: bool) -> str:
    return "true" if value else "false"


def _section_table(data: dict[str, Any], name: str) -> dict[str, Any] | None:
    section = data.get("section")
    if isinstance(section, dict):
        table = section.get(name)
        if isinstance(table, dict):
            return table
    return None


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


def _int_from_section(data: dict[str, Any], section: str, key: str, default: int) -> int:
    table = _section_table(data, section)
    if table is not None:
        raw = table.get(key)
        if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 1:
            return raw
    return default


def _int_from_track(data: dict[str, Any], component: str, key: str, default: int) -> int:
    daily = _section_table(data, "daily")
    if daily is not None:
        for side in ("left", "right"):
            track = daily.get(side)
            if not isinstance(track, dict):
                continue
            child = track.get(component)
            if isinstance(child, dict):
                raw = child.get(key)
                if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 1:
                    return raw
    return default


def with_overrides(spec: JobSpec, **overrides: Any) -> JobSpec:
    cleaned = {key: value for key, value in overrides.items() if value is not None}
    return replace(spec, **cleaned)
