"""One page per week spanning the configured month range."""

from parch.calendar import walk
from parch.calendar.day import Day
from parch.calendar.week import Week
from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.compose.page_data import PageData
from parch.mos.pages.weekly import Weekly as WeeklyPage

_EN_DASH = "–"


class Weekly:
    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        column_gutter: str,
        pattern: str = "dotted",
    ) -> None:
        self.section_name = section_name
        self.i18n = i18n
        self.configurator = configurator
        self.weekday_start = self.configurator.weekday_start()
        self.first_week_day = self.configurator.start_date().beginning_of_month().beginning_of_week()
        self.last_week_day = self.configurator.end_date().end_of_month().end_of_week()
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
                    title=self._title(weekly),
                    content=weekly.content(),
                    highlight_months=[thursday.month()],
                    highlight_quarters=[],
                    nav_links=[],
                )
            )
        return out

    def range_label(self, first: Day, last: Day) -> str:
        first_month = self.i18n.t(f"months.short.{first.month().name}")
        last_month = self.i18n.t(f"months.short.{last.month().name}")
        if first.day.month == last.day.month and first.day.year == last.day.year:
            return f"{first_month} {first.month_day} {_EN_DASH} {last.month_day}"
        return f"{first_month} {first.month_day} {_EN_DASH} {last_month} {last.month_day}"

    def _title(self, page: WeeklyPage) -> str:
        days = page.week.days()
        rng = self.range_label(days[0], days[-1])
        return (
            f"text(size: h1)[{self.i18n.t('week_name')} {page.week.number}"
            f" <{page.week.id}> #h(0.6em) {rng}]"
        )

    def _weeks(self) -> list[Week]:
        days = list(walk(self.first_week_day, self.last_week_day))
        weeks = []
        for i in range(0, len(days), 7):
            chunk = days[i : i + 7]
            if not chunk:
                continue
            weeks.append(Week(weekday_start=self.weekday_start, day=chunk[0]))
        return weeks
