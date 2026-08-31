"""Single daily page layout."""

from typing import Any

from parch import ConfigError
from parch.calendar.day import Day
from parch.config import StrictDict, _to_plain
from parch.i18n import I18n
from parch.mos.components.daily_notes import DailyNotes
from parch.mos.components.daily_schedule import DailySchedule
from parch.mos.components.daily_priorities import DailyPriorities
from parch.mos.components.little_calendar import LittleCalendar
from parch.mos.manifest import Manifest


COMPONENT_CLASSES = {
    "schedule": DailySchedule,
    "priorities": DailyPriorities,
    "notes": DailyNotes,
    "little_calendar": LittleCalendar,
}


class Daily:
    def __init__(
        self,
        i18n: I18n,
        manifest: Manifest,
        day: Day,
        items_spacing: str,
        side: str = "left",
        debug: bool = False,
        **params: Any,
    ) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.day = day
        self.items_spacing = items_spacing
        self.side = side
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
        hours = self._column(self.params.get("left_column") or [])
        writing = self._column(self.params.get("right_column") or [])
        return f"daily_well({self.side}, {hours}, {writing})"

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
            extra = {}
            if klass is LittleCalendar:
                extra["show_week_letter"] = False
                extra["side"] = self.side
            pieces.append(
                klass(
                    i18n=self.i18n,
                    manifest=self.manifest,
                    month=self.day.month(),
                    day=self.day,
                    **params,
                    **extra,
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
