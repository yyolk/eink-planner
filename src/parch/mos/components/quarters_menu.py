"""Rotated quarters strip in the side menu."""

from __future__ import annotations

from collections.abc import Sequence

from parch.calendar.quarter import Quarter
from parch.i18n import I18n
from parch.mos.manifest import Manifest


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
        label = self.manifest.link_or_content(
            quarter.id, f"{self.i18n.t('quarter.short')}{quarter.number}"
        )
        if quarter in self.highlighted:
            return f"table.cell(fill: black, text(white)[#{label}])"
        return f"table.cell([#{label}])"
