"""IR builders for index / projects / habits / review / tasks / meetings / colophon."""

from __future__ import annotations

import math
from typing import Any

from parch import __version__
from parch.calendar import walk
from parch.calendar.day import Day
from parch.calendar.month import Month
from parch.calendar.week import Week
from parch.config import StrictDict, _to_plain
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
from parch.ir.units import parse, to_mm
from parch.ir.widgets import (
    lead_title,
    lined_pad,
    maybe_link,
    ticked_field,
    ticked_lines,
    trail_strip,
)
from parch.sections.colophon import DEFAULT_TITLE, drop_empty_tables, _human_device

_INDEX_SKIP = frozenset({"cover", "index", "daily_notes"})
_INDEX_HUMAN = {
    "annual": "Calendar",
    "quarterly": "Quarters",
    "monthly": "Months",
    "weekly": "Weeks",
    "daily": "Days",
    "projects": "Projects",
    "habits": "Habits",
    "review": "Review",
    "tasks": "Tasks",
    "meetings": "Meetings",
    "colophon": "About this notebook",
}
_EN_DASH = "\u2013"
_MIN_PACK_ROWS = 12
_MAX_PACK_ROWS = 14
_DEFAULT_WEEKS_PER_PAGE = 13
_HABIT_HEADER_H = parse("16mm")
_NUM_COL = parse("16pt")
_DATE_COL = parse("16mm")
_DAY_STRIP_H = parse("8mm")
_TOPIC_LINES = 4
_ACTION_LINES = 5
_ROW_HEIGHT_MULT = 2
_INDEX_PAD = parse("4mm")
_INDEX_GUTTER = parse("3mm")


def _weeks(ctx) -> list[Week]:
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


def _index_available_mm(ctx) -> float:
    page_h = to_mm(parse(ctx.cfg.dig_bang("document", "layout", "dimensions", "height")))
    top = to_mm(parse(ctx.cfg.dig_bang("document", "layout", "margin", "top")))
    bottom = to_mm(parse(ctx.cfg.dig_bang("document", "layout", "margin", "bottom")))
    h1 = to_mm(ctx.styles.h1)
    return page_h - top - bottom - h1 - to_mm(_INDEX_PAD) - to_mm(_INDEX_GUTTER)


def _rows_per_index_page(ctx) -> int:
    available = _index_available_mm(ctx)
    row = _ROW_HEIGHT_MULT * to_mm(ctx.styles.regular_height)
    if row <= 0:
        return 1
    return max(1, math.floor(available / row))


def _raw_stack(heads: list[Node], body: Node, *, gap: Length | None = None) -> Node:
    g = gap if gap is not None else _INDEX_GUTTER
    children = [*heads, body]
    weights = [AUTO] * len(heads) + [FR1]
    return Box(child=Col(children=children, gap=g, weights=weights), padding=_INDEX_PAD)


def _year_node(ctx) -> Node:
    return maybe_link(ctx.manifest, "annual", Text(str(ctx.cfg.start_date().year), size=ctx.styles.h1))


def _year_crumb(ctx, section: Node) -> Node:
    crumb = Row(
        children=[_year_node(ctx), Text("/", size=ctx.styles.h1), section],
        gap=parse("6pt"),
        weights=[AUTO, AUTO, AUTO],
    )
    return lead_title(title=crumb, manifest=ctx.manifest, styles=ctx.styles)


def _dest_id(ctx, name: str) -> str:
    if name == "annual":
        return "annual"
    if name == "quarterly":
        return ctx.cfg.start_date().quarter().id
    if name == "monthly":
        return ctx.cfg.start_date().month().id
    if name == "weekly":
        first = ctx.cfg.start_date().beginning_of_month().beginning_of_week()
        return Week(weekday_start=ctx.cfg.weekday_start(), day=first).id
    if name == "daily":
        return ctx.cfg.start_date().id
    return name


