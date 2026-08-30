"""Year-at-a-glance page of 12 little calendars."""

from __future__ import annotations

import math
from typing import Any

from parch.calendar import walk
from parch.config import StrictDict, _to_plain
from parch.i18n import I18n
from parch.mos.components.little_calendar import LittleCalendar
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.compose.page_data import PageData


class Annual:
    ID = "annual"

    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        row_gutter: str = "5pt",
        **other: Any,
    ) -> None:
        self.section_name = section_name
        self.i18n = i18n
        self.configurator = configurator
        base = self.configurator.dig("planner", "params", "little_calendar") or {}
        extra = other.get("little_calendar") or {}
        self.little_calendar = {**_plain(base), **_plain(extra)}
        self.row_gutter = row_gutter

    def register(self, manifest: Manifest) -> None:
        manifest.register_source(self.ID)

    def pages(self, manifest: Manifest) -> list[PageData]:
        year = self.configurator.start_date().year
        return [
            PageData(
                title=f"text(size: h1)[{year}<{self.ID}>]",
                content=self._content(manifest),
                page_id=self.ID,
                nav_links=[],
            )
        ]

    def _content(self, manifest: Manifest) -> str:
        months = list(self._range())
        parts: list[str] = []
        for i, month in enumerate(months):
            parts.append(
                LittleCalendar(
                    i18n=self.i18n,
                    manifest=manifest,
                    month=month,
                    **self.little_calendar,
                    show_week_letter=False,
                ).generate()
            )
            nxt = months[i + 1] if i + 1 < len(months) else None
            if nxt is not None and nxt.quarter() != month.quarter():
                parts.append("grid.hline(stroke: regular_stroke + black)")
        rows = ", ".join(["1fr"] * math.ceil(len(months) / 3))
        return f"""grid(
  columns: (1fr, 1fr, 1fr),
  rows: ({rows}),
  column-gutter: regular_column_gutter,
  row-gutter: {self.row_gutter},

  {",\n".join(parts)}
)"""

    def _range(self):
        return walk(self.configurator.start_date().month(), self.configurator.end_date().month())


def _plain(value: Any) -> dict:
    if isinstance(value, StrictDict):
        return value.to_plain()
    if isinstance(value, dict):
        return _to_plain(value)
    return {}
