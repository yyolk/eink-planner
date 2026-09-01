"""Quarter page: three little calendars + scratch pad."""

from typing import Any

from parch.calendar.quarter import Quarter
from parch.i18n import I18n
from parch.mos.components.little_calendar import LittleCalendar
from parch.mos.manifest import Manifest
from parch.sections._shared import _WELL_PATTERN


class Quarterly:
    def __init__(
        self,
        i18n: I18n,
        manifest: Manifest,
        quarter: Quarter,
        little_calendar: dict[str, Any],
        pattern: str = "dotted",
        side: str = "left",
    ) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.quarter = quarter
        self.little_calendar = little_calendar
        self.pattern = pattern
        self.side = side

    def title(self) -> str:
        return f'text(size: h1)[{self.i18n.t("quarter.long")} {self.quarter.number} <{self.quarter.id}>]'

    def content(self) -> str:
        months = self._months_grid()
        pad = f"lined_well({_WELL_PATTERN.get(self.pattern, self.pattern)})"
        return f"quarter_well({self.side}, {months}, {pad})"

    def _months_grid(self) -> str:
        months = self._months()
        # Bound each month to an equal 1fr row. A stack + LittleCalendar
        # rows: 1fr lets the first month consume the whole column.
        rows = ", ".join(["1fr"] * len(months))
        return f"""grid(
  columns: 1fr,
  rows: ({rows}),
  row-gutter: regular_column_gutter,

  {", ".join(months)}
)"""

    def _months(self) -> list[str]:
        params = {**self.little_calendar, "show_week_letter": False}
        return [
            LittleCalendar(
                i18n=self.i18n,
                manifest=self.manifest,
                month=month,
                **params,
                side=self.side,
            ).generate()
            for month in self.quarter.months()
        ]
