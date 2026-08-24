"""Single daily page layout."""

from __future__ import annotations

from typing import Any

from eink_planner import ConfigError
from eink_planner.calendar.day import Day
from eink_planner.config import StrictDict, _to_plain
from eink_planner.i18n import I18n
from eink_planner.mos.components.daily_notes import DailyNotes
from eink_planner.mos.components.daily_schedule import DailySchedule
from eink_planner.mos.components.daily_top_priorities import DailyTopPriorities
from eink_planner.mos.components.little_calendar import LittleCalendar
from eink_planner.mos.manifest import Manifest


COMPONENT_CLASSES = {
    "schedule": DailySchedule,
    "top_priorities": DailyTopPriorities,
    "notes": DailyNotes,
    "little_calendar": LittleCalendar,
}


class Daily:
    def __init__(
        self,
        i18n: I18n,
        manifest: Manifest,
        day: Day,
        columns_width: str,
        items_spacing: str,
        debug: bool = False,
        **params: Any,
    ) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.day = day
        self.columns_width = columns_width
        self.items_spacing = items_spacing
        self.params = params
        self.debug = debug

    def title(self) -> str:
        week = self.manifest.link_or_content(
            self.day.week().id, f'{self.i18n.t("week_name")} {self.day.week().number}'
        )
        debug_stroke = "stroke: regular_stroke,\n" if self.debug else ""
        weekday = self.i18n.t(f"weekday.full.{self.day.weekday_name}")
        return f"""grid(
  columns: (auto, auto),
  rows: (3fr, 2fr),
  column-gutter: regular_column_gutter,
  {debug_stroke}
  grid.cell(
    rowspan: 2,
    align: center + horizon,
    rect(
      stroke: (right: regular_stroke),

      text(size: h1)[{self.day.month_day} <{self.day.id}>]
    )
  ),
  [*{weekday}*],
  {week}
)"""

    def content(self) -> str:
        return f"""grid(
  columns: {self.columns_width},
  rows: 1fr,
  column-gutter: regular_column_gutter,

  {self._column(self.params.get("left_column") or [])},
  {self._column(self.params.get("right_column") or [])}
)"""

    def _column(self, comps: list[Any]) -> str:
        pieces: list[str] = []
        for comp in comps:
            data = _to_plain(comp) if isinstance(comp, (StrictDict, dict)) else dict(comp)
            if not data.get("enabled"):
                continue
            klass = COMPONENT_CLASSES.get(data.get("class"))
            if klass is None:
                raise ConfigError(f"unknown component: {data.get('class')}")
            params = data.get("params") or {}
            if isinstance(params, StrictDict):
                params = params.to_plain()
            pieces.append(
                klass(
                    i18n=self.i18n,
                    manifest=self.manifest,
                    month=self.day.month(),
                    day=self.day,
                    **params,
                ).generate()
            )
        if not pieces:
            return "[]"
        rows = ", ".join(["auto"] * (len(pieces) - 1) + ["1fr"])
        return f"""grid(
  columns: 1fr,
  rows: ({rows}),
  row-gutter: {self.items_spacing},
  {",\n".join(pieces)}
)"""
