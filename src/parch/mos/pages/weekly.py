"""Weekly overview page."""

from parch.calendar.day import Day
from parch.calendar.week import Week
from parch.i18n import I18n
from parch.mos.manifest import Manifest


class Weekly:
    def __init__(
        self,
        i18n: I18n,
        manifest: Manifest,
        week: Week,
        column_gutter: str,
        pattern: str = "dotted",
    ) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.week = week
        self.column_gutter = column_gutter
        self.pattern = pattern

    def title(self) -> str:
        return f"text(size: h1)[{self.i18n.t('week_name')} {self.week.number} <{self.week.id}>]"

    def content(self) -> str:
        days = self.week.days()
        cells = ",\n  ".join(self._format_day(day) for day in days)
        notes = f"[{self.i18n.t('notes')}]"
        return f"""week_matrix(
  column-gutter: {self.column_gutter},
  header-stroke: regular_stroke + black,
  pattern: {self.pattern},
  {cells},
  {notes},
)"""

    def _format_day(self, day: Day) -> str:
        weekday = self.i18n.t(f"weekday.full.{day.weekday_name}")
        return self.manifest.link_or_content(day.id, f"{weekday} {day.month_day}")
