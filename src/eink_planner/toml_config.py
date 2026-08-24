"""TOML device profiles → the MOS generator's existing config shape.

Hyphenated TOML keys (``week-starts``, ``side-menu``, ``font-size``,
``card-rows``) stay hyphenated in the parsed dict; this module normalizes
them onto the same internal DTO the generator already reads.
"""

from __future__ import annotations

import calendar
import tomllib
from pathlib import Path
from typing import Any

from eink_planner import ConfigError
from eink_planner.config import StrictDict

_TOP_LEVEL = frozenset({"device", "calendar", "style", "layout", "sections", "section"})
_DEVICE_KEYS = frozenset({"name", "width", "height", "ppi"})
_CALENDAR_KEYS = frozenset({"year", "week-starts"})
_STYLE_KEYS = frozenset(
    {
        "stroke",
        "type",
        "margin",
        "gutter",
        "regular-height",
        "link-padding",
        "scratch-pad",
        "heading",
        "little-calendar",
    }
)
_STROKE_KEYS = frozenset({"regular", "thick"})
_TYPE_KEYS = frozenset({"body", "h1"})
_MARGIN_KEYS = frozenset({"top", "bottom", "left", "right"})
_GUTTER_KEYS = frozenset({"column"})
_HEADING_KEYS = frozenset({"height", "align"})
_LAYOUT_KEYS = frozenset(
    {
        "name",
        "side-menu",
        "side-menu-width",
        "reverse-months-quarters",
        "reverse-months-quarters-items",
        "menu-rotate",
        "column-gutter",
        "row-gutter",
    }
)
_SIDE_MENU_KEYS = frozenset({"position", "width"})
_SECTION_TYPES = frozenset(
    {"cover", "annual", "quarterly", "monthly", "weekly", "daily", "daily-notes", "projects", "colophon"}
)
_LITTLE_CAL_KEYS = frozenset({"show-month-name", "week-placement", "inset"})
_COVER_KEYS = frozenset({"title", "font-size"})
_ANNUAL_KEYS = frozenset({"little-calendar", "row-gutter", "show-month-name"})
_QUARTERLY_KEYS = frozenset({"months-column", "little-calendar", "pattern", "show-month-name"})
_MONTHLY_KEYS = frozenset({"week-placement", "week-label-rotation", "daily-cell-height", "pattern"})
_WEEKLY_KEYS = frozenset({"column-gutter", "pattern"})
_DAILY_KEYS = frozenset({"columns", "item-spacing", "left", "right"})
_DAILY_COLUMN = frozenset({"schedule", "little-calendar", "priorities", "notes"})
_SCHEDULE_KEYS = frozenset({"from", "to", "time-format", "trailing-half-hour"})
_PRIORITIES_KEYS = frozenset({"count"})
_NOTES_KEYS = frozenset({"pattern", "title-height", "height"})
_DAILY_NOTES_KEYS = frozenset({"pages", "pattern"})
_COLOPHON_KEYS = frozenset({"title", "highlight"})
_PROJECTS_KEYS = frozenset({"pages", "card-rows"})

_SECTION_CLASS = {
    "cover": "cover_plain",
    "annual": "annual",
    "quarterly": "quarterly",
    "monthly": "monthly",
    "weekly": "weekly",
    "daily": "daily",
    "daily-notes": "daily_notes",
    "projects": "projects",
    "colophon": "colophon",
}

_SECTION_NAME = {
    "cover": "cover",
    "annual": "annual",
    "quarterly": "quarterly",
    "monthly": "monthly",
    "weekly": "weekly",
    "daily": "daily",
    "daily-notes": "daily_notes",
    "projects": "projects",
    "colophon": "colophon",
}

_SCRATCH_PATTERNS = frozenset({"dotted", "lined"})


