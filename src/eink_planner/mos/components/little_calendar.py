"""Mini month calendar used on annual / quarterly / daily pages."""

from __future__ import annotations

from typing import Any

from eink_planner.calendar.day import Day
from eink_planner.calendar.month import Month
from eink_planner.calendar.week import Week
from eink_planner.i18n import I18n
from eink_planner.mos.manifest import Manifest


class LittleCalendar:
    def __init__(
        self,
        i18n: I18n,
        manifest: Manifest,
        week_placement: str,
        month: Month,
        inset: str,
        day: Day | None = None,
        show_month_name: bool = False,
        **_rest: Any,
    ) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.week_placement = str(week_placement).lower()
        self.month = month
        self.today = day
        self.show_month_name = bool(show_month_name)
        self.inset = inset

    def generate(self) -> str:
        return f"""grid(
  align: center + horizon,
  inset: {self.inset},
  stroke: {self._stroke()},
  columns: ({self._columns()}),
  rows: 1fr,

  {self._optional_month_name()}
  {self._heading()}, grid.hline(stroke: regular_stroke),
  {self._day_cells()}
)"""

    def _stroke(self) -> str:
        if self.week_placement not in {"left", "right"}:
            return "none"
        x = "7" if self.week_placement == "right" else "1"
        return f"(x, _) => if x == {x} {{( left: regular_stroke )}}"

    def _columns(self) -> str:
        cols = ["1fr"] * 7
        return ", ".join(self._with_week_column(cols, "1fr"))

    def _optional_month_name(self) -> str:
        if not self.show_month_name:
            return ""
        colspan = len(self._with_week_column([""] * 7, ""))
        name = self.i18n.t(f"months.full.{self.month.name}")
        return f"""grid.cell(
    colspan: {colspan},
    [{name}]
  ),
  grid.hline(stroke: regular_stroke),
"""

    def _heading(self) -> str:
        weeks = self._month_in_weeks()
        sample = weeks[1] if len(weeks) > 1 else weeks[0]
        heading = [f"[{self.i18n.t(f'weekday.one_letter.{day.weekday_name}')}]" for day in sample]
        week_label = f"[{self.i18n.t('weekday.one_letter.week')}]"
        return ", ".join(self._with_week_column(heading, week_label))

    def _day_cells(self) -> str:
        rows = []
        for week in self._month_in_weeks():
            row = [self._day_cell(day) for day in week]
            rows.append(", ".join(self._with_week_column(row, self._week_label_cell(week))))
        return ",\n".join(rows)

    def _day_cell(self, day: Day | None) -> str:
        if day is None:
            return "[]"
        text = self.manifest.link_or_content(day.id, str(day.month_day))
        if self.today == day:
            text = f"grid.cell(fill: black, text(white, {text}))"
        return text

    def _week_label_cell(self, week: list[Day | None]) -> str:
        current_week = self._first_present_day(week).week()
        return self.manifest.link_or_content(current_week.id, str(current_week.number))

    def _first_present_day(self, week: list[Day | None]) -> Day:
        for day in week:
            if day is not None:
                return day
        raise RuntimeError("week has no in-month days")

    def _with_week_column(self, cells: list[Any], value: Any) -> list[Any]:
        out = list(cells)
        if self.week_placement == "left":
            out.insert(0, value)
        elif self.week_placement == "right":
            out.append(value)
        return out

    def _month_in_weeks(self) -> list[list[Day | None]]:
        ranges = self._expand_week_ranges()
        weeks = self._mask_outside_days(ranges)
        return [week for week in weeks if not all(d is None for d in week)]

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
