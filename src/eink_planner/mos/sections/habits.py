"""Habits index (raw Typst) and per-month tracker grids (MOS chrome)."""

from __future__ import annotations

from datetime import date
from typing import Any

from eink_planner.calendar import walk
from eink_planner.calendar.day import Day
from eink_planner.calendar.month import Month
from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.manifest import Manifest
from eink_planner.mos.page_data import PageData
from eink_planner.mos.sections.annual import Annual

_INDEX_LEFT_INSET = "4mm"
_INDEX_BOTTOM_INSET = "4mm"
_INDEX_ROW_GUTTER = "3mm"
_HEADER_ROW = "16mm"
_HABIT_HEADER = """grid.cell(
  inset: 0pt,
  stroke: regular_stroke,
  box(
    width: 100%,
    height: 100%,
    place(line(start: (0%, 100%), end: (100%, 0%), stroke: regular_stroke))
  )
)"""
_BOX = "grid.cell(stroke: regular_stroke, [])"
_BOX_FRIDAY = "grid.cell(stroke: (rest: regular_stroke, bottom: thick_stroke), [])"
_FRIDAY_STROKE = "(rest: regular_stroke, bottom: thick_stroke)"


class Habits:
    ID = "habits"
    DEFAULT_COLUMNS = 6

    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        habit_columns: int = DEFAULT_COLUMNS,
        names: list[str] | None = None,
        **_rest: Any,
    ) -> None:
        self.section_name = section_name
        self.i18n = i18n
        self.configurator = configurator
        self.habit_columns = int(habit_columns)
        self.names = list(names) if names else []

    def register(self, manifest: Manifest) -> None:
        manifest.register_source(self.ID)
        for month in self._range():
            manifest.register_source(self.month_id(month))

    @staticmethod
    def month_id(month: Month) -> str:
        return f"habits-{month.name}"

    def pages(self, manifest: Manifest) -> list[PageData]:
        months = list(self._range())
        out = [PageData(raw_typst=True, content=self._index(manifest, months))]
        for month in months:
            page_id = self.month_id(month)
            out.append(
                PageData(
                    title=self._month_title(manifest, month),
                    content=self._month_grid(manifest, month),
                    page_id=page_id,
                    highlight_months=[month],
                    highlight_quarters=[month.quarter()],
                    month_link_id=self.month_id,
                    show_quarters=False,
                    nav_links=[],
                )
            )
        return out

    def _range(self):
        return walk(self.configurator.start_date().month(), self.configurator.end_date().month())

    def _year(self) -> int:
        return self.configurator.start_date().year

    def _year_cell(self, manifest: Manifest) -> str:
        return manifest.link_or_content(Annual.ID, str(self._year()))

    def _index(self, manifest: Manifest, months: list[Month]) -> str:
        n = len(months)
        today = date.today()
        if n:
            rows = []
            for month in months:
                hid = self.month_id(month)
                name = self.i18n.t(f"months.short.{month.name}").upper()
                label = manifest.link_or_content(hid, name)
                if is_current_index_month(month, today):
                    rows.append(
                        f"  grid.cell(fill: black, text(white)[#{label}]), "
                        "grid.cell(fill: black, [])"
                    )
                else:
                    rows.append(f"  {label}, []")
            body = f"""grid(
  columns: (auto, 1fr),
  rows: ({", ".join(["1fr"] * n)}),
  align: horizon,
  stroke: (bottom: regular_stroke),
  inset: (x: 4pt, y: 2pt),
{",\n".join(rows)}
)"""
        else:
            body = "[]"
        habits_cell = f"[{self.i18n.t('habits')} <{self.ID}>]"
        breadcrumb = f"""grid(
  columns: (auto, auto, 1fr),
  column-gutter: 6pt,
  align: horizon,
  text(size: h1, {self._year_cell(manifest)}),
  text(size: h1)[/],
  text(size: h1, {habits_cell})
)"""
        return f"""#grid(
  columns: 1fr,
  rows: (auto, 1fr),
  row-gutter: {_INDEX_ROW_GUTTER},
  inset: (left: {_INDEX_LEFT_INSET}, bottom: {_INDEX_BOTTOM_INSET}),
  {breadcrumb},
  {body}
)"""

    def _month_title(self, manifest: Manifest, month: Month) -> str:
        year = str(month.day.year)
        year_cell = manifest.link_or_content(Annual.ID, year)
        habits_cell = manifest.link_or_content(self.ID, self.i18n.t("habits"))
        full = self.i18n.t(f"months.full.{month.name}")
        page_id = self.month_id(month)
        return f"""grid(
  columns: (auto, auto, auto, auto, auto),
  column-gutter: 6pt,
  align: horizon,
  text(size: h1, {year_cell}),
  text(size: h1)[/],
  text(size: h1, {habits_cell}),
  text(size: h1)[/],
  text(size: h1)[{full}<{page_id}>]
)"""

    def _month_grid(self, manifest: Manifest, month: Month) -> str:
        days = list(walk(month.day, month.day.end_of_month()))
        n_habits = self.habit_columns
        n_days = len(days)
        cols = ", ".join(["auto"] + ["1fr"] * n_habits)
        rows = ", ".join([_HEADER_ROW] + ["1fr"] * n_days)
        padded = (list(self.names) + [""] * n_habits)[:n_habits]
        headers = ["[]"] + [_habit_header(name) for name in padded]
        cells = [", ".join(headers)]
        for day in days:
            label = self._date_label(manifest, day)
            if day.weekday_name == "friday":
                row = [f"grid.cell(stroke: {_FRIDAY_STROKE}, {label})"]
                row.extend([_BOX_FRIDAY] * n_habits)
            else:
                row = [label]
                row.extend([_BOX] * n_habits)
            cells.append(", ".join(row))
        return f"""grid(
  columns: ({cols}),
  rows: ({rows}),
  align: horizon,
  inset: 0pt,
  column-gutter: 0pt,
  row-gutter: 0pt,
  {",\n  ".join(cells)}
)"""

    def _date_label(self, manifest: Manifest, day: Day) -> str:
        short = self.i18n.t(f"weekday.short.{day.weekday_name}")
        linked = manifest.link_or_content(day.id, f"{short} {day.month_day}")
        return f"align(horizon + right, [#{linked}])"


def is_current_index_month(month: Month, today: date | None = None) -> bool:
    """True when *today* falls in this planner month (year + month)."""
    current = date.today() if today is None else today
    stamp = month.day.day
    return current.year == stamp.year and current.month == stamp.month


def _escape_typst(text: str) -> str:
    """Escape Typst specials so a habit name cannot break the document."""
    return (
        text.replace("\\", "\\\\")
        .replace("#", "\\#")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def _habit_header(name: str) -> str:
    if not name:
        return _HABIT_HEADER
    label = _escape_typst(name)
    return (
        "grid.cell(\n"
        "  inset: 0pt,\n"
        "  stroke: regular_stroke,\n"
        "  box(\n"
        "    width: 100%,\n"
        "    height: 100%,\n"
        "    clip: true,\n"
        "    align(center + horizon, text["
        + label
        + "])\n"
        "  )\n"
        ")"
    )
