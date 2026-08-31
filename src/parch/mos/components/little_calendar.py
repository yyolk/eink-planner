"""Mini month calendar used on annual / quarterly / daily pages."""

from typing import Any

from parch.calendar.day import Day
from parch.calendar.month import Month
from parch.i18n import I18n
from parch.mos.manifest import Manifest

WEEK_ROWS = 6


class LittleCalendar:
    def __init__(
        self,
        i18n: I18n,
        manifest: Manifest,
        month: Month,
        inset: str,
        day: Day | None = None,
        show_month_name: bool = False,
        show_week_letter: bool = True,
        side: str = "left",
        week_placement: str = "left",
        **_rest: Any,
    ) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.month = month
        self.today = day
        self.show_month_name = bool(show_month_name)
        self.show_week_letter = bool(show_week_letter)
        self.inset = inset
        self.side = side
        self.week_placement = str(week_placement).lower()

    def generate(self) -> str:
        if self.week_placement == "none":
            return self._generate_none()
        return f"""month_grid({self.side},
  {self._name_cell()}
  {self._heading()},
  {self._day_cells()},
  inset: {self.inset}
)"""

    def _generate_none(self) -> str:
        return f"""grid(
  align: center + horizon,
  inset: {self.inset},
  stroke: none,
  columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
  rows: (auto, auto) + (1fr,) * {WEEK_ROWS},
  grid.hline(y: 1, stroke: regular_stroke + black),
  grid.hline(y: 2, stroke: regular_stroke + black),
  {self._name_cell()}
  {self._heading()},
  {self._day_cells()}
)"""

    def _name_cell(self) -> str:
        colspan = 7 if self.week_placement == "none" else 8
        if self.show_month_name:
            name = self.i18n.t(f"months.full.{self.month.name}")
            return f"""grid.cell(
    colspan: {colspan},
    [{name}]
  ),
"""
        # Occupy the name track so weekdays stay on the second auto row.
        return f"""grid.cell(
    colspan: {colspan},
    inset: 0pt,
    []
  ),
"""

    def _heading(self) -> str:
        sample = self._expand_week_ranges()[0]
        heading = [f"[{self.i18n.t(f'weekday.letter.{day.weekday_name}')}]" for day in sample]
        if self.week_placement == "none":
            return ", ".join(heading)
        week_label = f"[{self.i18n.t('weekday.letter.week')}]" if self.show_week_letter else "[]"
        return ", ".join([week_label, *heading])

    def _day_cells(self) -> str:
        rows = []
        for week in self._month_in_weeks():
            row = [self._day_cell(day) for day in week]
            if self.week_placement == "none":
                rows.append(", ".join(row))
            else:
                rows.append(", ".join([self._week_label_cell(week), *row]))
        return ",\n".join(rows)

    def _day_cell(self, day: Day | None) -> str:
        if day is None:
            return "[]"
        text = self.manifest.link_or_content(day.id, str(day.month_day))
        if self.today == day:
            text = f"grid.cell(fill: black, text(white, {text}))"
        return text

    def _week_label_cell(self, week: list[Day | None]) -> str:
        present = self._first_present_day(week)
        if present is None:
            return "[]"
        current_week = present.week()
        return self.manifest.link_or_content(current_week.id, str(current_week.number))

    def _first_present_day(self, week: list[Day | None]) -> Day | None:
        for day in week:
            if day is not None:
                return day
        return None

    def _month_in_weeks(self) -> list[list[Day | None]]:
        ranges = self._expand_week_ranges()
        weeks = self._mask_outside_days(ranges)
        weeks = [week for week in weeks if not all(d is None for d in week)]
        empty = [None] * 7
        while len(weeks) < WEEK_ROWS:
            weeks.append(list(empty))
        if len(weeks) > WEEK_ROWS:
            raise RuntimeError(
                f"month {self.month.id} has {len(weeks)} weeks; month_grid week-rows is {WEEK_ROWS}"
            )
        return weeks

    def _expand_week_ranges(self) -> list[list[Day]]:
        first = self.month.day.beginning_of_week()
        last = self.month.day.end_of_week()
        ranges = [_days_inclusive(first, last)]
        while ranges[-1][-1].month() == self.month:
            prev_end = ranges[-1][-1]
            ranges.append(_days_inclusive(prev_end + 1, prev_end + 7))
        return ranges

    def _mask_outside_days(self, ranges: list[list[Day]]) -> list[list[Day | None]]:
        masked: list[list[Day | None]] = []
        for week in ranges:
            masked.append([day if day.month() == self.month else None for day in week])
        return masked


def _days_inclusive(start: Day, end: Day) -> list[Day]:
    out = []
    current = start
    while current <= end:
        out.append(current)
        current = current.succ()
    return out
