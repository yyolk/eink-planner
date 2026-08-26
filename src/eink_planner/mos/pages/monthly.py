"""Monthly calendar + notes page."""

from __future__ import annotations

from typing import Any

from eink_planner import ConfigError
from eink_planner.calendar.day import Day
from eink_planner.calendar.month import Month
from eink_planner.i18n import I18n
from eink_planner.mos.manifest import Manifest

WEEK_PLACEMENTS = ("left", "right", "none")


class Monthly:
    def __init__(
        self,
        i18n: I18n,
        manifest: Manifest,
        month: Month,
        month_params: dict[str, Any],
        pattern: str = "dotted",
    ) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.month = month
        self.month_params = month_params
        self.pattern = pattern
        self.week_placement = str(month_params.get("week_placement", "left")).lower()
        if self.week_placement not in WEEK_PLACEMENTS:
            raise ConfigError(f"week_placement: allowed: {list(WEEK_PLACEMENTS)}")

    def title(self) -> str:
        return f'text(size: h1)[{self.i18n.t(f"months.full.{self.month.name}")}<{self.month.id}>]'

    def content(self) -> str:
        return f"""grid(
  columns: 1fr,
  rows: (auto, 1fr),

  grid(
    stroke: regular_stroke,
    columns: ({self._columns()}),
    rows: ({self._rows()}),

    {self._heading()},
    {self._day_cells()}
  ),
  grid.hline(stroke: regular_stroke + black),
  rect_pattern({self.pattern})
)"""

    def _columns(self) -> str:
        cols = ["1fr"] * 7
        return ", ".join(self._with_week_column(cols, "regular_height"))

    def _rows(self) -> str:
        head = ["regular_height"]
        body = [str(self.month_params["daily_cell_height"])] * len(self._month_in_weeks())
        return ", ".join(head + body)

    def _heading(self) -> str:
        weeks = self._month_in_weeks()
        sample = weeks[1] if len(weeks) > 1 else weeks[0]
        heading = [
            f'align(center + horizon)[{self.i18n.t(f"weekday.full.{day.weekday_name}")}]'
            for day in sample
        ]
        return ", ".join(self._with_week_column(heading, "[]"))

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
        return f"grid.cell(align: top + left, inset: 3pt, [#{text}])"

    def _week_label_cell(self, week: list[Day | None]) -> str:
        current_week = self._first_present_day(week).week()
        label = self.manifest.link_or_content(current_week.id, str(current_week.number))
        rotation = self.month_params.get("week_label_rotation", "90deg")
        return f"align(center + horizon, rotate({rotation}, reflow: true)[#{label}])"

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
        weeks = [[day if day.month() == self.month else None for day in week] for week in ranges]
        return [week for week in weeks if not all(d is None for d in week)]

    def _expand_week_ranges(self) -> list[list[Day]]:
        first = self.month.day.beginning_of_week()
        last = self.month.day.end_of_week()
        ranges = [_days_inclusive(first, last)]
        while ranges[-1][-1].month() == self.month:
            prev_end = ranges[-1][-1]
            ranges.append(_days_inclusive(prev_end + 1, prev_end + 7))
        return ranges


def _days_inclusive(start: Day, end: Day) -> list[Day]:
    out = []
    current = start
    while current <= end:
        out.append(current)
        current = current.succ()
    return out
