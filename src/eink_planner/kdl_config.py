"""KDL 2.0 device profiles → the MOS generator's existing config shape.

ckdl 1.0 implements KDL 2.0 but does not accept digit-leading unit tokens
(``8mm``, ``0.3pt``, ``3fr``, ``270deg``) or hour ranges (``8..20``). Those
are valid in our profile style, so we quote them before ``ckdl.parse`` and
keep the original token text (``8mm``, not a split number + unit).
"""

from __future__ import annotations

import calendar
import re
from pathlib import Path
from typing import Any, Iterable

import ckdl

from eink_planner import ConfigError
from eink_planner.config import StrictDict

_TOP_LEVEL = frozenset({"device", "year", "week-starts", "style", "layout", "section"})
_STYLE_NODES = frozenset(
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
_STROKE_NODES = frozenset({"regular", "thick"})
_TYPE_NODES = frozenset({"body", "h1"})
_MARGIN_NODES = frozenset({"top", "bottom", "left", "right"})
_GUTTER_NODES = frozenset({"column"})
_HEADING_NODES = frozenset({"height", "align"})
_LAYOUT_NODES = frozenset(
    {
        "side-menu",
        "reverse-months-quarters",
        "reverse-months-quarters-items",
        "menu-rotate",
        "column-gutter",
        "row-gutter",
    }
)
_SECTION_TYPES = frozenset(
    {"cover", "annual", "quarterly", "monthly", "weekly", "daily", "daily-notes", "projects", "colophon"}
)
_LITTLE_CAL_NODES = frozenset({"show-month-name", "week-placement", "inset"})
_COVER_NODES = frozenset({"title", "font-size"})
_ANNUAL_NODES = frozenset({"little-calendar", "row-gutter"})
_QUARTERLY_NODES = frozenset({"months-column", "little-calendar", "pattern"})
_MONTHLY_NODES = frozenset({"week-placement", "week-label-rotation", "daily-cell-height", "pattern"})
_WEEKLY_NODES = frozenset({"column-gutter", "pattern"})
_DAILY_NODES = frozenset({"columns", "item-spacing", "left", "right"})
_DAILY_COLUMN = frozenset({"schedule", "little-calendar", "top-priorities", "notes"})
_SCHEDULE_NODES = frozenset({"time-format", "trailing-half-hour"})
_NOTES_NODES = frozenset({"pattern", "title-height", "height"})
_DAILY_NOTES_NODES = frozenset({"pages", "pattern"})
_COLOPHON_NODES = frozenset({"title", "highlight"})
_PROJECTS_NODES = frozenset({"pages"})
_DEVICE_NODES = frozenset({"page-size", "ppi"})

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

# Bare tokens that ckdl 1.0 cannot parse: units, fr tracks, hour ranges,
# and Typst-style ``(3fr 5fr)`` column tuples.
_BARE_TOKEN = re.compile(
    r"""
    \(\s*\d+(?:\.\d+)?fr(?:[ \t]+\d+(?:\.\d+)?fr)+\s*\)
    |
    \d+\.\.\d+
    |
    \d+(?:\.\d+)?(?:mm|cm|pt|fr|deg|in|em)
    """,
    re.VERBOSE,
)


def load_kdl(path: str | Path) -> StrictDict:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"{source}: {exc}") from exc
    return parse_kdl(text, source=str(source))


def parse_kdl(text: str, source: str = "<kdl>") -> StrictDict:
    quoted = quote_kdl_tokens(text)
    try:
        doc = ckdl.parse(quoted, version=2)
    except ckdl.ParseError as exc:
        raise ConfigError(f"{source}: {exc}") from exc
    try:
        data = kdl_document_to_dto(doc)
    except ConfigError as exc:
        raise ConfigError(f"{source}: {exc}") from exc
    return StrictDict(data)


def quote_kdl_tokens(text: str) -> str:
    """Quote digit-leading unit/range tokens so ckdl can parse the profile."""
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("//", i):
            end = text.find("\n", i)
            if end < 0:
                out.append(text[i:])
                break
            out.append(text[i:end])
            i = end
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                out.append(text[i:])
                break
            out.append(text[i : end + 2])
            i = end + 2
            continue
        if text[i] == '"':
            chunk, i = _consume_quoted(text, i)
            out.append(chunk)
            continue
        match = _BARE_TOKEN.match(text, i)
        if match:
            out.append(f'"{match.group(0)}"')
            i = match.end()
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def _consume_quoted(text: str, start: int) -> tuple[str, int]:
    i = start + 1
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == '"':
            return text[start : i + 1], i + 1
        i += 1
    return text[start:], n


