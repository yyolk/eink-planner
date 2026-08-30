"""One page per week spanning the configured month range."""

from __future__ import annotations

from parch.calendar import walk
from parch.calendar.week import Week
from parch.compose.ctx import ComposeCtx
from parch.mos.manifest import Manifest
from parch.mos.page_data import PageData
from parch.mos.pages.weekly import Weekly as WeeklyPage
from parch.sections.annual import Annual


class Weekly:
    def __init__(
        self,
        section_name: str,
        ctx: ComposeCtx,
        column_gutter: str,
        pattern: str = "dotted",
    ) -> None:
        self.section_name = section_name
        self.i18n = ctx.i18n
        self.configurator = ctx.configurator
        self.weekday_start = configurator.weekday_start()
        self.first_week_day = configurator.start_date().beginning_of_month().beginning_of_week()
        self.last_week_day = configurator.end_date().end_of_month().end_of_week()
        self.column_gutter = column_gutter
        self.pattern = pattern

    def register(self, manifest: Manifest) -> None:
        for week in self._weeks():
            manifest.register_source(week.id)

    def pages(self, manifest: Manifest) -> list[PageData]:
        out = []
        for week in self._weeks():
            weekly = WeeklyPage(
                i18n=self.i18n,
                manifest=manifest,
                week=week,
                column_gutter=self.column_gutter,
                pattern=self.pattern,
            )
            thursday = next(day for day in week.days() if day.weekday_name == "thursday")
            out.append(
                PageData(
                    title=self._title(manifest, weekly),
                    content=weekly.content(),
                    highlight_months=[thursday.month()],
                    highlight_quarters=[],
                    nav_links=[],
                )
            )
        return out

    def _year(self) -> int:
        return self.configurator.start_date().year

    def _year_cell(self, manifest: Manifest) -> str:
        return manifest.link_or_content(Annual.ID, str(self._year()))

    def _title(self, manifest: Manifest, page: WeeklyPage) -> str:
        return f"""grid(
  columns: (auto, auto, auto),
  column-gutter: 6pt,
  align: horizon,
  text(size: h1, {self._year_cell(manifest)}),
  text(size: h1)[/],
  {page.title()}
)"""

    def _weeks(self) -> list[Week]:
        days = list(walk(self.first_week_day, self.last_week_day))
        weeks = []
        for i in range(0, len(days), 7):
            chunk = days[i : i + 7]
            if not chunk:
                continue
            weeks.append(Week(weekday_start=self.weekday_start, day=chunk[0]))
        return weeks
