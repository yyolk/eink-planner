"""Helpers that return layout trees. No painter knowledge."""

from __future__ import annotations

from typing import Any, Iterable

from parch.calendar.day import Day
from parch.calendar.month import Month
from parch.calendar.quarter import Quarter
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
    Link,
    Node,
    Row,
    Spacer,
    Stroke,
    Text,
)
from parch.ir.plan import Styles
from parch.ir.units import parse
from parch.mos.manifest import Manifest


def maybe_link(manifest: Manifest, target_id: str | None, child: Node) -> Node:
    if target_id and manifest.source(target_id):
        return Link(target_id, child)
    return child


def heading_text(text: str, styles: Styles, page_id: str | None = None) -> Node:
    node: Node = Text(text, size=styles.h1)
    if page_id:
        node = Anchor(page_id, node)
    return node


def frame(
    *,
    styles: Styles,
    body: Node,
    title: Node | None,
    page_id: str | None,
    highlight_months: Iterable[Any],
    highlight_quarters: Iterable[Any],
    i18n: I18n,
    manifest: Manifest,
    months: list[Month],
    quarters: list[Quarter],
) -> Node:
    """Chrome + body as one tree. Painters should not add a side channel."""
    menu = side_menu(
        styles=styles,
        i18n=i18n,
        manifest=manifest,
        months=months,
        quarters=quarters,
        highlight_months=list(highlight_months),
        highlight_quarters=list(highlight_quarters),
    )
    head = heading_bar(title=title, page_id=page_id, styles=styles, manifest=manifest)
    if styles.side_menu_position == "right":
        cols = [FR1, styles.side_menu_width]
        cells: list[Cell] = [
            Cell(head, col=0, row=0),
            Cell(menu, col=1, row=0, rowspan=2),
            Cell(body, col=0, row=1),
        ]
    else:
        cols = [styles.side_menu_width, FR1]
        cells = [
            Cell(menu, col=0, row=0, rowspan=2),
            Cell(head, col=1, row=0),
            Cell(body, col=1, row=1),
        ]
    return Grid(
        cols=cols,
        rows=[styles.heading_height, FR1],
        cells=cells,
        gutter=(styles.column_gutter, styles.row_gutter),
    )


def heading_bar(
    *,
    title: Node | None,
    page_id: str | None,
    styles: Styles,
    manifest: Manifest,
) -> Node:
    calendar: Node = Text("Calendar")
    if page_id == "annual":
        calendar = Text("Calendar", color="white", bold=True)
        calendar = Box(child=calendar, fill="black", align="center", padding=parse("4pt"))
    calendar = maybe_link(manifest, "annual", calendar)
    title_node = title if title is not None else Spacer()
    # Calendar on the inner (menu) side, title opposite — matches MOS stack(rtl).
    if styles.side_menu_position == "right":
        children = [title_node, calendar]
        weights = [FR1, AUTO]
    else:
        children = [calendar, title_node]
        weights = [AUTO, FR1]
    return Row(children=children, gap=parse("2pt"), weights=weights)


def side_menu(
    *,
    styles: Styles,
    i18n: I18n,
    manifest: Manifest,
    months: list[Month],
    quarters: list[Quarter],
    highlight_months: list[Any],
    highlight_quarters: list[Any],
) -> Node:
    months = list(months)
    quarters = list(quarters)
    if styles.reverse_mq_items:
        months = list(reversed(months))
        quarters = list(reversed(quarters))
    month_ids = {m.id for m in highlight_months}
    quarter_ids = {q.id for q in highlight_quarters}
    month_col = _menu_strip(
        items=[(i18n.t(f"months.short.{m.name}"), m.id, m.id in month_ids) for m in months],
        styles=styles,
        manifest=manifest,
    )
    quarter_col = _menu_strip(
        items=[
            (f"{i18n.t('quarter.short')}{q.number}", q.id, q.id in quarter_ids) for q in quarters
        ],
        styles=styles,
        manifest=manifest,
    )
    # Visual order after 270°: fpdf2 draws months/quarters as a vertical Col.
    if styles.reverse_mq:
        children = [quarter_col, month_col]
        weights = [Length.fr(1), Length.fr(3)]
    else:
        children = [month_col, quarter_col]
        weights = [Length.fr(3), Length.fr(1)]
    return Col(children=children, weights=weights)


