"""MOS sections → PlannerDoc. Reuses calendar, Configurator, Manifest, I18n."""

from __future__ import annotations

from typing import Any

from parch import ConfigError
from parch.calendar import walk
from parch.calendar.dated_note import DatedNote
from parch.calendar.day import Day
from parch.calendar.month import Month
from parch.calendar.quarter import Quarter
from parch.calendar.week import Week
from parch.config import StrictDict, _to_plain
from parch.i18n import I18n
from parch.ir.nodes import (
    AUTO,
    FR1,
    Anchor,
    Box,
    Cell,
    Col,
    DottedPad,
    Grid,
    Length,
    Node,
    Page,
    Row,
    Spacer,
    Stroke,
    Text,
)
from parch.ir.plan import PlannerDoc, Styles
from parch.ir.units import parse, parse_tracks
from parch.ir._sections import (
    build_colophon,
    build_habits,
    build_index,
    build_meetings,
    build_projects,
    build_review,
    build_tasks,
    reg_colophon,
    reg_habits,
    reg_index,
    reg_meetings,
    reg_projects,
    reg_review,
    reg_tasks,
)
from parch.ir.widgets import (
    daily_heading,
    first_present,
    frame,
    heading_text,
    little_calendar,
    maybe_link,
    month_week_rows,
    notes_block,
    priorities,
    schedule,
    weekday_row,
    with_week_column,
)
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest


def build_planner(dto: StrictDict | dict[str, Any], i18n: I18n) -> PlannerDoc:
    cfg = Configurator(dto)
    manifest = Manifest()
    ctx = _Ctx(cfg=cfg, i18n=i18n, manifest=manifest, styles=Styles.from_configurator(cfg))
    sections = [s for s in (_section(raw) for raw in cfg.enabled_sections()) if s is not None]
    for name, _build, _params, _register in sections:
        manifest.register_section(name)
    for _name, _build, params, register in sections:
        register(ctx, params)
    pages: list[Page] = []
    for _name, build, params, _register in sections:
        pages.extend(build(ctx, params))
    return PlannerDoc.from_configurator(cfg, pages, manifest)


class _Ctx:
    def __init__(self, cfg: Configurator, i18n: I18n, manifest: Manifest, styles: Styles) -> None:
        self.cfg = cfg
        self.i18n = i18n
        self.manifest = manifest
        self.styles = styles
        self.months = list(walk(cfg.start_date().month(), cfg.end_date().month()))
        self.quarters = list(walk(cfg.start_date().quarter(), cfg.end_date().quarter()))

    def framed(
        self,
        body: Node,
        *,
        page_id: str | None,
        title: Node | None,
        highlight_months: list | None = None,
        highlight_quarters: list | None = None,
        chrome: bool = True,
    ) -> Page:
        tree = body
        if chrome:
            tree = frame(
                styles=self.styles,
                body=body,
                title=title,
                page_id=page_id,
                highlight_months=highlight_months or [],
                highlight_quarters=highlight_quarters or [],
                i18n=self.i18n,
                manifest=self.manifest,
                months=self.months,
                quarters=self.quarters,
            )
        return Page(
            id=page_id,
            body=tree,
            title=title,
            highlight_months=list(highlight_months or []),
            highlight_quarters=list(highlight_quarters or []),
            chrome=chrome,
        )


def _section(dto: Any) -> tuple[str, Any, dict[str, Any], Any] | None:
    klass_name = dto["class"]
    section_name = dto["name"]
    params = dto.get("params", {}) if isinstance(dto, StrictDict) else (dto.get("params") or {})
    params = _to_plain(params) if isinstance(params, (StrictDict, dict)) else {}
    params = {str(k).replace("-", "_"): v for k, v in params.items()}
    pair = _SECTION.get(klass_name)
    if pair is None:
        return None
    builder, register = pair
    return str(section_name), builder, params, register


def _plain(value: Any) -> dict:
    if isinstance(value, StrictDict):
        return value.to_plain()
    if isinstance(value, dict):
        return _to_plain(value)
    return {}


def _little_params(ctx: _Ctx, extra: Any) -> dict[str, Any]:
    base = ctx.cfg.dig("planner", "params", "little_calendar") or {}
    return {**_plain(base), **_plain(extra)}


def _cover(ctx: _Ctx, params: dict[str, Any]) -> list[Page]:
    name = str(params.get("name", "Planner"))
    font_size = parse(params.get("font_size", "36pt"))
    body = Box(child=Text(name, size=font_size), align="center")
    return [ctx.framed(body, page_id=None, title=None, chrome=False)]