def build_index(ctx, _params: dict[str, Any]) -> list[Page]:
    names = [
        str(section["name"])
        for section in ctx.cfg.enabled_sections()
        if str(section["name"]) not in _INDEX_SKIP and str(section["name"]) in _INDEX_HUMAN
    ]
    height = Length.mm(max(_index_available_mm(ctx) / 12.0, 8.0))
    cells: list[Node | Cell] = []
    for name in names:
        dest = _dest_id(ctx, name)
        label: Node = Text(_INDEX_HUMAN[name], align="left")
        label = maybe_link(ctx.manifest, dest, label)
        cells.append(Cell(label, align="horizon"))
    body: Node = Grid(cols=[FR1], rows=[height] * len(cells), cells=cells, inset=parse("4pt")) if cells else Spacer()
    title = Anchor("index", Text("Contents", size=ctx.styles.h1, bold=True))
    return [ctx.framed(_raw_stack([title], body), page_id="index", title=title, chrome=False)]


def reg_index(ctx, _params: dict[str, Any]) -> None:
    ctx.manifest.register_source("index")



def _projects_ids(ctx, params: dict[str, Any]) -> tuple[int, int, int]:
    pages_num = int(params.get("pages", 16))
    rpp = _rows_per_index_page(ctx)
    n_index = 1 if pages_num <= 0 else math.ceil(pages_num / rpp)
    return pages_num, rpp, n_index


def _projects_index_id(page: int) -> str:
    return "projects" if page <= 1 else f"projects-{page}"


def _project_board_id(index: int) -> str:
    return f"project-{index}"