_SCRATCH_PATTERNS = frozenset({"dotted", "lined"})


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


def _set_optional_pattern(node: ckdl.Node, params: dict[str, Any], path: str) -> None:
    if (pattern := _first(node.children, "pattern")) is not None:
        params["pattern"] = _plain(_arg0(pattern, path))


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


def kdl_document_to_dto(doc: ckdl.Document) -> dict[str, Any]:
    nodes = list(doc.nodes)
    if _first(nodes, "debug") is not None:
        raise ConfigError("debug does not belong in the config; use `lyp generate --debug`")
    _reject_unknown(nodes, _TOP_LEVEL, "")

    device_node = _require(nodes, "device")
    year_node = _require(nodes, "year")
    week_node = _require(nodes, "week-starts")
    style_node = _require(nodes, "style")
    layout_node = _require(nodes, "layout")
    section_nodes = [n for n in nodes if n.name == "section"]

    device_name, width, height, _ppi = _parse_device(device_node)
    year = _int_arg(year_node, "year")
    weekday = _str_arg(week_node, "week-starts")
    style = _parse_style(style_node)
    template, mos_layout = _parse_layout(layout_node)
    sections, extras = _parse_sections(section_nodes)

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


def _parse_device(node: ckdl.Node) -> tuple[str, str, str, int | None]:
    name = _str_arg(node, "device")
    _reject_unknown(node.children, _DEVICE_NODES, "device")
    page = _require(node.children, "page-size", "device")
    args = [_plain(a) for a in page.args]
    if len(args) != 2:
        raise ConfigError("device.page-size: expected width height")
    ppi_node = _first(node.children, "ppi")
    ppi = _int_arg(ppi_node, "device.ppi") if ppi_node is not None else None
    return name, _token(args[0]), _token(args[1]), ppi


def _parse_style(node: ckdl.Node) -> dict[str, Any]:
    _reject_unknown(node.children, _STYLE_NODES, "style")
    stroke = _require(node.children, "stroke", "style")
    typ = _require(node.children, "type", "style")
    margin = _require(node.children, "margin", "style")
    gutter = _require(node.children, "gutter", "style")

    _reject_unknown(stroke.children, _STROKE_NODES, "style.stroke")
    _reject_unknown(typ.children, _TYPE_NODES, "style.type")
    _reject_unknown(margin.children, _MARGIN_NODES, "style.margin")
    _reject_unknown(gutter.children, _GUTTER_NODES, "style.gutter")

    out: dict[str, Any] = {
        "regular_stroke": _token(_child_arg(stroke, "regular", "style.stroke")),
        "thick_stroke": _token(_child_arg(stroke, "thick", "style.stroke")),
        "body": _token(_child_arg(typ, "body", "style.type")),
        "h1": _token(_child_arg(typ, "h1", "style.type")),
        "margin": {
            "top": _token(_child_arg(margin, "top", "style.margin")),
            "bottom": _token(_child_arg(margin, "bottom", "style.margin")),
            "left": _token(_child_arg(margin, "left", "style.margin")),
            "right": _token(_child_arg(margin, "right", "style.margin")),
        },
        "column_gutter": _token(_child_arg(gutter, "column", "style.gutter")),
    }

    if (rh := _first(node.children, "regular-height")) is not None:
        out["regular_height"] = _token(_arg0(rh, "style.regular-height"))
    if (lp := _first(node.children, "link-padding")) is not None:
        out["link_padding"] = _token(_arg0(lp, "style.link-padding"))
    if (sp := _first(node.children, "scratch-pad")) is not None:
        out["scratch_pad"] = _plain(_arg0(sp, "style.scratch-pad"))
    if (heading := _first(node.children, "heading")) is not None:
        _reject_unknown(heading.children, _HEADING_NODES, "style.heading")
        out["heading"] = {}
        if (h := _first(heading.children, "height")) is not None:
            out["heading"]["height"] = _token(_arg0(h, "style.heading.height"))
        if (a := _first(heading.children, "align")) is not None:
            out["heading"]["align"] = _plain(_arg0(a, "style.heading.align"))
    if (lc := _first(node.children, "little-calendar")) is not None:
        out["little_calendar"] = _parse_little_calendar(lc, "style.little-calendar")
    return out