def _annual(ctx: _Ctx, params: dict[str, Any]) -> list[Page]:
    ctx.manifest.register_source("annual")
    little = _little_params(ctx, params.get("little_calendar"))
    row_gutter = parse(params.get("row_gutter", "5pt"))
    months = ctx.months
    cells = [
        little_calendar(
            i18n=ctx.i18n,
            manifest=ctx.manifest,
            month=month,
            week_placement=str(little.get("week_placement", "left")),
            inset=little.get("inset", "3pt"),
            show_month_name=bool(little.get("show_month_name", False)),
            styles=ctx.styles,
        )
        for month in months
    ]
    n = len(cells)
    rows_n = (n + 2) // 3
    body = Grid(
        cols=[FR1, FR1, FR1],
        rows=[FR1] * max(1, rows_n),
        cells=cells,
        gutter=(ctx.styles.regular_column_gutter, row_gutter),
    )
    title = heading_text("Calendar", ctx.styles, page_id="annual")
    return [ctx.framed(body, page_id="annual", title=title)]


def _quarterly(ctx: _Ctx, params: dict[str, Any]) -> list[Page]:
    little = _little_params(ctx, params.get("little_calendar"))
    months_column = str(params.get("months_column", "left")).lstrip(":").lower()
    out: list[Page] = []
    for quarter in ctx.quarters:
        ctx.manifest.register_source(quarter.id)
        cals = [
            little_calendar(
                i18n=ctx.i18n,
                manifest=ctx.manifest,
                month=month,
                week_placement=str(little.get("week_placement", "left")),
                inset=little.get("inset", "3pt"),
                show_month_name=bool(little.get("show_month_name", True)),
                styles=ctx.styles,
            )
            for month in quarter.months()
        ]
        stack = Col(children=cals, weights=[FR1] * len(cals), gap=parse("3mm"))
        pad = DottedPad()
        if months_column == "right":
            body = Row(children=[pad, stack], gap=ctx.styles.regular_column_gutter, weights=[Length.fr(3), Length.fr(2)])
        else:
            body = Row(children=[stack, pad], gap=ctx.styles.regular_column_gutter, weights=[Length.fr(2), Length.fr(3)])
        title = heading_text(f"{ctx.i18n.t('quarter.long')} {quarter.number}", ctx.styles, page_id=quarter.id)
        out.append(
            ctx.framed(
                body,
                page_id=quarter.id,
                title=title,
                highlight_quarters=[quarter],
            )
        )
    return out


def _monthly(ctx: _Ctx, params: dict[str, Any]) -> list[Page]:
    month_params = _plain(params.get("month_params") or {})
    placement = str(month_params.get("week_placement", "left")).lower()
    cell_h = parse(month_params.get("daily_cell_height", "16mm"))
    rot = 90.0
    raw_rot = str(month_params.get("week_label_rotation", "90deg"))
    if "270" in raw_rot or raw_rot.startswith("-") or "ccw" in raw_rot:
        rot = 270.0
    out: list[Page] = []
    for month in ctx.months:
        ctx.manifest.register_source(month.id)
        body = _monthly_body(ctx, month, placement, cell_h, rot)
        title = heading_text(ctx.i18n.t(f"months.full.{month.name}"), ctx.styles, page_id=month.id)
        out.append(
            ctx.framed(
                body,
                page_id=month.id,
                title=title,
                highlight_months=[month],
                highlight_quarters=[month.quarter()],
            )
        )
    return out


def _monthly_body(ctx: _Ctx, month: Month, placement: str, cell_h: Length, rot: float) -> Node:
    weeks = month_week_rows(month)
    headers = [ctx.i18n.t(f"weekday.full.{d.weekday_name}") for d in weekday_row(month)]
    show_week = placement in {"left", "right"}
    ncols = 8 if show_week else 7
    head_h = ctx.styles.regular_height
    stroke = Stroke(width=ctx.styles.regular_stroke)
    items: list[Node | Cell] = []
    head_cells = [Cell(Text(h), align="center") for h in headers]
    items.extend(with_week_column(head_cells, Cell(Spacer()), placement))
    for week in weeks:
        current = first_present(week).week()
        week_label: Node = Text(f'{ctx.i18n.t("week_name")} {current.number}')
        week_label = maybe_link(ctx.manifest, current.id, week_label)
        week_cell = Cell(
            Box(child=week_label, rotate=rot, align="center"),
            align="center",
            stroke=stroke,
        )
        day_cells: list[Node | Cell] = []
        for day in week:
            if day is None:
                day_cells.append(Cell(Spacer(), stroke=stroke))
                continue
            num: Node = Text(str(day.month_day))
            num = maybe_link(ctx.manifest, day.id, num)
            day_cells.append(
                Cell(
                    Box(
                        child=Box(
                            child=num,
                            stroke=stroke,
                            padding=parse("3pt"),
                            align="center",
                            min_w=Length.mm(6),
                            min_h=Length.mm(4.5),
                        ),
                        align="left",
                        padding=Length.mm(1),
                    ),
                    stroke=stroke,
                )
            )
        items.extend(with_week_column(day_cells, week_cell, placement))
    cal = Grid(
        cols=[FR1] * ncols,
        rows=[head_h] + [cell_h] * len(weeks),
        cells=items,
        align="center",
    )
    notes = notes_block(
        i18n=ctx.i18n,
        styles=ctx.styles,
        manifest=ctx.manifest,
        title=ctx.i18n.t("monthly_notes"),
    )
    return Col(
        children=[cal, notes],
        gap=ctx.styles.regular_column_gutter,
        weights=[AUTO, FR1],
    )