def build_projects(ctx, params: dict[str, Any]) -> list[Page]:
    pages_num, rpp, n_index = _projects_ids(ctx, params)
    out: list[Page] = []
    for page in range(1, n_index + 1):
        start = (page - 1) * rpp + 1
        end = min(page * rpp, pages_num)
        out.append(_projects_index_page(ctx, page, start, end))
    for index in range(1, pages_num + 1):
        parent = _projects_index_id((index - 1) // rpp + 1)
        out.append(_projects_board_page(ctx, index, parent))
    return out


def reg_projects(ctx, params: dict[str, Any]) -> None:
    pages_num, _rpp, n_index = _projects_ids(ctx, params)
    for page in range(1, n_index + 1):
        ctx.manifest.register_source(_projects_index_id(page))
    for index in range(1, pages_num + 1):
        ctx.manifest.register_source(_project_board_id(index))


def _projects_heading(ctx, projects_cell: Node) -> Node:
    """Unglue Contents mark (trail strip) from the Projects title."""
    mark = trail_strip(manifest=ctx.manifest, styles=ctx.styles, chip=None)
    if mark is None:
        return projects_cell
    return Row(children=[mark, Spacer(), projects_cell], weights=[AUTO, FR1, AUTO])


def _projects_index_page(ctx, page: int, start: int, end: int) -> Page:
    page_id = _projects_index_id(page)
    label: Node = Text(ctx.i18n.t("projects"), size=ctx.styles.h1)
    if page > 1:
        label = maybe_link(ctx.manifest, "projects", label)
    label = Anchor(page_id, label)
    title = _projects_heading(ctx, label)
    n = max(0, end - start + 1)
    row_h = Length.mm(_ROW_HEIGHT_MULT * to_mm(ctx.styles.regular_height))
    stroke = Stroke(width=ctx.styles.regular_stroke, sides=("bottom",))
    cells: list[Node | Cell] = []
    for index in range(start, end + 1):
        # Whole-row hit: number + write-in band share one link target.
        inner = Grid(
            cols=[_NUM_COL, FR1],
            rows=[FR1],
            cells=[
                Cell(Text(str(index), align="left"), align="horizon"),
                Cell(Spacer()),
            ],
            inset=Length.pt(0),
        )
        band: Node = Box(child=inner)
        band = maybe_link(ctx.manifest, _project_board_id(index), band)
        cells.append(Cell(band, align="horizon", stroke=stroke))
    body: Node
    if n:
        body = Grid(cols=[FR1], rows=[row_h] * n, cells=cells, inset=parse("4pt"))
    else:
        body = Spacer()
    return ctx.framed(_raw_stack([title], body), page_id=page_id, title=title, chrome=False)


def _projects_board_page(ctx, index: int, parent: str) -> Page:
    bid = _project_board_id(index)
    label = maybe_link(ctx.manifest, parent, Text(ctx.i18n.t("projects"), size=ctx.styles.h1))
    title = _projects_heading(ctx, label)
    quiet = Anchor(bid, Text(str(index), size=ctx.styles.text_size))
    name_line = Box(stroke=Stroke(width=ctx.styles.regular_stroke, sides=("bottom",)))
    heads = [
        Cell(Text(ctx.i18n.t("todo"), bold=True), align="center"),
        Cell(Text(ctx.i18n.t("doing"), bold=True), align="center"),
        Cell(Text(ctx.i18n.t("done"), bold=True), align="center"),
    ]
    kanban = Grid(
        cols=[FR1, FR1, FR1],
        rows=[AUTO, FR1],
        cells=[*heads, DottedPad(), DottedPad(), DottedPad()],
        gutter=(ctx.styles.regular_column_gutter, parse("2mm")),
    )
    return ctx.framed(
        _raw_stack([title, quiet, name_line], kanban, gap=parse("2.5mm")),
        page_id=bid,
        title=title,
        chrome=False,
    )



def _habit_month_id(month: Month) -> str:
    return f"habits-{month.name}"


def build_habits(ctx, params: dict[str, Any]) -> list[Page]:
    n_habits = int(params.get("habit_columns", 6))
    names = list(params.get("names") or [])
    months = list(ctx.months)
    out = [_habits_index(ctx, months)]
    for month in months:
        out.append(_habits_month(ctx, month, n_habits, names))
    return out


def reg_habits(ctx, _params: dict[str, Any]) -> None:
    ctx.manifest.register_source("habits")
    for month in ctx.months:
        ctx.manifest.register_source(_habit_month_id(month))


def _habits_index(ctx, months: list[Month]) -> Page:
    label = Anchor("habits", Text(ctx.i18n.t("habits"), size=ctx.styles.h1))
    title = _year_crumb(ctx, label)
    stroke = Stroke(width=ctx.styles.regular_stroke, sides=("bottom",))
    cells: list[Node | Cell] = []
    for month in months:
        name: Node = Text(ctx.i18n.t(f"months.full.{month.name}"), align="left")
        name = maybe_link(ctx.manifest, _habit_month_id(month), name)
        cells.append(Cell(name, align="horizon", stroke=stroke))
    body: Node
    if cells:
        body = Grid(cols=[FR1], rows=[FR1] * len(cells), cells=cells, inset=parse("4pt"))
    else:
        body = Spacer()
    return ctx.framed(_raw_stack([title], body), page_id="habits", title=title, chrome=False)


def _habits_month(ctx, month: Month, n_habits: int, names: list[str]) -> Page:
    page_id = _habit_month_id(month)
    year = maybe_link(ctx.manifest, "annual", Text(str(month.day.year), size=ctx.styles.h1))
    habits = maybe_link(ctx.manifest, "habits", Text(ctx.i18n.t("habits"), size=ctx.styles.h1))
    full = Anchor(page_id, Text(ctx.i18n.t(f"months.full.{month.name}"), size=ctx.styles.h1))
    title = Row(
        children=[year, Text("/", size=ctx.styles.h1), habits, Text("/", size=ctx.styles.h1), full],
        gap=parse("6pt"),
        weights=[AUTO, AUTO, AUTO, AUTO, AUTO],
    )
    days = list(walk(month.day, month.day.end_of_month()))
    padded = (list(names) + [""] * n_habits)[:n_habits]
    stroke = Stroke(width=ctx.styles.regular_stroke)
    headers: list[Node | Cell] = [Cell(Spacer(), stroke=stroke)]
    for name in padded:
        if name:
            headers.append(Cell(Text(name), align="center", stroke=stroke))
        else:
            headers.append(Cell(Spacer(), stroke=stroke))
    cells: list[Node | Cell] = list(headers)
    rows: list[Length] = [_HABIT_HEADER_H]
    for day in days:
        short = ctx.i18n.t(f"weekday.short.{day.weekday_name}")
        label: Node = Text(f"{short} {day.month_day}", align="right")
        label = maybe_link(ctx.manifest, day.id, label)
        cells.append(Cell(label, align="horizon"))
        cells.extend(Cell(Spacer(), stroke=stroke) for _ in range(n_habits))
        rows.append(FR1)
        if day.weekday_name == "friday":
            cells.append(Cell(Spacer(), colspan=1 + n_habits, fill="black"))
            rows.append(Length.mm(0.4))
    grid = Grid(cols=[AUTO] + [FR1] * n_habits, rows=rows, cells=cells)
    return ctx.framed(
        grid,
        page_id=page_id,
        title=title,
        highlight_months=[month],
        highlight_quarters=[month.quarter()],
        chrome=True,
    )



def _week_page_sizes(n_weeks: int, weeks_per_page: int) -> list[int]:
    n = weeks_per_page
    if n < 1:
        raise ValueError("weeks_per_page must be at least 1")
    if n_weeks <= 0:
        return [0]
    sizes = [n] * (n_weeks // n)
    rem = n_weeks % n
    if rem:
        sizes.append(rem)
    if len(sizes) >= 2 and sizes[-1] < _MIN_PACK_ROWS and sizes[-2] + sizes[-1] <= _MAX_PACK_ROWS:
        sizes[-2] += sizes[-1]
        sizes.pop()
    return sizes


def _week_chunks(weeks: list[Week], weeks_per_page: int) -> list[list[Week]]:
    sizes = _week_page_sizes(len(weeks), weeks_per_page)
    out: list[list[Week]] = []
    i = 0
    for size in sizes:
        out.append(weeks[i : i + size])
        i += size
    return out


def _range_label(ctx, first: Day, last: Day) -> str:
    first_month = ctx.i18n.t(f"months.short.{first.month().name}")
    last_month = ctx.i18n.t(f"months.short.{last.month().name}")
    if first.day.month == last.day.month and first.day.year == last.day.year:
        return f"{first_month} {first.month_day} {_EN_DASH} {last.month_day}"
    return f"{first_month} {first.month_day} {_EN_DASH} {last_month} {last.month_day}"


def _review_index_id(page_index: int) -> str:
    return "review" if page_index == 0 else f"review-{page_index + 1}"


def _review_week_id(week: Week) -> str:
    return f"review-{week.id}"


def _tasks_index_id(page_index: int) -> str:
    return "tasks" if page_index == 0 else f"tasks-{page_index + 1}"


def _tasks_week_id(week: Week) -> str:
    return f"tasks-{week.id}"


def _week_index_body(ctx, weeks: list[Week], week_id) -> Node:
    n = len(weeks)
    if not n:
        return Spacer()
    stroke = Stroke(width=ctx.styles.regular_stroke, sides=("bottom",))
    cells: list[Node | Cell] = []
    for week in weeks:
        days = week.days()
        rng = _range_label(ctx, days[0], days[-1])
        inner = Row(
            children=[Text(str(week.number)), Text(rng, size=ctx.styles.text_size)],
            gap=parse("4pt"),
            weights=[_NUM_COL, FR1],
        )
        cells.append(Cell(maybe_link(ctx.manifest, week_id(week), inner), align="horizon", stroke=stroke))
    inner_grid = Grid(cols=[FR1], rows=[FR1] * n, cells=cells, inset=parse("4pt"))
    if n >= _MIN_PACK_ROWS or n >= _DEFAULT_WEEKS_PER_PAGE:
        return inner_grid
    empty = max(1, _DEFAULT_WEEKS_PER_PAGE - n)
    return Grid(cols=[FR1], rows=[Length.fr(n), Length.fr(empty)], cells=[inner_grid, Spacer()])


def build_review(ctx, params: dict[str, Any]) -> list[Page]:
    weeks_per_page = int(params.get("weeks_per_page", _DEFAULT_WEEKS_PER_PAGE))
    pattern = str(params.get("pattern") or "lined")
    weeks = _weeks(ctx)
    chunks = _week_chunks(weeks, weeks_per_page)
    out: list[Page] = []
    for index, chunk in enumerate(chunks):
        page_id = _review_index_id(index)
        label = Anchor(page_id, Text(ctx.i18n.t("review"), size=ctx.styles.h1))
        title = _year_crumb(ctx, label)
        if chunk:
            quiet: Node = Text(_range_label(ctx, chunk[0].days()[0], chunk[-1].days()[-1]), size=ctx.styles.text_size)
        else:
            quiet = Spacer()
        body = _week_index_body(ctx, chunk, _review_week_id)
        out.append(ctx.framed(_raw_stack([title, quiet], body), page_id=page_id, title=title, chrome=False))
    for index, chunk in enumerate(chunks):
        parent = _review_index_id(index)
        for week in chunk:
            out.append(_review_week_page(ctx, week, parent, pattern))
    return out


def reg_review(ctx, params: dict[str, Any]) -> None:
    weeks = _weeks(ctx)
    weeks_per_page = int(params.get("weeks_per_page", _DEFAULT_WEEKS_PER_PAGE))
    for index in range(len(_week_page_sizes(len(weeks), weeks_per_page))):
        ctx.manifest.register_source(_review_index_id(index))
    for week in weeks:
        ctx.manifest.register_source(_review_week_id(week))


def _review_week_page(ctx, week: Week, parent: str, pattern: str) -> Page:
    page_id = _review_week_id(week)
    days = week.days()
    rng = _range_label(ctx, days[0], days[-1])
    label = maybe_link(ctx.manifest, parent, Text(ctx.i18n.t("review"), size=ctx.styles.h1))
    title = _year_crumb(ctx, label)
    week_line = Row(
        children=[Anchor(page_id, Text(str(week.number))), Text(rng, size=ctx.styles.text_size)],
        gap=parse("6pt"),
        weights=[AUTO, AUTO],
    )
    strip_cells: list[Node | Cell] = []
    for day in days:
        short = ctx.i18n.t(f"weekday.short.{day.weekday_name}")
        cell: Node = Text(f"{short} {day.month_day}")
        strip_cells.append(Cell(maybe_link(ctx.manifest, day.id, cell), align="center"))
    strip = Grid(cols=[FR1] * 7, rows=[_DAY_STRIP_H], cells=strip_cells, inset=parse("2pt"))
    ruled = Box(child=strip, stroke=Stroke(width=ctx.styles.regular_stroke, sides=("bottom",)))
    field: Node = DottedPad() if pattern == "dotted" else lined_pad(styles=ctx.styles)
    return ctx.framed(_raw_stack([title, week_line, ruled], field), page_id=page_id, title=title, chrome=False)


def build_tasks(ctx, params: dict[str, Any]) -> list[Page]:
    weeks_per_page = int(params.get("weeks_per_page", _DEFAULT_WEEKS_PER_PAGE))
    weeks = _weeks(ctx)
    chunks = _week_chunks(weeks, weeks_per_page)
    out: list[Page] = []
    for index, chunk in enumerate(chunks):
        page_id = _tasks_index_id(index)
        label = Anchor(page_id, Text(ctx.i18n.t("tasks"), size=ctx.styles.h1))
        title = _year_crumb(ctx, label)
        body = _week_index_body(ctx, chunk, _tasks_week_id)
        out.append(ctx.framed(_raw_stack([title], body), page_id=page_id, title=title, chrome=False))
    for index, chunk in enumerate(chunks):
        parent = _tasks_index_id(index)
        for week in chunk:
            out.append(_tasks_week_page(ctx, week, parent))
    return out


def reg_tasks(ctx, params: dict[str, Any]) -> None:
    weeks = _weeks(ctx)
    weeks_per_page = int(params.get("weeks_per_page", _DEFAULT_WEEKS_PER_PAGE))
    for index in range(len(_week_page_sizes(len(weeks), weeks_per_page))):
        ctx.manifest.register_source(_tasks_index_id(index))
    for week in weeks:
        ctx.manifest.register_source(_tasks_week_id(week))


def _tasks_week_page(ctx, week: Week, parent: str) -> Page:
    page_id = _tasks_week_id(week)
    days = week.days()
    rng = _range_label(ctx, days[0], days[-1])
    label = maybe_link(ctx.manifest, parent, Text(ctx.i18n.t("tasks"), size=ctx.styles.h1))
    title = _year_crumb(ctx, label)
    week_label: Node = Text(f"{ctx.i18n.t('week_name')} {week.number}")
    week_label = maybe_link(ctx.manifest, week.id, week_label)
    quiet = Row(children=[week_label, Text(rng, size=ctx.styles.text_size)], gap=parse("6pt"), weights=[AUTO, AUTO])
    bottom = Stroke(width=ctx.styles.regular_stroke, sides=("bottom",))
    strip_cells: list[Node | Cell] = []
    for day in days:
        full = ctx.i18n.t(f"weekday.full.{day.weekday_name}")
        cell: Node = Text(f"{full} {day.month_day}", size=Length.pt(6))
        cell = maybe_link(ctx.manifest, day.id, cell)
        strip_cells.append(Cell(Box(child=cell, stroke=bottom, align="center"), align="center"))
    strip = Grid(cols=[FR1] * 7, rows=[_DAY_STRIP_H], cells=strip_cells)
    rh = max(to_mm(ctx.styles.regular_height), 0.1)
    n_rows = max(8, int(_index_available_mm(ctx) / rh) - 4)
    field = ticked_field(styles=ctx.styles, rows=n_rows)
    tree = Box(
        child=Col(
            children=[Anchor(page_id, Spacer()), title, quiet, strip, field],
            gap=_INDEX_GUTTER,
            weights=[AUTO, AUTO, AUTO, AUTO, FR1],
        ),
        padding=_INDEX_PAD,
    )
    return ctx.framed(tree, page_id=page_id, title=title, chrome=False)



def _meetings_ids(ctx, params: dict[str, Any]) -> tuple[int, int, int]:
    index_pages = max(1, int(params.get("index_pages", 1)))
    rpp = _rows_per_index_page(ctx)
    return rpp * index_pages, rpp, index_pages


def _meetings_index_id(page: int) -> str:
    return "meetings" if page <= 1 else f"meetings-{page}"


def _meeting_id(index: int) -> str:
    return f"meeting-{index}"


def build_meetings(ctx, params: dict[str, Any]) -> list[Page]:
    pages_num, rpp, n_index = _meetings_ids(ctx, params)
    out: list[Page] = []
    for page in range(1, n_index + 1):
        start = (page - 1) * rpp + 1
        end = page * rpp
        out.append(_meetings_index_page(ctx, page, start, end))
    for index in range(1, pages_num + 1):
        parent = _meetings_index_id((index - 1) // rpp + 1)
        out.append(_meeting_page(ctx, index, pages_num, parent))
    return out


def reg_meetings(ctx, params: dict[str, Any]) -> None:
    pages_num, _rpp, n_index = _meetings_ids(ctx, params)
    for page in range(1, n_index + 1):
        ctx.manifest.register_source(_meetings_index_id(page))
    for index in range(1, pages_num + 1):
        ctx.manifest.register_source(_meeting_id(index))


def _meetings_index_page(ctx, page: int, start: int, end: int) -> Page:
    page_id = _meetings_index_id(page)
    label: Node = Text(ctx.i18n.t("meetings"), size=ctx.styles.h1)
    if page > 1:
        label = maybe_link(ctx.manifest, "meetings", label)
    label = Anchor(page_id, label)
    title = _year_crumb(ctx, label)
    n = max(0, end - start + 1)
    stroke = Stroke(width=ctx.styles.regular_stroke, sides=("bottom",))
    cells: list[Node | Cell] = []
    for index in range(start, end + 1):
        num: Node = Text(str(index), align="left")
        num = maybe_link(ctx.manifest, _meeting_id(index), num)
        cells.append(Cell(num, align="horizon", stroke=stroke))
        cells.append(Cell(Spacer(), stroke=stroke))
    body: Node = Grid(cols=[_NUM_COL, FR1], rows=[FR1] * n, cells=cells, inset=parse("4pt")) if n else Spacer()
    return ctx.framed(_raw_stack([title], body), page_id=page_id, title=title, chrome=False)


def _meeting_page(ctx, index: int, pages_num: int, parent: str) -> Page:
    mid = _meeting_id(index)
    label = maybe_link(ctx.manifest, parent, Text(ctx.i18n.t("meetings"), size=ctx.styles.h1))
    title = _year_crumb(ctx, label)
    name_line = Grid(
        cols=[FR1, _DATE_COL, AUTO],
        rows=[ctx.styles.regular_height],
        cells=[
            Cell(Spacer(), stroke=Stroke(width=ctx.styles.regular_stroke, sides=("bottom",))),
            Cell(Spacer(), stroke=Stroke(width=ctx.styles.regular_stroke, sides=("bottom",))),
            Cell(Anchor(mid, Text(f"{index}/{pages_num}", size=ctx.styles.text_size)), align="horizon"),
        ],
        gutter=(parse("6pt"), Length.mm(0)),
    )
    topics = Col(
        children=[Text(ctx.i18n.t("topics")), ticked_lines(styles=ctx.styles, rows=_TOPIC_LINES)],
        gap=parse("1.5mm"),
        weights=[AUTO, AUTO],
    )
    actions = Col(
        children=[Text(ctx.i18n.t("action_items")), ticked_lines(styles=ctx.styles, rows=_ACTION_LINES)],
        gap=parse("1.5mm"),
        weights=[AUTO, AUTO],
    )
    tree = Box(
        child=Col(
            children=[title, name_line, topics, Text(ctx.i18n.t("notes")), lined_pad(styles=ctx.styles), actions],
            gap=parse("2.5mm"),
            weights=[AUTO, AUTO, AUTO, AUTO, FR1, AUTO],
        ),
        padding=_INDEX_PAD,
    )
    return ctx.framed(tree, page_id=mid, title=title, chrome=False)


def build_colophon(ctx, params: dict[str, Any]) -> list[Page]:
    title_text = str(params.get("title") or DEFAULT_TITLE)
    dump = bool(params.get("dump"))
    command = bool(params.get("command"))
    sha = bool(params.get("sha"))
    heading = Anchor("colophon", Text(title_text, size=ctx.styles.h1, bold=True))
    title = lead_title(title=heading, manifest=ctx.manifest, styles=ctx.styles)
    device = _human_device(str(ctx.cfg.dig("device") or ""))
    rows = [
        _colo_fact("Device", Text(device)),
        _colo_fact("Year", _year_node(ctx)),
        _colo_fact("Version", Text(__version__)),
    ]
    if command:
        rows.append(_colo_fact("Command", Text(_prov_field(ctx, "command"))))
    if sha:
        rows.append(_colo_fact("SHA-256", Text(_prov_field(ctx, "config_sha256"))))
    facts = Col(children=rows, gap=Length.mm(0), weights=[ctx.styles.regular_height] * len(rows))
    pieces: list[Node] = [title, facts]
    weights: list[Length] = [AUTO, AUTO]
    if dump:
        dumped = drop_empty_tables(_prov_field(ctx, "config_text"))
        if dumped.strip():
            pieces.append(Text(dumped))
            weights.append(FR1)
    body = Col(children=pieces, gap=parse("4mm"), weights=weights)
    return [ctx.framed(body, page_id="colophon", title=title, chrome=False)]


def reg_colophon(ctx, _params: dict[str, Any]) -> None:
    ctx.manifest.register_source("colophon")


def _colo_fact(label: str, value: Node) -> Node:
    return Row(children=[Text(label, bold=True), value], gap=parse("8pt"), weights=[AUTO, FR1])


def _prov_field(ctx, key: str) -> str:
    raw = ctx.cfg.dig("planner", "params", "provenance")
    if isinstance(raw, StrictDict):
        data = raw.to_plain()
    elif isinstance(raw, dict):
        data = _to_plain(raw)
    else:
        data = {}
    value = data.get(key)
    return "" if value is None else str(value)
