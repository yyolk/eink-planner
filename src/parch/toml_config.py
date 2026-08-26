"""Device profile models → the MOS generator's existing config shape.

Loaders validate underscore-key TOML via Pydantic, then this adapter
builds the same internal DTO the generator already reads.
"""

from __future__ import annotations

import calendar
import tomllib
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from parch import ConfigError
from parch.config import StrictDict
from parch.models import format_validation_error, load_device_profile
from parch.models.device import (
    AnnualSection,
    ColophonSection,
    CoverSection,
    DailyNotesSection,
    DailySection,
    DailyTrack,
    DeviceProfile,
    LittleCalendar,
    MonthlySection,
    Notes,
    Priorities,
    HabitsSection,
    MeetingsSection,
    ProjectsSection,
    QuarterlySection,
    ReviewSection,
    Schedule,
    WeeklySection,
)

_SECTION_CLASS = {
    "cover": "cover_plain",
    "annual": "annual",
    "quarterly": "quarterly",
    "monthly": "monthly",
    "weekly": "weekly",
    "daily": "daily",
    "daily_notes": "daily_notes",
    "projects": "projects",
    "meetings": "meetings",
    "habits": "habits",
    "review": "review",
    "colophon": "colophon",
}

_SECTION_NAME = {
    "cover": "cover",
    "annual": "annual",
    "quarterly": "quarterly",
    "monthly": "monthly",
    "weekly": "weekly",
    "daily": "daily",
    "daily_notes": "daily_notes",
    "projects": "projects",
    "meetings": "meetings",
    "habits": "habits",
    "review": "review",
    "colophon": "colophon",
}


def load_toml(path: str | Path) -> StrictDict:
    source = Path(path)
    try:
        profile = load_device_profile(source)
    except OSError as exc:
        raise ConfigError(f"{source}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigError(f"{source}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{source}: {exc}") from exc
    except ValidationError as exc:
        raise ConfigError(f"{source}: {format_validation_error(exc)}") from exc
    try:
        return StrictDict(device_profile_to_dto(profile))
    except ConfigError as exc:
        if str(exc).startswith(str(source)):
            raise
        raise ConfigError(f"{source}: {exc}") from exc


def parse_toml(text: str, source: str = "<toml>") -> StrictDict:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{source}: {exc}") from exc
    try:
        profile = DeviceProfile.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"{source}: {format_validation_error(exc)}") from exc
    try:
        return StrictDict(device_profile_to_dto(profile))
    except ConfigError as exc:
        if str(exc).startswith(str(source)):
            raise
        raise ConfigError(f"{source}: {exc}") from exc


