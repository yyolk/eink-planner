"""Monthly calendar + notes page."""

from typing import Any

from parch import ConfigError
from parch.calendar.day import Day
from parch.calendar.month import Month
from parch.i18n import I18n
from parch.mos.manifest import Manifest
from parch.typst_emit import typst_emit

WEEK_PLACEMENTS = ("left", "right", "none")


class Monthly:
    def __init__(
        self,
        i18n: I18n,
        manifest: Manifest,
        month: Month,
        month_params: dict[str, Any],
        pattern: str = "dotted",
        side: str = "left",
    ) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.month = month
        self.month_params = month_params
        self.pattern = pattern
        self.side = side
        self.week_placement = str(month_params.get("week_placement", "left")).lower()
        if self.week_placement not in WEEK_PLACEMENTS:
            raise ConfigError(f"week_placement: allowed: {list(WEEK_PLACEMENTS)}")

    def title(self) -> str:
        return typst_emit(
            t'text(size: h1)[{self.i18n.t(f"months.full.{self.month.name}")}<{self.month.id}>]'
        )

    def content(self) -> str:
        calendar = self._calendar()
        return f"""layout(size => block(
  width: size.width,
  height: size.height,
  grid(
    columns: 1fr,
    rows: (1fr, auto, 1fr),
    {calendar},
    grid.hline(stroke: regular_stroke + black),
    rect_pattern({self.pattern})
  )
))"""

    def _calendar(self) -> str:
        if self.week_placement == "none":
            return f"""block(
    width: 100%,
    height: 1fr,
    grid(
    stroke: regular_stroke,
    columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    rows: {self._rows()},

    {self._heading()},
    {self._day_cells()}
  ))"""
        return f"""month_weeks({self.side},
    rows: {self._rows()},
    {self._heading()},
    {self._day_cells()}
  )"""

    def _rows(self) -> str:
        n = len(self._month_in_weeks())
        return f"(regular_height,) + (1fr,) * {n}"

    def _heading(self) -> str:
        weeks = self._month_in_weeks()
        sample = weeks[1] if len(weeks) > 1 else weeks[0]
        heading = [
            f'align(center + horizon)[{self.i18n.t(f"weekday.full.{day.weekday_name}")}]'
            for day in sample
        ]
        if self.week_placement == "none":
            return ", ".join(heading)
        return ", ".join(["[]", *heading])

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
