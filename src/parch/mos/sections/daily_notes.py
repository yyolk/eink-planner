"""Extra dotted note pages that follow each day."""

from __future__ import annotations

from typing import Any

from parch.calendar import walk
from parch.calendar.dated_note import DatedNote
from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.mos.page_data import PageData
from parch.mos.sections.annual import Annual


class DailyNotes:
    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        pages: int,
        pattern: str = "dotted",
        **_rest: Any,
    ) -> None:
        self.section_name = section_name
        self.i18n = i18n
        self.configurator = configurator
        self.pages_num = int(pages)
        self.pattern = pattern

    def register(self, manifest: Manifest) -> None:
        for note in self._range():
            manifest.register_source(note.id)

    def pages(self, manifest: Manifest) -> list[PageData]:
        out = []
        year = str(self.configurator.start_date().year)
        for note in self._range():
            out.append(
                PageData(
                    title=self._title(manifest, note),
                    content=f"rect_pattern({self.pattern})",
                    highlight_months=[note.day.month()],
                    highlight_quarters=[],
                    nav_links=[(Annual.ID, year)],
                )
            )
        return out

    def _title(self, manifest: Manifest, daily_note: DatedNote) -> str:
        week = manifest.link_or_content(
            daily_note.day.week().id,
            f'{self.i18n.t("week_name")} {daily_note.day.week().number}',
        )
        day = f"text(size: h1)[{daily_note.day.month_day} <{daily_note.id}>]"
        if manifest.source(daily_note.day.id):
            day = f"padded_link(<{daily_note.day.id}>)[#{day}]"
        weekday = self.i18n.t(f"weekday.full.{daily_note.day.weekday_name}")
        week_row = week
        fraction = self._fraction(manifest, daily_note)
        if fraction is not None:
            week_row = f"""grid(
  columns: (auto, auto),
  column-gutter: regular_column_gutter,
  align: horizon,
  {week},
  text(size: 0.85em, {fraction})
)"""
        return f"""grid(
  columns: (auto, auto),
  rows: (3fr, 2fr),
  column-gutter: regular_column_gutter,

  grid.cell(
    rowspan: 2,
    align: center + horizon,
    rect(
      stroke: (right: regular_stroke),

      {day}
    )
  ),
  [*{weekday}*],
  {week_row}
)"""

    def _fraction(self, manifest: Manifest, daily_note: DatedNote) -> str | None:
        if self.pages_num <= 1:
            return None
        sibling_page = daily_note.page % self.pages_num + 1
        sibling = DatedNote(
            day=daily_note.day,
            weekday_start=daily_note.weekday_start,
            page=sibling_page,
        )
        return manifest.link_or_content(
            sibling.id, f"{daily_note.page}/{self.pages_num}"
        )

    def _range(self) -> list[DatedNote]:
        notes: list[DatedNote] = []
        for day in walk(self.configurator.start_date(), self.configurator.end_date()):
            for page_num in range(1, self.pages_num + 1):
                notes.append(
                    DatedNote(day=day, weekday_start=day.weekday_start, page=page_num)
                )
        return notes
