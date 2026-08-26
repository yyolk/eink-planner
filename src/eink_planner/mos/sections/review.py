"""Weekly Review: index of weeks and one lined leftover-notes page per week.

Raw Typst only — no MOS chrome. Sibling of Habits, not a second weekly planner.
"""

from __future__ import annotations

from typing import Any

from eink_planner.calendar import walk
from eink_planner.calendar.day import Day
from eink_planner.calendar.week import Week
from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.manifest import Manifest
from eink_planner.mos.page_data import PageData
from eink_planner.mos.sections.annual import Annual

_INDEX_LEFT_INSET = "4mm"
_INDEX_BOTTOM_INSET = "4mm"
_INDEX_ROW_GUTTER = "3mm"
_DAY_STRIP_HEIGHT = "8mm"
_EN_DASH = "–"


class Review:
    ID = "review"
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
        return Review.ID if page_index == 0 else f"{Review.ID}-{page_index + 1}"

    @staticmethod
    def week_page_id(week: Week) -> str:
        return f"{Review.ID}-{week.id}"

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

    def _chunks(self, weeks: list[Week]) -> list[list[Week]]:
        n = self.weeks_per_page
        if n < 1:
            raise ValueError("weeks_per_page must be at least 1")
        if not weeks:
            return [[]]
        return [weeks[i : i + n] for i in range(0, len(weeks), n)]

    def _index_count(self, n_weeks: int) -> int:
        if n_weeks <= 0:
            return 1
        n = self.weeks_per_page
        if n < 1:
            raise ValueError("weeks_per_page must be at least 1")
        return (n_weeks + n - 1) // n

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

    def _index(self, manifest: Manifest, weeks: list[Week], page_index: int) -> str:
        page_id = self.index_id(page_index)
        n = len(weeks)
        if n:
            rows = []
            for week in weeks:
                hid = self.week_page_id(week)
                days = week.days()
                rng = self.range_label(days[0], days[-1])
                label = f"{week.number} #text(size: 0.85em)[{rng}]"
                band = f"box(width: 100%, height: 100%, align(horizon + left, [{label}]))"
                if manifest.source(hid):
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
    stroke: (bottom: regular_stroke),
    inset: (x: 4pt, y: 0pt),
{",\n".join(rows)}
  )
)"""
        else:
            body = "[]"
        if weeks:
            span = self.range_label(weeks[0].days()[0], weeks[-1].days()[-1])
            quiet = f"text(size: 0.85em)[{span}]"
        else:
            quiet = "[]"
        review_cell = f"[{self.i18n.t('review')} <{page_id}>]"
        breadcrumb = f"""grid(
  columns: (auto, auto, 1fr),
  column-gutter: 6pt,
  align: horizon,
  text(size: h1, {self._year_cell(manifest)}),
  text(size: h1)[/],
  text(size: h1, {review_cell})
)"""
        return f"""#grid(
  columns: 1fr,
  rows: (auto, auto, 1fr),
  row-gutter: {_INDEX_ROW_GUTTER},
  inset: (left: {_INDEX_LEFT_INSET}, bottom: {_INDEX_BOTTOM_INSET}),
  {breadcrumb},
  {quiet},
  {body}
)"""

    def _week_page(self, manifest: Manifest, week: Week, index_page_id: str) -> str:
        days = week.days()
        rng = self.range_label(days[0], days[-1])
        page_id = self.week_page_id(week)
        year_cell = self._year_cell(manifest)
        review_cell = manifest.link_or_content(index_page_id, self.i18n.t("review"))
        breadcrumb = f"""grid(
  columns: (auto, auto, 1fr),
  column-gutter: 6pt,
  align: horizon,
  text(size: h1, {year_cell}),
  text(size: h1)[/],
  text(size: h1, {review_cell})
)"""
        week_line = f"[{week.number} <{page_id}> #h(0.6em) #text(size: 0.85em)[{rng}]]"
        cells = ", ".join(self._day_cell(manifest, day) for day in days)
        day_strip = f"""stack(
  dir: ttb,
  spacing: 0pt,
  grid(
    columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    rows: {_DAY_STRIP_HEIGHT},
    align: horizon + center,
    inset: (x: 2pt, y: 0pt),
    {cells}
  ),
  line(length: 100%, stroke: regular_stroke)
)"""
        return f"""#grid(
  columns: 1fr,
  rows: (auto, auto, auto, 1fr),
  row-gutter: {_INDEX_ROW_GUTTER},
  inset: (left: {_INDEX_LEFT_INSET}, bottom: {_INDEX_BOTTOM_INSET}),
  {breadcrumb},
  {week_line},
  {day_strip},
  rect_pattern(lined)
)"""

    def _day_cell(self, manifest: Manifest, day: Day) -> str:
        short = self.i18n.t(f"weekday.short.{day.weekday_name}")
        label = f"{short} {day.month_day}"
        band = f"box(width: 100%, height: 100%, align(horizon + center, [{label}]))"
        if manifest.source(day.id):
            band = f"padded_link(<{day.id}>, {band})"
        return f"grid.cell(align: horizon + center, {band})"
