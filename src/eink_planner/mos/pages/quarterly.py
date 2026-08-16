"""Quarter page: three little calendars + scratch pad."""

from __future__ import annotations

from typing import Any

from eink_planner.calendar.quarter import Quarter
from eink_planner.i18n import I18n
from eink_planner.mos.components.little_calendar import LittleCalendar
from eink_planner.mos.manifest import Manifest


class Quarterly:
    def __init__(
        self,
        i18n: I18n,
        manifest: Manifest,
        quarter: Quarter,
        months_column: str,
        little_calendar: dict[str, Any],
    ) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.quarter = quarter
        self.months_column = str(months_column).lstrip(":").lower()
        self.little_calendar = little_calendar

    def title(self) -> str:
        return f'text(size: h1)[{self.i18n.t("quarters.long")} {self.quarter.number} <{self.quarter.id}>]'

    def content(self) -> str:
        cols = ["2fr", "3fr"]
        columns = [self._months_stack(), "scratch_pad"]
        if self.months_column == "right":
            cols.reverse()
            columns.reverse()
        return f"""grid(
  columns: ({",".join(cols)}),
  column-gutter: regular_column_gutter,

  {", ".join(columns)}
)"""

    def _months_stack(self) -> str:
        return f"""stack(
  dir: ttb,
  spacing: 1fr,

  {", ".join(self._months())}
)"""

    def _months(self) -> list[str]:
        return [
            LittleCalendar(
                i18n=self.i18n,
                manifest=self.manifest,
                month=month,
                **self.little_calendar,
            ).generate()
            for month in self.quarter.months()
        ]