def _weeks(ctx: _Ctx) -> list[Week]:
    weekday_start = ctx.cfg.weekday_start()
    first = ctx.cfg.start_date().beginning_of_month().beginning_of_week()
    last = ctx.cfg.end_date().end_of_month().end_of_week()
    days = list(walk(first, last))
    weeks: list[Week] = []
    for i in range(0, len(days), 7):
        chunk = days[i : i + 7]
        if chunk:
            weeks.append(Week(weekday_start=weekday_start, day=chunk[0]))
    return weeks


def _weekly(ctx: _Ctx, params: dict[str, Any]) -> list[Page]:
    gutter = parse(params.get("column_gutter", "4pt"))
    thick = Stroke(width=ctx.styles.thick_stroke, sides=("bottom",))
    out: list[Page] = []
    for week in _weeks(ctx):
        ctx.manifest.register_source(week.id)
        days = week.days()
        head = Length.mm(4)

        def day_cell(day: Day) -> Cell:
            label: Node = Text(day.strftime("%A, %e").replace("  ", " "), align="left")
            label = maybe_link(ctx.manifest, day.id, label)
            return Cell(label, stroke=thick, align="horizon")

        cells: list[Node | Cell] = []
        # row 0: Mon Tue Wed
        cells.extend(day_cell(d) for d in days[0:3])
        # row 1: pad
        cells.append(Cell(DottedPad(), colspan=3))
        # row 2: Thu Fri Sat
        cells.extend(day_cell(d) for d in days[3:6])
        # row 3: pad
        cells.append(Cell(DottedPad(), colspan=3))
        # row 4: Sun + Notes
        cells.append(day_cell(days[6]))
        cells.append(Cell(Text(ctx.i18n.t("notes"), align="left"), colspan=2, stroke=thick, align="horizon"))
        # row 5: pad
        cells.append(Cell(DottedPad(), colspan=3))
        body = Grid(
            cols=[FR1, FR1, FR1],
            rows=[head, FR1, head, FR1, head, FR1],
            cells=cells,
            gutter=(gutter, Length.mm(0)),
        )
        title = heading_text(f"{ctx.i18n.t('week_name')} {week.number}", ctx.styles, page_id=week.id)
        out.append(
            ctx.framed(
                body,
                page_id=week.id,
                title=title,
                highlight_months=week.in_months(),
                highlight_quarters=week.in_quarters(),
            )
        )
    return out


def _daily(ctx: _Ctx, params: dict[str, Any]) -> list[Page]:
    weights = parse_tracks(params.get("columns_width", "(3fr, 5fr)"))
    if len(weights) < 2:
        weights = [Length.fr(3), Length.fr(5)]
    spacing = parse(params.get("items_spacing", "4mm"))
    out: list[Page] = []
    for day in walk(ctx.cfg.start_date(), ctx.cfg.end_date()):
        ctx.manifest.register_source(day.id)
        left = _daily_column(ctx, day, params.get("left_column") or [], spacing)
        right = _daily_column(ctx, day, params.get("right_column") or [], spacing)
        body = Row(
            children=[left, right],
            gap=ctx.styles.regular_column_gutter,
            weights=weights[:2],
        )
        title = daily_heading(day=day, i18n=ctx.i18n, manifest=ctx.manifest, styles=ctx.styles)
        out.append(
            ctx.framed(
                body,
                page_id=day.id,
                title=title,
                highlight_months=[day.month()],
                highlight_quarters=[day.quarter()],
            )
        )
    return out


