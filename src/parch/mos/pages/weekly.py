"""Weekly overview page."""

from __future__ import annotations

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
        return f"""grid(
  columns: (1fr, 1fr, 1fr),
  rows: (1fr, 1fr, 1fr),
  column-gutter: {self.column_gutter},

  {self._format_days(days[0:3])},
  {self._format_days(days[3:6])},
  {self._format_day(days[6])}, {self._format_notes()}
)"""

    def _format_days(self, days: list[Day]) -> str:
        return ", ".join(self._format_day(day) for day in days)

    def _format_day(self, day: Day) -> str:
        weekday = self.i18n.t(f"weekday.full.{day.weekday_name}")
        label = self.manifest.link_or_content(day.id, f"{weekday} {day.month_day}")
        return self._cell(label)

    def _format_notes(self) -> str:
        header = f"[{self.i18n.t('notes')}]"
        return f"grid.cell(colspan: 2, {self._cell(header)})"

    def _cell(self, header: str) -> str:
        """Seat the day-label rule under the font descender."""
        return f"""grid(
  columns: 1fr,
  rows: (auto, 1fr),
  grid.cell(stroke: (bottom: regular_stroke + black), inset: (bottom: 0.25em), text(bottom-edge: "descender", {header})),
  rect_pattern({self.pattern})
)"""