def _parse_layout(node: ckdl.Node) -> tuple[str, dict[str, Any]]:
    template = _str_arg(node, "layout")
    if template != "mos":
        raise ConfigError(f"layout: unknown template {template!r}")
    _reject_unknown(node.children, _LAYOUT_NODES, "layout")
    side = _require(node.children, "side-menu", "layout")
    side_args = [_plain(a) for a in side.args]
    if len(side_args) != 2:
        raise ConfigError("layout.side-menu: expected position width")
    position = str(side_args[0]).lower()
    if position not in {"left", "right"}:
        raise ConfigError("layout.side-menu: expected left or right")
    reverse = _bool_arg(_require(node.children, "reverse-months-quarters", "layout"), "layout.reverse-months-quarters")
    mos: dict[str, Any] = {
        "side_menu_position": position,
        "side_menu_width": _token(side_args[1]),
        "column_gutter": _token(_child_arg(node, "column-gutter", "layout")),
        "row_gutter": _token(_child_arg(node, "row-gutter", "layout")),
        "menu_rotate": _token(_child_arg(node, "menu-rotate", "layout")),
        "reverse_months_quarters": reverse,
    }
    items = _first(node.children, "reverse-months-quarters-items")
    if items is not None:
        mos["reverse_months_quarters_items"] = _bool_arg(items, "layout.reverse-months-quarters-items")
    return template, mos


