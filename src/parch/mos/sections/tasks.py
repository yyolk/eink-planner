"""Weekly Tasks: index of weeks and one ticked leftover page per week.

Raw Typst only — no MOS chrome. Sibling of Review.
"""

from __future__ import annotations

from typing import Any

from parch.calendar import walk
from parch.calendar.day import Day
from parch.calendar.week import Week
from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.mos.contents_mark import body_size_token, heading_height_token, lead_title
from parch.mos.page_data import PageData
from parch.mos.sections.annual import Annual

_INDEX_LEFT_INSET = "4mm"
_INDEX_BOTTOM_INSET = "4mm"
_INDEX_ROW_GUTTER = "3mm"
_DAY_STRIP_HEIGHT = "8mm"
_EN_DASH = "–"
_WEEK_NUM_COL = "2em"
_MIN_PACK_ROWS = 12
_MAX_PACK_ROWS = 14


class Tasks:
    ID = "tasks"
    DEFAULT_WEEKS_PER_PAGE = 13

    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        weeks_per_page: int = DEFAULT_WEEKS_PER_PAGE,
        **_rest: Any,
    ) -> None:
        self.section_name = section_name
        self.i18n = i18n
        self.configurator = configurator
        self.weeks_per_page = int(weeks_per_page)
        self.weekday_start = configurator.weekday_start()
        self.first_week_day = configurator.start_date().beginning_of_month().beginning_of_week()
        self.last_week_day = configurator.end_date().end_of_month().end_of_week()

    def register(self, manifest: Manifest) -> None:
        weeks = self._weeks()
        for index in range(self._index_count(len(weeks))):
            manifest.register_source(self.index_id(index))
        for week in weeks:
            manifest.register_source(self.week_page_id(week))

    @staticmethod
    def index_id(page_index: int) -> str:
        return Tasks.ID if page_index == 0 else f"{Tasks.ID}-{page_index + 1}"

    @staticmethod
    def week_page_id(week: Week) -> str:
        return f"{Tasks.ID}-{week.id}"

    def pages(self, manifest: Manifest) -> list[PageData]:
        weeks = self._weeks()
        chunks = self._chunks(weeks)
        out: list[PageData] = []
        for index, chunk in enumerate(chunks):
            out.append(PageData(raw_typst=True, content=self._index(manifest, chunk, index)))
        for index, chunk in enumerate(chunks):
            parent = self.index_id(index)
            for week in chunk:
                out.append(
                    PageData(
                        raw_typst=True,
                        content=self._week_page(manifest, week, parent),
                    )
                )
        return out

    def _weeks(self) -> list[Week]:
        days = list(walk(self.first_week_day, self.last_week_day))
        weeks = []
        for i in range(0, len(days), 7):
            chunk = days[i : i + 7]
            if not chunk:
                continue
            weeks.append(Week(weekday_start=self.weekday_start, day=chunk[0]))
        return weeks

    def _page_sizes(self, n_weeks: int) -> list[int]:
        n = self.weeks_per_page
        if n < 1:
            raise ValueError("weeks_per_page must be at least 1")
        if n_weeks <= 0:
            return [0]
        sizes = [n] * (n_weeks // n)
        rem = n_weeks % n
        if rem:
            sizes.append(rem)
        if (
            len(sizes) >= 2
            and sizes[-1] < _MIN_PACK_ROWS
            and sizes[-2] + sizes[-1] <= _MAX_PACK_ROWS
        ):
            sizes[-2] += sizes[-1]
            sizes.pop()
        return sizes

    def _chunks(self, weeks: list[Week]) -> list[list[Week]]:
        sizes = self._page_sizes(len(weeks))
        out: list[list[Week]] = []
        i = 0
        for size in sizes:
            out.append(weeks[i : i + size])
            i += size
        return out

    def _index_count(self, n_weeks: int) -> int:
        return len(self._page_sizes(n_weeks))

    def _year(self) -> int:
        return self.configurator.start_date().year

    def _year_cell(self, manifest: Manifest) -> str:
        return manifest.link_or_content(Annual.ID, str(self._year()))

    def range_label(self, first: Day, last: Day) -> str:
        first_month = self.i18n.t(f"months.short.{first.month().name}")
        last_month = self.i18n.t(f"months.short.{last.month().name}")
        if first.day.month == last.day.month and first.day.year == last.day.year:
            return f"{first_month} {first.month_day} {_EN_DASH} {last.month_day}"
        return f"{first_month} {first.month_day} {_EN_DASH} {last_month} {last.month_day}"

    def _index_row(self, manifest: Manifest, week: Week) -> str:
        hid = self.week_page_id(week)
        days = week.days()
        rng = self.range_label(days[0], days[-1])
        inner = (
            "grid(\n"
            f"      columns: ({_WEEK_NUM_COL}, 1fr),\n"
            "      rows: 1fr,\n"
            "      align: horizon + left,\n"
            "      inset: 0pt,\n"
            f"      [{week.number}],\n"
            f"      [{rng}]\n"
            "    )"
        )
        band = f"box(width: 100%, height: 100%, {inner})"
        if manifest.source(hid):
            band = f"padded_link(<{hid}>, {band})"
        return (
            "  grid.cell(\n"
            "    align: horizon + left,\n"
            f"    {band}\n"
            "  )"
        )

    def _index_body(self, manifest: Manifest, weeks: list[Week]) -> str:
        n = len(weeks)
        if not n:
            return "[]"
        rows = [self._index_row(manifest, week) for week in weeks]
        inner = f"""box(
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
        if n >= _MIN_PACK_ROWS or n >= self.weeks_per_page:
            return inner
        empty = self.DEFAULT_WEEKS_PER_PAGE - n
        return f"""grid(
  columns: 1fr,
  rows: ({n}fr, {empty}fr),
  inset: 0pt,
  {inner},
  []
)"""

    def _crumb(self, manifest: Manifest, tasks_cell: str) -> str:
        breadcrumb = f"""grid(
  columns: (auto, auto, 1fr),
  column-gutter: 6pt,
  align: horizon,
  text(size: h1, {self._year_cell(manifest)}),
  text(size: h1)[/],
  text(size: h1, {tasks_cell})
)"""
        return lead_title(
            manifest,
            heading_height_token(self.configurator),
            breadcrumb,
            body_size_token(self.configurator),
        )

    def _index(self, manifest: Manifest, weeks: list[Week], page_index: int) -> str:
        page_id = self.index_id(page_index)
        body = self._index_body(manifest, weeks)
        tasks_cell = f"[{self.i18n.t('tasks')} <{page_id}>]"
        return f"""#grid(
  columns: 1fr,
  rows: (auto, 1fr),
  row-gutter: {_INDEX_ROW_GUTTER},
  inset: (left: {_INDEX_LEFT_INSET}, bottom: {_INDEX_BOTTOM_INSET}),
  {self._crumb(manifest, tasks_cell)},
  {body}
)"""

    def _week_page(self, manifest: Manifest, week: Week, index_page_id: str) -> str:
        days = week.days()
        rng = self.range_label(days[0], days[-1])
        page_id = self.week_page_id(week)
        tasks_cell = manifest.link_or_content(index_page_id, self.i18n.t("tasks"))
        week_label = f"{self.i18n.t('week_name')} {week.number}"
        week_cell = manifest.link_or_content(week.id, week_label)
        quiet = f"text(size: 0.85em)[#{week_cell} #h(0.6em) {rng}]"
        cells = ", ".join(self._day_cell(manifest, day) for day in days)
        day_strip = f"""grid(
  columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
  rows: {_DAY_STRIP_HEIGHT},
  align: horizon + center,
  inset: (x: 2pt, y: 0pt),
  {cells}
)"""
        return f"""#[] <{page_id}>