def device_profile_to_dto(profile: DeviceProfile) -> dict[str, Any]:
    style = profile.style
    heading = style.heading
    heading_height = (heading.height if heading and heading.height else None) or style.type.h1
    heading_align = (heading.align if heading and heading.align else None) or "horizon"

    style_little = _little_cal_dict(style.little_calendar)
    sections, extras = _sections_from_profile(profile)

    little = dict(style_little)
    if extras.get("daily_little_calendar"):
        little.update(extras["daily_little_calendar"])
    little.setdefault("week_placement", "left")
    little.setdefault("inset", "3pt")

    for section in sections:
        if section["name"] != "daily":
            continue
        for col_name in ("left_column", "right_column"):
            for comp in section["params"].get(col_name) or []:
                if comp.get("class") != "little_calendar":
                    continue
                merged = {**style_little, **(comp.get("params") or {})}
                merged.setdefault("week_placement", "left")
                merged.setdefault("inset", "3pt")
                comp["params"] = merged

    scratch = style.scratch_pad or "dotted"
    _apply_section_patterns(sections, scratch)
    regular_height = style.regular_height or _default_regular_height(style.type.body)
    link_padding = style.link_padding or _default_link_padding(style.type.body)

    mos_layout = {
        "side_menu_position": profile.layout.side_menu,
        "side_menu_width": profile.layout.side_menu_width,
        "column_gutter": profile.layout.column_gutter,
        "row_gutter": profile.layout.row_gutter,
        "menu_rotate": profile.layout.menu_rotate,
        "reverse_months_quarters": profile.layout.reverse_months_quarters,
    }
    if profile.layout.reverse_months_quarters_items is not None:
        mos_layout["reverse_months_quarters_items"] = profile.layout.reverse_months_quarters_items
    else:
        mos_layout["reverse_months_quarters_items"] = profile.layout.reverse_months_quarters

    year = profile.calendar.year
    start_date = f"{year:04d}-01-01"
    last_day = calendar.monthrange(year, 12)[1]
    end_date = f"{year:04d}-12-{last_day:02d}"

    return {
        "template": profile.layout.name,
        "device": profile.device.name,
        "document": {
            "layout": {
                "dimensions": {"width": profile.device.width, "height": profile.device.height},
                "margin": style.margin.model_dump(),
            },
            "text": {"size": style.type.body, "h1": style.type.h1},
        },
        "planner": {
            "params": {
                "regular_stroke": style.stroke.regular,
                "thick_stroke": style.stroke.thick,
                "regular_height": regular_height,
                "scratch_pad": scratch,
                "link_padding": link_padding,
                "regular_column_gutter": style.gutter.column,
                "start_date": start_date,
                "end_date": end_date,
                "weekday_start": profile.calendar.week_starts,
                "little_calendar": little,
                "mos_layout": mos_layout,
                "heading": {"height": heading_height, "align": heading_align},
            },
            "sections": sections,
        },
    }


def _sections_from_profile(profile: DeviceProfile) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    extras: dict[str, Any] = {}
    tables = profile.section
    colo_queue: list[ColophonSection] | None = None
    if isinstance(tables.colophon, list):
        colo_queue = list(tables.colophon)

    sections: list[dict[str, Any]] = []
    for kind in profile.sections:
        if kind == "colophon" and colo_queue is not None:
            if not colo_queue:
                raise ConfigError("section.colophon: more names in sections than [[section.colophon]] tables")
            params = _section_colophon(colo_queue.pop(0))
        else:
            raw = getattr(tables, kind, None)
            params = _build_section_params(kind, raw, extras)
        sections.append(
            {
                "name": _SECTION_NAME[kind],
                "class": _SECTION_CLASS[kind],
                "enabled": True,
                "params": params,
            }
        )
    return sections, extras


def _build_section_params(kind: str, raw: Any, extras: dict[str, Any]) -> dict[str, Any]:
    if kind == "cover":
        return _section_cover(raw)
    if kind == "annual":
        return _section_annual(raw) if raw is not None else {}
    if kind == "quarterly":
        return _section_quarterly(raw)
    if kind == "monthly":
        return _section_monthly(raw)
    if kind == "weekly":
        return _section_weekly(raw)
    if kind == "daily":
        return _section_daily(raw, extras)
    if kind == "daily_notes":
        return _section_daily_notes(raw)
    if kind == "projects":
        return _section_projects(raw)
    if kind == "meetings":
        return _section_meetings(raw)
    if kind == "habits":
        return _section_habits(raw)
    if kind == "review":
        return _section_review(raw)
    if kind == "colophon":
        return _section_colophon(raw) if raw is not None else {}
    return {}


def _section_cover(table: CoverSection) -> dict[str, Any]:
    return {"name": table.title, "font_size": table.font_size}


def _section_annual(table: AnnualSection) -> dict[str, Any]:
    params: dict[str, Any] = {}
    little = _little_cal_dict(table.little_calendar)
    if table.show_month_name is not None:
        little["show_month_name"] = table.show_month_name
    if little:
        params["little_calendar"] = little
    if table.row_gutter is not None:
        params["row_gutter"] = table.row_gutter
    return params


def _section_quarterly(table: QuarterlySection) -> dict[str, Any]:
    params: dict[str, Any] = {"months_column": table.months_column}
    little = _little_cal_dict(table.little_calendar)
    if table.show_month_name is not None:
        little["show_month_name"] = table.show_month_name
    if little:
        params["little_calendar"] = little
    if table.pattern is not None:
        params["pattern"] = table.pattern
    return params