def _daily_column(ctx: _Ctx, day: Day, comps: list[Any], spacing: Length) -> Node:
    pieces: list[Node] = []
    weights: list[Length] = []
    for comp in comps:
        data = _to_plain(comp) if isinstance(comp, (StrictDict, dict)) else dict(comp)
        if not data.get("enabled"):
            continue
        klass = data.get("class")
        p = data.get("params") or {}
        if isinstance(p, StrictDict):
            p = p.to_plain()
        if klass == "schedule":
            pieces.append(
                schedule(
                    i18n=ctx.i18n,
                    styles=ctx.styles,
                    from_hour=int(p.get("from", 8)),
                    to_hour=int(p.get("to", 20)),
                    trailing_30=bool(p.get("trailing_30_minutes", True)),
                    time_format=str(p.get("time_format", "%k")),
                )
            )
            weights.append(AUTO)
        elif klass in {"top_priorities", "priorities"}:
            pieces.append(priorities(i18n=ctx.i18n, styles=ctx.styles, number=int(p.get("number", 5))))
            weights.append(AUTO)
        elif klass == "notes":
            note_id = DatedNote(weekday_start=day.weekday_start, day=day).id
            th = parse(p["title_height"]) if p.get("title_height") else ctx.styles.regular_height
            nh = parse(p["notes_height"]) if p.get("notes_height") else FR1
            pieces.append(
                notes_block(
                    i18n=ctx.i18n,
                    styles=ctx.styles,
                    manifest=ctx.manifest,
                    more_target=note_id,
                    title_height=th,
                    notes_height=nh,
                )
            )
            weights.append(nh if nh.unit == "fr" else FR1)
        elif klass == "little_calendar":
            pieces.append(
                little_calendar(
                    i18n=ctx.i18n,
                    manifest=ctx.manifest,
                    month=day.month(),
                    week_placement=str(p.get("week_placement", "left")),
                    inset=p.get("inset", "3pt"),
                    show_month_name=bool(p.get("show_month_name", False)),
                    today=day,
                    styles=ctx.styles,
                )
            )
            weights.append(FR1)
        else:
            raise ConfigError(f"unknown component: {klass}")
    if not pieces:
        return Spacer()
    return Col(children=pieces, gap=spacing, weights=weights)


def _daily_notes(ctx: _Ctx, params: dict[str, Any]) -> list[Page]:
    pages_num = int(params.get("pages", 1))
    out: list[Page] = []
    for day in walk(ctx.cfg.start_date(), ctx.cfg.end_date()):
        for page_num in range(1, pages_num + 1):
            note = DatedNote(day=day, weekday_start=day.weekday_start, page=page_num)
            ctx.manifest.register_source(note.id)
            title = daily_heading(
                day=day,
                i18n=ctx.i18n,
                manifest=ctx.manifest,
                styles=ctx.styles,
                note_id=note.id,
            )
            out.append(
                ctx.framed(
                    DottedPad(),
                    page_id=note.id,
                    title=title,
                    highlight_months=[day.month()],
                    highlight_quarters=[day.quarter()],
                )
            )
    return out


def _reg_cover(_ctx: _Ctx, _params: dict[str, Any]) -> None:
    return None


def _reg_annual(ctx: _Ctx, _params: dict[str, Any]) -> None:
    ctx.manifest.register_source("annual")


def _reg_quarterly(ctx: _Ctx, _params: dict[str, Any]) -> None:
    for quarter in ctx.quarters:
        ctx.manifest.register_source(quarter.id)


def _reg_monthly(ctx: _Ctx, _params: dict[str, Any]) -> None:
    for month in ctx.months:
        ctx.manifest.register_source(month.id)


def _reg_weekly(ctx: _Ctx, _params: dict[str, Any]) -> None:
    for week in _weeks(ctx):
        ctx.manifest.register_source(week.id)


def _reg_daily(ctx: _Ctx, _params: dict[str, Any]) -> None:
    for day in walk(ctx.cfg.start_date(), ctx.cfg.end_date()):
        ctx.manifest.register_source(day.id)


def _reg_daily_notes(ctx: _Ctx, params: dict[str, Any]) -> None:
    pages_num = int(params.get("pages", 1))
    for day in walk(ctx.cfg.start_date(), ctx.cfg.end_date()):
        for page_num in range(1, pages_num + 1):
            note = DatedNote(day=day, weekday_start=day.weekday_start, page=page_num)
            ctx.manifest.register_source(note.id)


_SECTION = {
    "cover_plain": (_cover, _reg_cover),
    "index": (build_index, reg_index),
    "annual": (_annual, _reg_annual),
    "quarterly": (_quarterly, _reg_quarterly),
    "monthly": (_monthly, _reg_monthly),
    "weekly": (_weekly, _reg_weekly),
    "daily": (_daily, _reg_daily),
    "daily_notes": (_daily_notes, _reg_daily_notes),
    "projects": (build_projects, reg_projects),
    "habits": (build_habits, reg_habits),
    "review": (build_review, reg_review),
    "tasks": (build_tasks, reg_tasks),
    "meetings": (build_meetings, reg_meetings),
    "colophon": (build_colophon, reg_colophon),
}