#grid(
  columns: 1fr,
  rows: (auto, auto, auto, 1fr),
  row-gutter: {_INDEX_ROW_GUTTER},
  inset: (left: {_INDEX_LEFT_INSET}, bottom: {_INDEX_BOTTOM_INSET}),
  {self._crumb(manifest, tasks_cell)},
  {quiet},
  {day_strip},
  {_TASK_FIELD}
)"""

    def _day_cell(self, manifest: Manifest, day: Day) -> str:
        full = self.i18n.t(f"weekday.full.{day.weekday_name}")
        label = f"{full} {day.month_day}"
        band = (
            "box(width: 100%, height: 100%, align(horizon + center, "
            f"stack(dir: ttb, spacing: 0pt, [{label}], "
            "line(length: 100%, stroke: regular_stroke + black))))"
        )
        if manifest.source(day.id):
            band = f"padded_link(<{day.id}>, {band})"
        return f"grid.cell(align: horizon + center, {band})"


_TASK_FIELD = """layout(size => {
  let n = calc.max(0, calc.floor(size.height / regular_height))
  if n == 0 { [] } else {
    grid(
      columns: 1fr,
      rows: n * (regular_height,),
      stroke: (_, _) => (bottom: regular_stroke + black),
      inset: 0pt,
      ..n * (box(height: regular_height, align(horizon, [$square.stroked$])),),
    )
  }
})"""