def _section_monthly(table: MonthlySection) -> dict[str, Any]:
    params: dict[str, Any] = {
        "month_params": {
            "week_placement": table.week_placement,
            "week_label_rotation": table.week_label_rotation,
            "daily_cell_height": table.daily_cell_height,
        }
    }
    if table.pattern is not None:
        params["pattern"] = table.pattern
    return params


def _section_weekly(table: WeeklySection) -> dict[str, Any]:
    params: dict[str, Any] = {"column_gutter": table.column_gutter}
    if table.pattern is not None:
        params["pattern"] = table.pattern
    return params


def _section_daily(table: DailySection, extras: dict[str, Any]) -> dict[str, Any]:
    return {
        "columns_width": "(" + ", ".join(table.columns) + ")",
        "items_spacing": table.item_spacing,
        "left_column": _daily_column(table.left, extras) if table.left else [],
        "right_column": _daily_column(table.right, extras) if table.right else [],
    }


def _daily_column(track: DailyTrack, extras: dict[str, Any]) -> list[dict[str, Any]]:
    comps: list[dict[str, Any]] = []
    for key in track.component_keys():
        child = getattr(track, key)
        if child is None:
            continue
        if key == "schedule":
            comps.append(_component_schedule(child))
        elif key == "little_calendar":
            lc = _little_cal_dict(child)
            extras["daily_little_calendar"] = lc
            comps.append(
                {
                    "name": "little calendar",
                    "class": "little_calendar",
                    "enabled": True,
                    "params": lc,
                }
            )
        elif key == "priorities":
            comps.append(_component_priorities(child))
        elif key == "notes":
            comps.append(_component_notes(child))
    return comps


def _component_schedule(raw: Schedule) -> dict[str, Any]:
    params: dict[str, Any] = {"from": raw.hour_from, "to": raw.hour_to}
    if raw.time_format is not None:
        params["time_format"] = raw.time_format
    params["trailing_30_minutes"] = raw.trailing_half_hour
    return {"name": "schedule", "class": "schedule", "enabled": True, "params": params}


def _component_priorities(raw: Priorities) -> dict[str, Any]:
    return {
        "name": "priorities",
        "class": "priorities",
        "enabled": True,
        "params": {"number": raw.count},
    }


def _component_notes(raw: Notes) -> dict[str, Any]:
    notes: dict[str, Any] = {
        "title_height": raw.title_height,
        "notes_height": raw.height if raw.height is not None else "1fr",
    }
    if raw.pattern is not None:
        notes["pattern"] = raw.pattern
    return {"name": "notes", "class": "notes", "enabled": True, "params": notes}


def _section_colophon(table: ColophonSection) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if table.title is not None:
        params["title"] = table.title
    if table.dump is not None:
        params["dump"] = table.dump
    if table.command is not None:
        params["command"] = table.command
    if table.sha is not None:
        params["sha"] = table.sha
    return params


def _section_daily_notes(table: DailyNotesSection) -> dict[str, Any]:
    params: dict[str, Any] = {"pages": table.pages}
    if table.pattern is not None:
        params["pattern"] = table.pattern
    return params


def _section_projects(table: ProjectsSection | None) -> dict[str, Any]:
    if table is None:
        return {"pages": 16, "card_rows": 5}
    return {"pages": table.pages, "card_rows": table.card_rows}


def _section_meetings(table: MeetingsSection | None) -> dict[str, Any]:
    if table is None:
        return {"index_pages": 1}
    return {"index_pages": table.index_pages}


def _section_habits(table: HabitsSection | None) -> dict[str, Any]:
    if table is None:
        table = HabitsSection()
    return {"habit_columns": table.habit_columns, "names": list(table.names)}


def _section_review(table: ReviewSection | None) -> dict[str, Any]:
    if table is None:
        table = ReviewSection()
    params: dict[str, Any] = {"weeks_per_page": table.weeks_per_page}
    if table.pattern is not None:
        params["pattern"] = table.pattern
    return params