def _menu_strip(
    items: list[tuple[str, str, bool]],
    styles: Styles,
    manifest: Manifest,
) -> Node:
    cells: list[Node] = []
    for label, target_id, highlighted in items:
        text = Text(label, color="white" if highlighted else "black", size=parse("7pt"))
        text = maybe_link(manifest, target_id, text)
        cells.append(
            Box(
                child=text,
                stroke=Stroke(width=styles.regular_stroke),
                fill="black" if highlighted else None,
                align="center",
                rotate=styles.menu_rotate,
            )
        )
    return Col(children=cells)


def little_calendar(
    *,
    i18n: I18n,
    manifest: Manifest,
    month: Month,
    week_placement: str = "left",
    inset: Any = "3pt",
    show_month_name: bool = False,
    today: Day | None = None,
    styles: Styles,
) -> Node:
    placement = str(week_placement).lower()
    weeks = month_week_rows(month)
    headers = [i18n.t(f"weekday.letter.{d.weekday_name}") for d in weekday_row(month)]
    week_letter = i18n.t("weekday.letter.week")
    show_week = placement in {"left", "right"}
    ncols = 8 if show_week else 7
    week_stroke = Stroke(width=styles.regular_stroke, sides=("left",) if placement == "right" else ("right",))
    header_stroke = Stroke(width=styles.regular_stroke, sides=("bottom",))

    def with_week(cells: list[Node | Cell], week_cell: Node | Cell) -> list[Node | Cell]:
        out: list[Node | Cell] = list(cells)
        if placement == "left":
            out.insert(0, week_cell)
        elif placement == "right":
            out.append(week_cell)
        return out

    items: list[Node | Cell] = []
    if show_month_name:
        name = i18n.t(f"months.full.{month.name}")
        items.append(Cell(Text(name), colspan=ncols, align="center", stroke=header_stroke))

    head_cells: list[Node | Cell] = [Cell(Text(h), align="center", stroke=header_stroke) for h in headers]
    week_head = Cell(Text(week_letter), align="center", stroke=header_stroke)
    if show_week:
        # Separator lives on the week column edge facing the days.
        if placement == "left":
            week_head.stroke = Stroke(width=styles.regular_stroke, sides=("bottom", "right"))
        else:
            week_head.stroke = Stroke(width=styles.regular_stroke, sides=("bottom", "left"))
    items.extend(with_week(head_cells, week_head))

    for week in weeks:
        current = first_present(week).week()
        week_label: Node = Text(str(current.number))
        week_label = maybe_link(manifest, current.id, week_label)
        day_cells: list[Node | Cell] = []
        for day in week:
            if day is None:
                day_cells.append(Spacer())
                continue
            label: Node = Text(str(day.month_day))
            label = maybe_link(manifest, day.id, label)
            if today == day:
                label = Box(child=label, fill="black", align="center")
                if isinstance(label.child, Text):
                    label.child.color = "white"
                elif isinstance(label.child, Link) and isinstance(label.child.child, Text):
                    label.child.child.color = "white"
            day_cells.append(Cell(label, align="center"))
        week_cell = Cell(week_label, align="center", stroke=week_stroke if show_week else None)
        items.extend(with_week(day_cells, week_cell))

    n_rows = (1 if show_month_name else 0) + 1 + len(weeks)
    return Grid(
        cols=[FR1] * ncols,
        rows=[FR1] * n_rows,
        cells=items,
        align="center",
        inset=parse(inset),
    )


def schedule(
    *,
    i18n: I18n,
    styles: Styles,
    from_hour: int = 8,
    to_hour: int = 20,
    trailing_30: bool = True,
    time_format: str = "%k",
) -> Node:
    rh = styles.regular_height
    thick = Stroke(width=styles.thick_stroke, sides=("bottom",))
    black = Stroke(width=styles.regular_stroke, color="black", sides=("bottom",))
    gray = Stroke(width=styles.regular_stroke, color="gray", sides=("bottom",))
    rows: list[Length] = [rh]
    cells: list[Node | Cell] = [
        Cell(
            Box(child=Text(i18n.t("schedule"), align="left"), align="horizon", min_h=rh),
            stroke=thick,
            align="horizon",
        )
    ]
    for hour in range(int(from_hour), int(to_hour) + 1):
        pretty = f"{hour:2d}" if time_format == "%k" else f"{hour:02d}"
        rows.append(rh)
        cells.append(Cell(Text(pretty, align="left"), stroke=black, align="horizon"))
        rows.append(rh)
        cells.append(Cell(Spacer(), stroke=gray))
    if trailing_30:
        rows.append(rh)
        cells.append(Spacer())
    return Grid(cols=[FR1], rows=rows, cells=cells)


