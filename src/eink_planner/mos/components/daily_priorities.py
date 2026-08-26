"""Priorities checkbox list on the day page."""

from __future__ import annotations

from typing import Any

from eink_planner.i18n import I18n


class DailyPriorities:
    def __init__(self, i18n: I18n, number: int, **_rest: Any) -> None:
        self.i18n = i18n
        self.number = int(number)

    def generate(self) -> str:
        return f"""grid(
  columns: 1fr,
  inset: 0mm,
  stroke: (_, _) => (bottom: regular_stroke + black),

  grid.cell(stroke: (bottom: regular_stroke + black), box(height: regular_height, align(horizon, [{self.i18n.t("priorities")}]))),
  {self._lines()}
)"""

    def _lines(self) -> str:
        cell = "box(height: regular_height, align(horizon, [$square.stroked$]))"
        return ",\n".join([cell] * self.number)
