"""Habits index (raw Typst) and per-month tracker grids (MOS chrome)."""

from __future__ import annotations

from parch.calendar import walk
from parch.calendar.day import Day
from parch.calendar.month import Month
from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.mos.contents_mark import body_size_token, heading_height_token, trail_strip
from parch.compose.page_data import HeadingMark, PageData

_INDEX_LEFT_INSET = "4mm"
_INDEX_BOTTOM_INSET = "4mm"
_INDEX_ROW_GUTTER = "3mm"
_HEADER_ROW = "regular_height"
_BOX = "grid.cell(stroke: regular_stroke, [])"


class Habits:
    ID = "habits"
    DEFAULT_COLUMNS = 4

    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        habit_columns: int = DEFAULT_COLUMNS,
        names: list[str] | None = None,
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
                    heading_mark=HeadingMark.TRAIL,
                )
            )
        return out

    def _range(self):
        return walk(self.configurator.start_date().month(), self.configurator.end_date().month())

    def _heading(self, manifest: Manifest, habits_cell: str) -> str:
        title = f"text(size: h1, {habits_cell})"
        mark = trail_strip(
            manifest,
            heading_height_token(self.configurator),
            body_size_token(self.configurator),
            chip=None,
        )
        if not mark:
            return title
        return f"""stack(
  dir: ltr,
  spacing: 1fr,
  {mark},
  {title}
)"""

    def _index(self, manifest: Manifest, months: list[Month]) -> str:
        n = len(months)
        if n:
            rows = []
            for month in months:
                hid = self.month_id(month)
                name = self.i18n.t(f"months.full.{month.name}")
                band = (
                    "box(width: 100%, height: 100%, "
                    f"align(horizon + left, [{name}]))"
                )
                if manifest.source(hid):
                    # Link wraps the full-size box so the PDF annotation
                    # is the 1fr cell, not the padded month word.
                    band = f"padded_link(<{hid}>, {band})"
                rows.append(
                    "  grid.cell(\n"
                    "    align: horizon + left,\n"
                    f"    {band}\n"
                    "  )"
                )
            body = f"""box(
  width: 100%,
  height: 100%,
  grid(
    columns: 1fr,
    rows: ({", ".join(["1fr"] * n)}),
    align: horizon + left,
    inset: (x: 4pt, y: 0pt),
{",\n".join(rows)}
  )
)"""
        else:
            body = "[]"
        habits_cell = f"[{self.i18n.t('habits')} <{self.ID}>]"
        return f"""#grid(
  columns: 1fr,
  rows: (auto, 1fr),
  row-gutter: {_INDEX_ROW_GUTTER},
  inset: (left: {_INDEX_LEFT_INSET}, bottom: {_INDEX_BOTTOM_INSET}),
  {self._heading(manifest, habits_cell)},
  {body}
)"""

    def _mos_right(self) -> bool:
        return (
            self.configurator.dig_bang("planner", "params", "mos_layout")["side_menu_position"]
            == "right"
        )

    def _month_label(self, month: Month) -> str:
        full = self.i18n.t(f"months.full.{month.name}")
        return f"text(size: h1)[{full}<{self.month_id(month)}>]"

    def _seated_month_label(self, month: Month) -> str:
        full = self.i18n.t(f"months.full.{month.name}")
        return (
            "text(size: h1, box(inset: (top: 0.25em), "
            f'text(top-edge: "cap-height")[{full}<{self.month_id(month)}>]))'
        )

    def _month_title(self, manifest: Manifest, month: Month) -> str:
        habits_cell = manifest.link_or_content(self.ID, self.i18n.t("habits"))
        habits = f"text(size: h1, {habits_cell})"
        if not self._mos_right():
            return habits
        return f"""stack(
  dir: ttb,
  {habits},
  {self._month_label(month)}
)"""

    def _month_grid(self, manifest: Manifest, month: Month) -> str:
        days = list(walk(month.day, month.day.end_of_month()))
        n_habits = self.habit_columns
        cols = ", ".join(["auto"] + ["1fr"] * n_habits)
        row_sizes = [_HEADER_ROW]
        padded = (list(self.names) + [""] * n_habits)[:n_habits]
        headers = ["[]"] + [_habit_header(name) for name in padded]
        cells = [", ".join(headers)]
        for day in days:
            row = [self._date_label(manifest, day)]
            row.extend([_BOX] * n_habits)
            cells.append(", ".join(row))
            row_sizes.append("1fr")
        rows = ", ".join(row_sizes)
        grid = f"""grid(
  columns: ({cols}),
  rows: ({rows}),
  align: horizon,
  inset: 0pt,
  column-gutter: 0pt,
  row-gutter: 0pt,
  {",\n  ".join(cells)}
)"""
        if self._mos_right():
            return grid
        return f"""grid(
  columns: 1fr,
  rows: (auto, 1fr),
  align: horizon + left,
  {self._seated_month_label(month)},
  {grid}
)"""

    def _date_label(self, manifest: Manifest, day: Day) -> str:
        short = self.i18n.t(f"weekday.short.{day.weekday_name}")
        linked = manifest.link_or_content(day.id, f"{short} {day.month_day}")
        return f"align(horizon + right, [#{linked}])"


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
        return _BOX
    label = _escape_typst(name)
    return (
        "grid.cell(\n"
        "  inset: 0pt,\n"
        "  stroke: regular_stroke,\n"
        "  align(center + horizon, text["
        + label
        + "])\n"
        ")"
    )
