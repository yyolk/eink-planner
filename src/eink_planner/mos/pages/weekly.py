"""Weekly overview page."""

from __future__ import annotations

from eink_planner.calendar.day import Day
from eink_planner.calendar.week import Week
from eink_planner.i18n import I18n
from eink_planner.mos.manifest import Manifest


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
        return f'text(size: h1)[{self.i18n.t("week_name_full")} {self.week.number} <{self.week.id}>]'

    def content(self) -> str:
        days = self.week.days()
        return f"""grid(
  columns: (1fr, 1fr, 1fr),
  rows: (4mm, 1fr, 4mm, 1fr, 4mm, 1fr),
  column-gutter: {self.column_gutter},

  {self._format_days(days[0:3])},
  grid.cell(colspan: 3, rect_pattern({self.pattern})),
  {self._format_days(days[3:6])},
  grid.cell(colspan: 3, rect_pattern({self.pattern})),
  {self._format_day(days[6])}, grid.cell(colspan: 2, stroke: (bottom: thick_stroke), [{self.i18n.t("notes")}]),
  grid.cell(colspan: 3, rect_pattern({self.pattern}))
)"""

    def _format_days(self, days: list[Day]) -> str:
        return ", ".join(self._format_day(day) for day in days)

    def _format_day(self, day: Day) -> str:
        # Ruby Date#strftime("%A, %e") — full weekday + space-padded day
        label = self.manifest.link_or_content(day.id, day.strftime("%A, %e"))
        return f"grid.cell(stroke: (bottom: thick_stroke), {label})"
