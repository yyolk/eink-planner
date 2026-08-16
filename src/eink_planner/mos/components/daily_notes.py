"""Daily notes block on the day page."""

from __future__ import annotations

from typing import Any

from eink_planner.calendar.dated_note import DatedNote
from eink_planner.calendar.day import Day
from eink_planner.i18n import I18n
from eink_planner.mos.manifest import Manifest


class DailyNotes:
    def __init__(
        self,
        i18n: I18n,
        manifest: Manifest,
        day: Day,
        title_height: str,
        notes_height: str,
        **_rest: Any,
    ) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.day = day
        self.title_height = title_height
        self.notes_height = notes_height

    def generate(self) -> str:
        daily_note_id = DatedNote(weekday_start=self.day.weekday_start, day=self.day).id
        more = ""
        if self.manifest.source(daily_note_id):
            more = f' #padded_link(<{daily_note_id}>)[| {self.i18n.t("more_daily_notes")}]'
        return f"""grid(
  columns: 1fr,
  rows: ({self.title_height}, {self.notes_height}),
  grid.cell(align:horizon, stroke: (bottom: thick_stroke), [{self.i18n.t("daily_notes")}{more}]),
  scratch_pad
)"""