def load_toml(path: str | Path) -> StrictDict:
    source = Path(path)
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise ConfigError(f"{source}: {exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigError(f"{source}: {exc}") from exc
    return parse_toml(text, source=str(source))


def parse_toml(text: str, source: str = "<toml>") -> StrictDict:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{source}: {exc}") from exc
    try:
        dto = toml_document_to_dto(data)
    except ConfigError as exc:
        raise ConfigError(f"{source}: {exc}") from exc
    return StrictDict(dto)


def _require_pattern(name: Any, path: str) -> str:
    text = str(name)
    if text not in _SCRATCH_PATTERNS:
        raise ConfigError(f"{path}: unknown {text!r}")
    return text


def _house_scratch_pad(style: dict[str, Any]) -> str:
    raw = style.get("scratch_pad")
    if raw is None or raw == "":
        return "dotted"
    return _require_pattern(raw, "style.scratch-pad")


def _resolve_pattern(explicit: Any | None, house: str, path: str) -> str:
    if explicit is None:
        return house
    return _require_pattern(explicit, path)


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
                    comp_params["pattern"] = _resolve_pattern(
                        comp_params.get("pattern"), house, "section.daily.notes.pattern"
                    )
        elif name in {"daily_notes", "quarterly", "monthly", "weekly"}:
            path = {
                "daily_notes": "section.daily-notes.pattern",
                "quarterly": "section.quarterly.pattern",
                "monthly": "section.monthly.pattern",
                "weekly": "section.weekly.pattern",
            }[name]
            params["pattern"] = _resolve_pattern(params.get("pattern"), house, path)


def toml_document_to_dto(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ConfigError("expected a TOML table at the root")
    if "debug" in data:
        raise ConfigError("debug does not belong in the config; use `lyp generate --debug`")
    _reject_unknown(data, _TOP_LEVEL, "")

    device_tbl = _require_table(data, "device")
    calendar_tbl = _require_table(data, "calendar")
    style_tbl = _require_table(data, "style")
    layout_tbl = _require_table(data, "layout")

    device_name, width, height, _ppi = _parse_device(device_tbl)
    year = _int(calendar_tbl.get("year"), "calendar.year", required=True)
    _reject_unknown(calendar_tbl, _CALENDAR_KEYS, "calendar")
    weekday = _str(calendar_tbl.get("week-starts"), "calendar.week-starts", required=True)
    style = _parse_style(style_tbl)
    template, mos_layout = _parse_layout(layout_tbl)
    sections, extras = _parse_sections(data.get("sections"), data.get("section"))

    heading = style.get("heading") or {}
    heading_height = heading.get("height") or style["h1"]
    heading_align = heading.get("align") or "horizon"

    style_little = dict(style.get("little_calendar") or {})
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

    scratch = _house_scratch_pad(style)
    _apply_section_patterns(sections, scratch)
    regular_height = style.get("regular_height") or _default_regular_height(style["body"])
    link_padding = style.get("link_padding") or _default_link_padding(style["body"])

    reverse = mos_layout["reverse_months_quarters"]
    mos_layout.setdefault("reverse_months_quarters_items", reverse)

    start_date = f"{year:04d}-01-01"
    last_day = calendar.monthrange(year, 12)[1]
    end_date = f"{year:04d}-12-{last_day:02d}"

    return {
        "template": template,
        "device": device_name,
        "document": {
            "layout": {
                "dimensions": {"width": width, "height": height},
                "margin": style["margin"],
            },
            "text": {"size": style["body"], "h1": style["h1"]},
        },
        "planner": {
            "params": {
                "regular_stroke": style["regular_stroke"],
                "thick_stroke": style["thick_stroke"],
                "regular_height": regular_height,
                "scratch_pad": scratch,
                "link_padding": link_padding,
                "regular_column_gutter": style["column_gutter"],
                "start_date": start_date,
                "end_date": end_date,
                "weekday_start": weekday,
                "little_calendar": little,
                "mos_layout": mos_layout,
                "heading": {"height": heading_height, "align": heading_align},
            },
            "sections": sections,
        },
    }


def _parse_device(table: dict[str, Any]) -> tuple[str, str, str, int | None]:
    _reject_unknown(table, _DEVICE_KEYS, "device")
    name = _str(table.get("name"), "device.name", required=True)
    width = _token(table.get("width"), "device.width", required=True)
    height = _token(table.get("height"), "device.height", required=True)
    ppi = None
    if "ppi" in table:
        ppi = _int(table.get("ppi"), "device.ppi", required=True)
    return name, width, height, ppi


def _parse_style(table: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(table, _STYLE_KEYS, "style")
    stroke = _require_table(table, "stroke", "style")
    typ = _require_table(table, "type", "style")
    margin = _require_table(table, "margin", "style")
    gutter = _require_table(table, "gutter", "style")

    _reject_unknown(stroke, _STROKE_KEYS, "style.stroke")
    _reject_unknown(typ, _TYPE_KEYS, "style.type")
    _reject_unknown(margin, _MARGIN_KEYS, "style.margin")
    _reject_unknown(gutter, _GUTTER_KEYS, "style.gutter")

    out: dict[str, Any] = {
        "regular_stroke": _token(stroke.get("regular"), "style.stroke.regular", required=True),
        "thick_stroke": _token(stroke.get("thick"), "style.stroke.thick", required=True),
        "body": _token(typ.get("body"), "style.type.body", required=True),
        "h1": _token(typ.get("h1"), "style.type.h1", required=True),
        "margin": {
            "top": _token(margin.get("top"), "style.margin.top", required=True),
            "bottom": _token(margin.get("bottom"), "style.margin.bottom", required=True),
            "left": _token(margin.get("left"), "style.margin.left", required=True),
            "right": _token(margin.get("right"), "style.margin.right", required=True),
        },
        "column_gutter": _token(gutter.get("column"), "style.gutter.column", required=True),
    }

    if "regular-height" in table:
        out["regular_height"] = _token(table.get("regular-height"), "style.regular-height", required=True)
    if "link-padding" in table:
        out["link_padding"] = _token(table.get("link-padding"), "style.link-padding", required=True)
    if "scratch-pad" in table:
        out["scratch_pad"] = _plain(table.get("scratch-pad"), "style.scratch-pad")
    if "heading" in table:
        heading = _require_table(table, "heading", "style")
        _reject_unknown(heading, _HEADING_KEYS, "style.heading")
        out["heading"] = {}
        if "height" in heading:
            out["heading"]["height"] = _token(heading.get("height"), "style.heading.height", required=True)
        if "align" in heading:
            out["heading"]["align"] = _str(heading.get("align"), "style.heading.align", required=True)
    if "little-calendar" in table:
        out["little_calendar"] = _parse_little_calendar(table.get("little-calendar"), "style.little-calendar")
    return out


def _parse_layout(table: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    _reject_unknown(table, _LAYOUT_KEYS, "layout")
    template = _str(table.get("name"), "layout.name", required=True)
    if template != "mos":
        raise ConfigError(f"layout: unknown template {template!r}")

    side_raw = table.get("side-menu")
    position: str
    width: str
    if isinstance(side_raw, dict):
        _reject_unknown(side_raw, _SIDE_MENU_KEYS, "layout.side-menu")
        position = _str(side_raw.get("position"), "layout.side-menu.position", required=True)
        width = _token(side_raw.get("width"), "layout.side-menu.width", required=True)
    else:
        position = _str(side_raw, "layout.side-menu", required=True)
        width = _token(table.get("side-menu-width"), "layout.side-menu-width", required=True)
    position = position.lower()
    if position not in {"left", "right"}:
        raise ConfigError("layout.side-menu: expected left or right")

    reverse = _bool(table.get("reverse-months-quarters"), "layout.reverse-months-quarters", required=True)
    mos: dict[str, Any] = {
        "side_menu_position": position,
        "side_menu_width": width,
        "column_gutter": _token(table.get("column-gutter"), "layout.column-gutter", required=True),
        "row_gutter": _token(table.get("row-gutter"), "layout.row-gutter", required=True),
        "menu_rotate": _token(table.get("menu-rotate"), "layout.menu-rotate", required=True),
        "reverse_months_quarters": reverse,
    }
    if "reverse-months-quarters-items" in table:
        mos["reverse_months_quarters_items"] = _bool(
            table.get("reverse-months-quarters-items"),
            "layout.reverse-months-quarters-items",
            required=True,
        )
    return template, mos


def _parse_sections(order: Any, tables: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    extras: dict[str, Any] = {}
    if order is None:
        raise ConfigError("missing key: sections")
    if not isinstance(order, list):
        raise ConfigError("sections: expected an array of section names")
    if tables is None:
        tables = {}
    if not isinstance(tables, dict):
        raise ConfigError("section: expected a table")
    _reject_unknown(tables, _SECTION_TYPES, "section")

    colophon_queue: list[dict[str, Any]] | None = None
    raw_colo = tables.get("colophon")
    if isinstance(raw_colo, list):
        queue: list[dict[str, Any]] = []
        for entry in raw_colo:
            if not isinstance(entry, dict):
                raise ConfigError("section.colophon: expected a table")
            queue.append(entry)
        colophon_queue = queue

    sections: list[dict[str, Any]] = []
    for item in order:
        kind = str(item)
        if kind not in _SECTION_TYPES:
            raise ConfigError(f"unknown section: {kind}")
        if kind == "colophon" and colophon_queue is not None:
            if not colophon_queue:
                raise ConfigError("section.colophon: more names in sections than [[section.colophon]] tables")
            raw = colophon_queue.pop(0)
            if not isinstance(raw, dict):
                raise ConfigError("section.colophon: expected a table")
            params = _section_colophon(raw)
        else:
            raw = tables.get(kind)
            if raw is None:
                raw = {}
            if not isinstance(raw, dict):
                raise ConfigError(f"section.{kind}: expected a table")
            builder = {
                "cover": _section_cover,
                "annual": _section_annual,
                "quarterly": _section_quarterly,
                "monthly": _section_monthly,
                "weekly": _section_weekly,
                "daily": lambda n: _section_daily(n, extras),
                "daily-notes": _section_daily_notes,
                "projects": _section_projects,
                "colophon": _section_colophon,
            }[kind]
            params = builder(raw)
        sections.append(
            {
                "name": _SECTION_NAME[kind],
                "class": _SECTION_CLASS[kind],
                "enabled": True,
                "params": params,
            }
        )
    return sections, extras


def _section_cover(table: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(table, _COVER_KEYS, "section.cover")
    return {
        "name": _str(table.get("title"), "section.cover.title", required=True),
        "font_size": _token(table.get("font-size"), "section.cover.font-size", required=True),
    }


def _section_annual(table: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(table, _ANNUAL_KEYS, "section.annual")
    params: dict[str, Any] = {}
    little = _collect_little_calendar(table, "section.annual")
    if little:
        params["little_calendar"] = little
    if "row-gutter" in table:
        params["row_gutter"] = _token(table.get("row-gutter"), "section.annual.row-gutter", required=True)
    return params


def _section_quarterly(table: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(table, _QUARTERLY_KEYS, "section.quarterly")
    params: dict[str, Any] = {
        "months_column": _str(table.get("months-column"), "section.quarterly.months-column", required=True),
    }
    little = _collect_little_calendar(table, "section.quarterly")
    if little:
        params["little_calendar"] = little
    if "pattern" in table:
        params["pattern"] = _plain(table.get("pattern"), "section.quarterly.pattern")
    return params


def _section_monthly(table: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(table, _MONTHLY_KEYS, "section.monthly")
    params: dict[str, Any] = {
        "month_params": {
            "week_placement": _str(table.get("week-placement"), "section.monthly.week-placement", required=True),
            "week_label_rotation": _token(
                table.get("week-label-rotation"), "section.monthly.week-label-rotation", required=True
            ),
            "daily_cell_height": _token(
                table.get("daily-cell-height"), "section.monthly.daily-cell-height", required=True
            ),
        }
    }
    if "pattern" in table:
        params["pattern"] = _plain(table.get("pattern"), "section.monthly.pattern")
    return params


def _section_weekly(table: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(table, _WEEKLY_KEYS, "section.weekly")
    params: dict[str, Any] = {
        "column_gutter": _token(table.get("column-gutter"), "section.weekly.column-gutter", required=True),
    }
    if "pattern" in table:
        params["pattern"] = _plain(table.get("pattern"), "section.weekly.pattern")
    return params


def _section_daily(table: dict[str, Any], extras: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(table, _DAILY_KEYS, "section.daily")
    params: dict[str, Any] = {
        "columns_width": _typst_columns(table.get("columns"), "section.daily.columns"),
        "items_spacing": _token(table.get("item-spacing"), "section.daily.item-spacing", required=True),
        "left_column": [],
        "right_column": [],
    }
    if "left" in table:
        params["left_column"] = _daily_column(table.get("left"), extras, "section.daily.left")
    if "right" in table:
        params["right_column"] = _daily_column(table.get("right"), extras, "section.daily.right")
    return params


def _daily_column(raw: Any, extras: dict[str, Any], path: str) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: expected a table")
    _reject_unknown(raw, _DAILY_COLUMN, path)
    comps: list[dict[str, Any]] = []
    for key in raw:
        child = raw[key]
        if key == "schedule":
            comps.append(_component_schedule(child, f"{path}.schedule"))
        elif key == "little-calendar":
            lc = _parse_little_calendar(child, f"{path}.little-calendar")
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
            if not isinstance(child, dict):
                raise ConfigError(f"{path}.priorities: expected a table")
            _reject_unknown(child, _PRIORITIES_KEYS, f"{path}.priorities")
            comps.append(
                {
                    "name": "top priorities",
                    "class": "top_priorities",
                    "enabled": True,
                    "params": {"number": _int(child.get("count"), f"{path}.priorities.count", required=True)},
                }
            )
        elif key == "notes":
            if not isinstance(child, dict):
                raise ConfigError(f"{path}.notes: expected a table")
            _reject_unknown(child, _NOTES_KEYS, f"{path}.notes")
            notes: dict[str, Any] = {
                "title_height": _token(child.get("title-height"), f"{path}.notes.title-height", required=True),
                "notes_height": (
                    _token(child.get("height"), f"{path}.notes.height", required=True)
                    if "height" in child
                    else "1fr"
                ),
            }
            if "pattern" in child:
                notes["pattern"] = _plain(child.get("pattern"), f"{path}.notes.pattern")
            comps.append(
                {
                    "name": "notes",
                    "class": "notes",
                    "enabled": True,
                    "params": notes,
                }
            )
        else:
            raise ConfigError(f"unknown key: {path}.{key}")
    return comps


def _component_schedule(raw: Any, path: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: expected a table")
    _reject_unknown(raw, _SCHEDULE_KEYS, path)
    start = _int(raw.get("from"), f"{path}.from", required=True)
    end = _int(raw.get("to"), f"{path}.to", required=True)
    params: dict[str, Any] = {"from": start, "to": end}
    if "time-format" in raw:
        params["time_format"] = _str(raw.get("time-format"), f"{path}.time-format", required=True)
    if "trailing-half-hour" in raw:
        params["trailing_30_minutes"] = _bool(raw.get("trailing-half-hour"), f"{path}.trailing-half-hour", required=True)
    else:
        params["trailing_30_minutes"] = True
    return {"name": "schedule", "class": "schedule", "enabled": True, "params": params}


def _section_colophon(table: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(table, _COLOPHON_KEYS, "section.colophon")
    params: dict[str, Any] = {}
    if "title" in table:
        params["title"] = _str(table.get("title"), "section.colophon.title", required=True)
    if "highlight" in table:
        params["highlight"] = _bool(table.get("highlight"), "section.colophon.highlight", required=True)
    return params


def _section_daily_notes(table: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(table, _DAILY_NOTES_KEYS, "section.daily-notes")
    params: dict[str, Any] = {
        "pages": _int(table.get("pages"), "section.daily-notes.pages", required=True),
    }
    if "pattern" in table:
        params["pattern"] = _plain(table.get("pattern"), "section.daily-notes.pattern")
    return params


def _section_projects(table: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(table, _PROJECTS_KEYS, "section.projects")
    pages = 20 if "pages" not in table else _int(table.get("pages"), "section.projects.pages", required=True)
    rows = 8 if "card-rows" not in table else _int(table.get("card-rows"), "section.projects.card-rows", required=True)
    return {"pages": pages, "card_rows": rows}


def _collect_little_calendar(table: dict[str, Any], path: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "little-calendar" in table:
        out.update(_parse_little_calendar(table.get("little-calendar"), f"{path}.little-calendar"))
    if "show-month-name" in table:
        out["show_month_name"] = _bool(table.get("show-month-name"), f"{path}.show-month-name", required=True)
    return out


def _parse_little_calendar(raw: Any, path: str) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: expected a table")
    _reject_unknown(raw, _LITTLE_CAL_KEYS, path)
    out: dict[str, Any] = {}
    if "show-month-name" in raw:
        out["show_month_name"] = _bool(raw.get("show-month-name"), f"{path}.show-month-name", required=True)
    if "week-placement" in raw:
        out["week_placement"] = _str(raw.get("week-placement"), f"{path}.week-placement", required=True)
    if "inset" in raw:
        out["inset"] = _token(raw.get("inset"), f"{path}.inset", required=True)
    return out


def _typst_columns(value: Any, path: str) -> str:
    if value is None:
        raise ConfigError(f"{path}: missing column tracks")
    if isinstance(value, list):
        parts = [_token(item, f"{path}[]", required=True) for item in value]
        if not parts:
            raise ConfigError(f"{path}: missing column tracks")
        return "(" + ", ".join(parts) + ")"
    raw = _token(value, path, required=True).strip()
    if raw.startswith("(") and raw.endswith(")"):
        parts = raw[1:-1].replace(",", " ").split()
        if not parts:
            raise ConfigError(f"{path}: missing column tracks")
        return "(" + ", ".join(parts) + ")"
    return raw


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


def _reject_unknown(table: dict[str, Any], allowed: frozenset[str], path: str) -> None:
    for key in table:
        if key not in allowed:
            loc = f"{path}.{key}" if path else key
            raise ConfigError(f"unknown key: {loc}")


def _require_table(parent: dict[str, Any], name: str, path: str = "") -> dict[str, Any]:
    loc = f"{path}.{name}" if path else name
    if name not in parent:
        raise ConfigError(f"missing key: {loc}")
    value = parent[name]
    if not isinstance(value, dict):
        raise ConfigError(f"{loc}: expected a table")
    return value


def _plain(value: Any, path: str) -> Any:
    if value is None:
        raise ConfigError(f"{path}: missing value")
    return value


def _str(value: Any, path: str, *, required: bool = False) -> str:
    if value is None:
        if required:
            raise ConfigError(f"{path}: missing value")
        return ""
    if isinstance(value, bool) or isinstance(value, (int, float)):
        raise ConfigError(f"{path}: expected string")
    return str(value)


def _token(value: Any, path: str, *, required: bool = False) -> str:
    if value is None:
        if required:
            raise ConfigError(f"{path}: missing value")
        return ""
    return str(value)


def _int(value: Any, path: str, *, required: bool = False) -> int:
    if value is None:
        if required:
            raise ConfigError(f"{path}: missing value")
        return 0
    if isinstance(value, bool) or isinstance(value, float):
        raise ConfigError(f"{path}: expected integer")
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{path}: expected integer") from exc


def _bool(value: Any, path: str, *, required: bool = False) -> bool:
    if value is None:
        if required:
            raise ConfigError(f"{path}: missing value")
        return False
    if not isinstance(value, bool):
        raise ConfigError(f"{path}: expected boolean")
    return value