def _little_cal_dict(raw: LittleCalendar | None) -> dict[str, Any]:
    if raw is None:
        return {}
    out: dict[str, Any] = {}
    if raw.show_month_name is not None:
        out["show_month_name"] = raw.show_month_name
    if raw.week_placement is not None:
        out["week_placement"] = raw.week_placement
    if raw.inset is not None:
        out["inset"] = raw.inset
    return out


def _apply_section_patterns(sections: list[dict[str, Any]], house: str) -> None:
    for section in sections:
        name = section["name"]
        params = section["params"]
        if name == "daily":
            for col_name in ("left_column", "right_column"):
                for comp in params.get(col_name) or []:
                    if comp.get("class") != "notes":
                        continue
                    comp_params = comp.setdefault("params", {})
                    if comp_params.get("pattern") is None:
                        comp_params["pattern"] = house
        elif name in {"daily_notes", "quarterly", "monthly", "weekly"}:
            # Review is not in this set: its default is lined, not the house scratch_pad.
            if params.get("pattern") is None:
                params["pattern"] = house


def _default_regular_height(body: str) -> str:
    pt = _pt_number(body)
    if pt is not None:
        half = pt / 2
        return f"{int(half)}mm" if half == int(half) else f"{half}mm"
    return "5mm"


def _default_link_padding(body: str) -> str:
    pt = _pt_number(body)
    if pt is not None:
        pad = pt - 2
        return f"{int(pad)}pt" if pad == int(pad) else f"{pad}pt"
    return "8pt"


def _pt_number(token: str) -> float | None:
    text = str(token).strip()
    if not text.endswith("pt"):
        return None
    try:
        return float(text[:-2])
    except ValueError:
        return None


def apply_debug(dto: StrictDict, debug: bool) -> StrictDict:
    """CLI overlay: debug is not a config key."""
    if not debug:
        return dto
    data = dto.to_plain()
    data["debug"] = True
    return StrictDict(data)


def apply_year(dto: StrictDict, year: int | None) -> StrictDict:
    """CLI overlay: rewrite start/end dates. Year stays in the profile."""
    if year is None:
        return dto
    year = _coerce_year(year)
    data = dto.to_plain()
    planner = data.setdefault("planner", {})
    if not isinstance(planner, dict):
        planner = {}
        data["planner"] = planner
    params = planner.setdefault("params", {})
    if not isinstance(params, dict):
        params = {}
        planner["params"] = params
    old_year = _year_from_start(params.get("start_date"))
    try:
        last_day = calendar.monthrange(year, 12)[1]
    except ValueError as exc:
        raise ConfigError("year: out of range") from exc
    params["start_date"] = f"{year:04d}-01-01"
    params["end_date"] = f"{year:04d}-12-{last_day:02d}"
    if old_year is not None and old_year != year:
        _rewrite_cover_year(planner, old_year, year)
    return StrictDict(data)


def _coerce_year(year: Any) -> int:
    if isinstance(year, bool):
        raise ConfigError("year: expected integer")
    if isinstance(year, int):
        value = year
    else:
        try:
            value = int(year)
        except (TypeError, ValueError) as exc:
            raise ConfigError("year: expected integer") from exc
    if value < 1 or value > 9999:
        raise ConfigError("year: out of range")
    return value


def _year_from_start(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(str(raw)[:4])
    except (TypeError, ValueError):
        return None


def _rewrite_cover_year(planner: dict[str, Any], old_year: int, year: int) -> None:
    sections = planner.get("sections") or []
    old = f"{old_year:04d}"
    new = f"{year:04d}"
    for section in sections:
        if not isinstance(section, dict):
            continue
        if section.get("name") != "cover" and section.get("class") != "cover_plain":
            continue
        params = section.get("params")
        if not isinstance(params, dict):
            continue
        name = params.get("name")
        if isinstance(name, str) and old in name:
            params["name"] = name.replace(old, new)
