"""Extra dotted note pages that follow each day."""

from parch.calendar import walk
from parch.calendar.dated_note import DatedNote
from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.compose.page_data import HeadingMark, PageData


class DailyNotes:
    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        pages: int,
        pattern: str = "dotted",
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
        for note in self._range():
            out.append(
                PageData(
                    title=self._title(manifest, note),
                    content=f"lined_well({self.pattern})",
                    highlight_months=[note.day.month()],
                    highlight_quarters=[],
                    nav_links=[],
                    heading_mark=HeadingMark.TRAIL,
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
  {week}
)"""

    def _range(self) -> list[DatedNote]:
        notes: list[DatedNote] = []
        for day in walk(self.configurator.start_date(), self.configurator.end_date()):
            for page_num in range(1, self.pages_num + 1):
                notes.append(
                    DatedNote(day=day, weekday_start=day.weekday_start, page=page_num)
                )
        return notes
