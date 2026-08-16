"""Rotated months strip in the side menu."""

from __future__ import annotations

from collections.abc import Sequence

from eink_planner.calendar.month import Month
from eink_planner.i18n import I18n
from eink_planner.mos.manifest import Manifest


class MonthsMenu:
    def __init__(self, i18n: I18n, manifest: Manifest, range: Sequence[Month]) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.range = list(range)
        self.highlighted: list[Month] = []

    def highlight(self, items: list[Month] | None = None) -> list[Month]:
        self.highlighted = list(items or [])
        return self.highlighted

    def generate(self) -> str:
        cols = ", ".join(["1fr"] * len(self.range))
        return f"""table(
  stroke: regular_stroke,
  columns: ({cols}),
  rows: 1fr,
  align: horizon + center,

  {self._months()}
)"""

    def _months(self) -> str:
        return ",\n".join(self._format(month) for month in self.range)

    def _format(self, month: Month) -> str:
        text = self.i18n.t(f"months.short.{month.name}")
        if self.manifest.source(month.id):
            text = f"#padded_link(<{month.id}>)[{text}]"
        if month in self.highlighted:
            return f"table.cell(fill: black, text(white)[{text}])"
        return f"table.cell([{text}])"
