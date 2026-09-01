"""Daily notes block on the day page."""

from typing import Any

from parch.calendar.dated_note import DatedNote
from parch.calendar.day import Day
from parch.i18n import I18n
from parch.mos.manifest import Manifest
from parch.mos.preamble import _WELL_PATTERN


class DailyNotes:
    def __init__(
        self,
        i18n: I18n,
        manifest: Manifest,
        day: Day,
        title_height: str,
        notes_height: str,
        pattern: str = "dotted",
        **_rest: Any,
    ) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.day = day
        self.title_height = title_height
        self.notes_height = notes_height
        self.pattern = pattern

    def generate(self) -> str:
        daily_note_id = DatedNote(weekday_start=self.day.weekday_start, day=self.day).id
        notes = self.i18n.t("daily_notes")
        rule = "stroke: (bottom: regular_stroke + black)"
        if self.manifest.source(daily_note_id):
            more = self.manifest.link_or_content(daily_note_id, self.i18n.t("more_daily_notes"))
            return f"""grid(
  columns: (1fr, auto),
  rows: ({self.title_height}, {self.notes_height}),
  grid.cell(align: horizon, {rule}, [{notes}]),
  grid.cell(align: horizon + right, {rule}, {more}),
  grid.cell(colspan: 2, lined_well({_WELL_PATTERN.get(self.pattern, self.pattern)}))
)"""
        return f"""grid(
  columns: 1fr,
  rows: ({self.title_height}, {self.notes_height}),
  grid.cell(align: horizon, {rule}, [{notes}]),
  lined_well({_WELL_PATTERN.get(self.pattern, self.pattern)})
)"""