def _parse_sections(nodes: list[ckdl.Node]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    extras: dict[str, Any] = {}
    sections: list[dict[str, Any]] = []
    for node in nodes:
        if not node.args:
            raise ConfigError("section: missing type argument")
        if len(node.args) != 1:
            raise ConfigError("section: expected one type argument")
        kind = str(_plain(node.args[0]))
        if kind not in _SECTION_TYPES:
            raise ConfigError(f"unknown section: {kind}")
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
        params = builder(node)
        sections.append(
            {
                "name": _SECTION_NAME[kind],
                "class": _SECTION_CLASS[kind],
                "enabled": True,
                "params": params,
            }
        )
    return sections, extras


def _section_cover(node: ckdl.Node) -> dict[str, Any]:
    _reject_unknown(node.children, _COVER_NODES, "section.cover")
    return {
        "name": _plain(_child_arg(node, "title", "section.cover")),
        "font_size": _token(_child_arg(node, "font-size", "section.cover")),
    }


def _section_annual(node: ckdl.Node) -> dict[str, Any]:
    _reject_unknown(node.children, _ANNUAL_NODES, "section.annual")
    params: dict[str, Any] = {}
    if (lc := _first(node.children, "little-calendar")) is not None:
        params["little_calendar"] = _parse_little_calendar(lc, "section.annual.little-calendar")
    if (rg := _first(node.children, "row-gutter")) is not None:
        params["row_gutter"] = _token(_arg0(rg, "section.annual.row-gutter"))
    return params


def _section_quarterly(node: ckdl.Node) -> dict[str, Any]:
    _reject_unknown(node.children, _QUARTERLY_NODES, "section.quarterly")
    params: dict[str, Any] = {
        "months_column": _plain(_child_arg(node, "months-column", "section.quarterly")),
    }
    if (lc := _first(node.children, "little-calendar")) is not None:
        params["little_calendar"] = _parse_little_calendar(lc, "section.quarterly.little-calendar")
    _set_optional_pattern(node, params, "section.quarterly.pattern")
    return params


def _section_monthly(node: ckdl.Node) -> dict[str, Any]:
    _reject_unknown(node.children, _MONTHLY_NODES, "section.monthly")
    params: dict[str, Any] = {
        "month_params": {
            "week_placement": _plain(_child_arg(node, "week-placement", "section.monthly")),
            "week_label_rotation": _token(_child_arg(node, "week-label-rotation", "section.monthly")),
            "daily_cell_height": _token(_child_arg(node, "daily-cell-height", "section.monthly")),
        }
    }
    _set_optional_pattern(node, params, "section.monthly.pattern")
    return params


def _section_weekly(node: ckdl.Node) -> dict[str, Any]:
    _reject_unknown(node.children, _WEEKLY_NODES, "section.weekly")
    params: dict[str, Any] = {"column_gutter": _token(_child_arg(node, "column-gutter", "section.weekly"))}
    _set_optional_pattern(node, params, "section.weekly.pattern")
    return params


def _section_daily(node: ckdl.Node, extras: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown(node.children, _DAILY_NODES, "section.daily")
    columns = _require(node.children, "columns", "section.daily")
    params: dict[str, Any] = {
        "columns_width": _typst_columns(columns, "section.daily.columns"),
        "items_spacing": _token(_child_arg(node, "item-spacing", "section.daily")),
        "left_column": [],
        "right_column": [],
    }
    if (left := _first(node.children, "left")) is not None:
        params["left_column"] = _daily_column(left, extras, "section.daily.left")
    if (right := _first(node.children, "right")) is not None:
        params["right_column"] = _daily_column(right, extras, "section.daily.right")
    return params


def _daily_column(node: ckdl.Node, extras: dict[str, Any], path: str) -> list[dict[str, Any]]:
    _reject_unknown(node.children, _DAILY_COLUMN, path)
    comps: list[dict[str, Any]] = []
    for child in node.children:
        if child.name == "schedule":
            comps.append(_component_schedule(child, f"{path}.schedule"))
        elif child.name == "little-calendar":
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
        elif child.name == "top-priorities":
            comps.append(
                {
                    "name": "top priorities",
                    "class": "top_priorities",
                    "enabled": True,
                    "params": {"number": _int_arg(child, f"{path}.top-priorities")},
                }
            )
        elif child.name == "notes":
            _reject_unknown(child.children, _NOTES_NODES, f"{path}.notes")
            pattern_node = _first(child.children, "pattern")
            title = _token(_child_arg(child, "title-height", f"{path}.notes"))
            height_node = _first(child.children, "height")
            notes = {
                "title_height": title,
                "notes_height": _token(_arg0(height_node, f"{path}.notes.height"))
                if height_node is not None
                else "1fr",
            }
            if pattern_node is not None:
                notes["pattern"] = _plain(_arg0(pattern_node, f"{path}.notes.pattern"))
            comps.append(
                {
                    "name": "notes",
                    "class": "notes",
                    "enabled": True,
                    "params": notes,
                }
            )
        else:
            raise ConfigError(f"unknown node: {path}.{child.name}")
    return comps


def _component_schedule(node: ckdl.Node, path: str) -> dict[str, Any]:
    _reject_unknown(node.children, _SCHEDULE_NODES, path)
    start, end = _hour_range(node, path)
    params: dict[str, Any] = {"from": start, "to": end}
    if (fmt := _first(node.children, "time-format")) is not None:
        params["time_format"] = _plain(_arg0(fmt, f"{path}.time-format"))
    if (trail := _first(node.children, "trailing-half-hour")) is not None:
        params["trailing_30_minutes"] = _bool_arg(trail, f"{path}.trailing-half-hour")
    else:
        params["trailing_30_minutes"] = True
    return {"name": "schedule", "class": "schedule", "enabled": True, "params": params}


def _section_colophon(node: ckdl.Node) -> dict[str, Any]:
    _reject_unknown(node.children, _COLOPHON_NODES, "section.colophon")
    params: dict[str, Any] = {}
    if (title := _first(node.children, "title")) is not None:
        params["title"] = _plain(_arg0(title, "section.colophon.title"))
    if (highlight := _first(node.children, "highlight")) is not None:
        params["highlight"] = _bool_arg(highlight, "section.colophon.highlight")
    return params


def _section_daily_notes(node: ckdl.Node) -> dict[str, Any]:
    _reject_unknown(node.children, _DAILY_NOTES_NODES, "section.daily-notes")
    params: dict[str, Any] = {"pages": _int_arg(_require(node.children, "pages", "section.daily-notes"), "section.daily-notes.pages")}
    _set_optional_pattern(node, params, "section.daily-notes.pattern")
    return params


def _section_projects(node: ckdl.Node) -> dict[str, Any]:
    _reject_unknown(node.children, _PROJECTS_NODES, "section.projects")
    pages_node = _first(node.children, "pages")
    if pages_node is None:
        return {"pages": 20}
    return {"pages": _int_arg(pages_node, "section.projects.pages")}


def _parse_little_calendar(node: ckdl.Node, path: str) -> dict[str, Any]:
    _reject_unknown(node.children, _LITTLE_CAL_NODES, path)
    out: dict[str, Any] = {}
    if (show := _first(node.children, "show-month-name")) is not None:
        out["show_month_name"] = _bool_arg(show, f"{path}.show-month-name")
    if (place := _first(node.children, "week-placement")) is not None:
        out["week_placement"] = _plain(_arg0(place, f"{path}.week-placement"))
    if (inset := _first(node.children, "inset")) is not None:
        out["inset"] = _token(_arg0(inset, f"{path}.inset"))
    return out


def _hour_range(node: ckdl.Node, path: str) -> tuple[int, int]:
    args = [_plain(a) for a in node.args]
    if len(args) == 1 and isinstance(args[0], str) and ".." in args[0]:
        left, right = args[0].split("..", 1)
        try:
            return int(left), int(right)
        except ValueError as exc:
            raise ConfigError(f"{path}: expected hour range like 8..20") from exc
    if len(args) == 2:
        if any(isinstance(a, bool) or not isinstance(a, int) for a in args):
            raise ConfigError(f"{path}: expected hour range like 8..20")
        return args[0], args[1]
    raise ConfigError(f"{path}: expected hour range like 8..20")


def _typst_columns(node: ckdl.Node, path: str) -> str:
    args = [_token(_plain(a)) for a in node.args]
    if not args:
        raise ConfigError(f"{path}: missing column tracks")
    if len(args) == 1:
        raw = args[0].strip()
        if raw.startswith("(") and raw.endswith(")"):
            parts = raw[1:-1].replace(",", " ").split()
            if not parts:
                raise ConfigError(f"{path}: missing column tracks")
            return "(" + ", ".join(parts) + ")"
        return raw
    return "(" + ", ".join(args) + ")"


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
    """CLI overlay: debug is not a KDL key."""
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


def _reject_unknown(nodes: Iterable[ckdl.Node], allowed: frozenset[str], path: str) -> None:
    for node in nodes:
        if node.name not in allowed:
            loc = f"{path}.{node.name}" if path else node.name
            raise ConfigError(f"unknown node: {loc}")


def _require(nodes: Iterable[ckdl.Node], name: str, path: str = "") -> ckdl.Node:
    found = [n for n in nodes if n.name == name]
    loc = f"{path}.{name}" if path else name
    if not found:
        raise ConfigError(f"missing node: {loc}")
    if len(found) > 1 and name != "section":
        raise ConfigError(f"duplicate node: {loc}")
    return found[0]


def _first(nodes: Iterable[ckdl.Node], name: str) -> ckdl.Node | None:
    for node in nodes:
        if node.name == name:
            return node
    return None


def _child_arg(parent: ckdl.Node, name: str, path: str) -> Any:
    return _arg0(_require(parent.children, name, path), f"{path}.{name}")


def _arg0(node: ckdl.Node, path: str) -> Any:
    if not node.args:
        raise ConfigError(f"{path}: missing argument")
    if len(node.args) != 1:
        raise ConfigError(f"{path}: expected one argument")
    return _plain(node.args[0])


def _str_arg(node: ckdl.Node, path: str) -> str:
    return str(_arg0(node, path))


def _int_arg(node: ckdl.Node, path: str) -> int:
    value = _arg0(node, path)
    if isinstance(value, bool) or isinstance(value, float):
        raise ConfigError(f"{path}: expected integer")
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{path}: expected integer") from exc


def _bool_arg(node: ckdl.Node, path: str) -> bool:
    value = _arg0(node, path)
    if not isinstance(value, bool):
        raise ConfigError(f"{path}: expected #true or #false")
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, ckdl.Value):
        if value.type_annotation:
            return f"{value.value}{value.type_annotation}"
        return value.value
    return value


def _token(value: Any) -> str:
    return str(value)
