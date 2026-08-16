"""Rotated quarters strip in the side menu."""

from __future__ import annotations

from collections.abc import Sequence

from eink_planner.calendar.quarter import Quarter
from eink_planner.i18n import I18n
from eink_planner.mos.manifest import Manifest


class QuartersMenu:
    def __init__(self, i18n: I18n, manifest: Manifest, range: Sequence[Quarter]) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.range = list(range)
        self.highlighted: list[Quarter] = []

    def highlight(self, items: list[Quarter] | None = None) -> list[Quarter]:
        self.highlighted = list(items or [])
        return self.highlighted

    def generate(self) -> str:
        cols = ", ".join(["1fr"] * len(self.range))
        return f"""table(
  stroke: regular_stroke,
  columns: ({cols}),
  rows: 1fr,
  align: horizon + center,

  {self._quarters()}
)"""

    def _quarters(self) -> str:
        return ",\n".join(self._format(quarter) for quarter in self.range)

    def _format(self, quarter: Quarter) -> str:
        text = f"{self.i18n.t('quarters.short')}{quarter.number}"
        if self.manifest.source(quarter.id):
            text = f"#padded_link(<{quarter.id}>)[{text}]"
        if quarter in self.highlighted:
            return f"table.cell(fill: black, text(white)[{text}])"
        return f"table.cell([{text}])"