def priorities(*, i18n: I18n, styles: Styles, number: int = 5) -> Node:
    rh = styles.regular_height
    thick = Stroke(width=styles.thick_stroke, sides=("bottom",))
    regular = Stroke(width=styles.regular_stroke, sides=("bottom",))
    rows = [rh]
    cells: list[Node | Cell] = [
        Cell(Text(i18n.t("priorities"), align="left"), stroke=thick, align="horizon")
    ]
    box = Length.mm(2.2)
    for _ in range(int(number)):
        rows.append(rh)
        check = Box(
            min_w=box,
            min_h=box,
            stroke=Stroke(width=styles.regular_stroke),
        )
        cells.append(
            Cell(
                Box(child=check, align="left", padding=Length.mm(0.4), min_h=rh),
                stroke=regular,
                align="horizon",
            )
        )
    return Grid(cols=[FR1], rows=rows, cells=cells)


def notes_block(
    *,
    i18n: I18n,
    styles: Styles,
    manifest: Manifest,
    more_target: str | None = None,
    title: str | None = None,
    title_height: Length | None = None,
    notes_height: Length | None = None,
) -> Node:
    th = title_height or styles.regular_height
    nh = notes_height or FR1
    label = title if title is not None else i18n.t("daily_notes")
    title_node: Node = Text(label, align="left")
    if more_target and manifest.source(more_target):
        more = maybe_link(manifest, more_target, Text(f'| {i18n.t("more_daily_notes")}'))
        title_node = Row(children=[title_node, more], gap=parse("4pt"), weights=[AUTO, AUTO])
    return Grid(
        cols=[FR1],
        rows=[th, nh],
        cells=[
            Cell(title_node, stroke=Stroke(width=styles.thick_stroke, sides=("bottom",)), align="horizon"),
            DottedPad(),
        ],
    )


def daily_heading(
    *,
    day: Day,
    i18n: I18n,
    manifest: Manifest,
    styles: Styles,
    note_id: str | None = None,
) -> Node:
    num: Node = Text(str(day.month_day), size=styles.h1)
    if note_id:
        num = maybe_link(manifest, day.id, num)
        num = Anchor(note_id, num)
    else:
        num = Anchor(day.id, num)
    weekday = Text(i18n.t(f"weekday.full.{day.weekday_name}"), bold=True)
    week: Node = Text(f'{i18n.t("week_name")} {day.week().number}')
    week = maybe_link(manifest, day.week().id, week)
    return Row(
        children=[
            Box(
                child=num,
                stroke=Stroke(width=styles.regular_stroke, sides=("right",)),
                align="center",
                padding=parse("2pt"),
            ),
            Col(children=[weekday, week], weights=[Length.fr(3), Length.fr(2)]),
        ],
        gap=styles.regular_column_gutter,
        weights=[AUTO, AUTO],
    )


def with_week_column(cells: list[Any], value: Any, placement: str) -> list[Any]:
    out = list(cells)
    if placement == "left":
        out.insert(0, value)
    elif placement == "right":
        out.append(value)
    return out


def days_inclusive(start: Day, end: Day) -> list[Day]:
    out: list[Day] = []
    current = start
    while current <= end:
        out.append(current)
        current = current.succ()
    return out


def month_week_rows(month: Month) -> list[list[Day | None]]:
    first = month.day.beginning_of_week()
    last = month.day.end_of_week()
    ranges = [days_inclusive(first, last)]
    while ranges[-1][-1].month() == month:
        prev_end = ranges[-1][-1]
        ranges.append(days_inclusive(prev_end + 1, prev_end + 7))
    weeks = [[day if day.month() == month else None for day in week] for week in ranges]
    return [week for week in weeks if not all(d is None for d in week)]


def first_present(week: list[Day | None]) -> Day:
    for day in week:
        if day is not None:
            return day
    raise RuntimeError("week has no in-month days")


def weekday_row(month: Month) -> list[Day]:
    start = month.day.beginning_of_week()
    return [start + i for i in range(7)]
