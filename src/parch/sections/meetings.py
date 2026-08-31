"""Meetings index and per-meeting notes pages (raw Typst, no MOS chrome)."""

import math

from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.mos.contents_mark import body_size_token, heading_height_token, trail_heading
from parch.compose.page_data import HeadingMark, PageData
from parch.sections._shared import _length_mm

# Match the Projects index so row capacity tracks the same geometry.
_INDEX_LEFT_INSET = "4mm"
_INDEX_BOTTOM_INSET = "4mm"
_INDEX_ROW_GUTTER = "3mm"
_ROW_HEIGHT_MULT = 2
_NUM_COL = "2em"
# Quiet date write-in on the name line — short ruled cell, no DATE label.
_DATE_COL = "16mm"
_TOPIC_LINES = 4
_ACTION_LINES = 5


class Meetings:
    ID = "meetings"
    DEFAULT_INDEX_PAGES = 1
    TOPIC_LINES = _TOPIC_LINES
    ACTION_LINES = _ACTION_LINES

    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        index_pages: int = DEFAULT_INDEX_PAGES,
    ) -> None:
        self.section_name = section_name
        self.i18n = i18n
        self.configurator = configurator
        self.index_pages_num = int(index_pages)
        self.pages_num = self.rows_per_index_page() * self.index_pages_num

    def register(self, manifest: Manifest) -> None:
        for page in range(1, self.index_page_count() + 1):
            manifest.register_source(self.index_page_id(page))
        for index in range(1, self.pages_num + 1):
            manifest.register_source(self.meeting_id(index))

    @staticmethod
    def meeting_id(index: int) -> str:
        return f"meeting-{index}"

    @staticmethod
    def index_page_id(page: int) -> str:
        return Meetings.ID if page <= 1 else f"{Meetings.ID}-{page}"

    def rows_per_index_page(self) -> int:
        """How many 2×-regular_height rows fit on one index page."""
        page_h = _length_mm(self.configurator.dig_bang("document", "layout", "dimensions", "height"))
        top = _length_mm(self.configurator.dig_bang("document", "layout", "margin", "top"))
        bottom = _length_mm(self.configurator.dig_bang("document", "layout", "margin", "bottom"))
        breadcrumb = _length_mm(self.configurator.dig_bang("document", "text", "h1"))
        available = (
            page_h
            - top
            - bottom
            - breadcrumb
            - _length_mm(_INDEX_BOTTOM_INSET)
            - _length_mm(_INDEX_ROW_GUTTER)
        )
        row = _ROW_HEIGHT_MULT * _length_mm(
            self.configurator.dig_bang("planner", "params", "regular_height")
        )
        if row <= 0:
            return 1
        return max(1, math.floor(available / row))

    def index_page_count(self) -> int:
        return max(1, self.index_pages_num)

    def board_index_id(self, index: int) -> str:
        page = (index - 1) // self.rows_per_index_page() + 1
        return self.index_page_id(page)

    def pages(self, manifest: Manifest) -> list[PageData]:
        rpp = self.rows_per_index_page()
        out: list[PageData] = []
        for page in range(1, self.index_page_count() + 1):
            start = (page - 1) * rpp + 1
            end = page * rpp
            out.append(PageData(raw_typst=True, content=self._index(manifest, page, start, end)))
        for index in range(1, self.pages_num + 1):
            out.append(PageData(raw_typst=True, content=self._meeting(manifest, index)))
        return out

    def _heading(self, manifest: Manifest, meetings_cell: str) -> str:
        return trail_heading(
            manifest,
            heading_height_token(self.configurator),
            f"text(size: h1, {meetings_cell})",
            body_size_token(self.configurator),
            direction="rtl",
            edge=HeadingMark.FOLLOW,
        )

    def _index_meetings_cell(self, manifest: Manifest, page: int) -> str:
        label = self.i18n.t("meetings")
        page_id = self.index_page_id(page)
        if page <= 1:
            return f"[{label} <{page_id}>]"
        return f"[#{manifest.link_or_content(self.ID, label)} <{page_id}>]"

    def _index_row(self, manifest: Manifest, index: int) -> str:
        mid = self.meeting_id(index)
        inner = (
            "grid(\n"
            f"      columns: ({_NUM_COL}, 1fr),\n"
            "      rows: 1fr,\n"
            "      align: horizon + left,\n"
            "      inset: 0pt,\n"
            f"      [{index}],\n"
            "      []\n"
            "    )"
        )
        band = f"box(width: 100%, height: 100%, {inner})"
        if manifest.source(mid):
            band = f"padded_link(<{mid}>, {band})"
        return (
            "  grid.cell(\n"
            "    align: horizon + left,\n"
            f"    {band}\n"
            "  )"
        )

    def _index(self, manifest: Manifest, page: int, start: int, end: int) -> str:
        n = max(0, end - start + 1)
        if n:
            rows = [self._index_row(manifest, index) for index in range(start, end + 1)]
            # Every index is full (rpp * index_pages), so 1fr bands eat leftover height.
            body = f"""grid(
  columns: 1fr,
  rows: ({", ".join(["1fr"] * n)}),
  align: horizon + left,
  stroke: (bottom: regular_stroke + black),
  inset: (x: 4pt, y: 2pt),
{",\n".join(rows)}
)"""
        else:
            body = "[]"
        return f"""#grid(
  columns: 1fr,
  rows: (auto, 1fr),
  row-gutter: {_INDEX_ROW_GUTTER},
  inset: (left: {_INDEX_LEFT_INSET}, bottom: {_INDEX_BOTTOM_INSET}),
  {self._heading(manifest, self._index_meetings_cell(manifest, page))},
  {body}
)"""

    def _ticked_lines(self, n: int) -> str:
        cells = ",\n    ".join(
            ["box(height: regular_height, align(horizon, [$square.stroked$]))"] * n
        )
        rows = ", ".join(["regular_height"] * n)
        return f"""grid(
  columns: 1fr,
  rows: ({rows}),
  stroke: (_, _) => (bottom: regular_stroke + black),
  inset: 0pt,
    {cells}
)"""

    def _label(self, key: str) -> str:
        return f"[{self.i18n.t(key)}]"

    def _meeting(self, manifest: Manifest, index: int) -> str:
        meetings = self.i18n.t("meetings")
        mid = self.meeting_id(index)
        meetings_cell = manifest.link_or_content(self.board_index_id(index), meetings)
        name_line = f"""grid(
  columns: (1fr, {_DATE_COL}),
  column-gutter: 6pt,
  align: horizon,
  grid.cell(stroke: (bottom: regular_stroke + black), []),
  grid.cell(stroke: (bottom: regular_stroke + black), []),
)"""
        topics = f"""grid(
  columns: 1fr,
  rows: (auto, auto),
  row-gutter: 1.5mm,
  {self._label("topics")},
  {self._ticked_lines(_TOPIC_LINES)}
)"""
        actions = f"""grid(
  columns: 1fr,
  rows: (auto, auto),
  row-gutter: 1.5mm,
  {self._label("action_items")},
  {self._ticked_lines(_ACTION_LINES)}
)"""
        quiet = f"text(size: 0.85em)[{index}]"
        return f"""#[] <{mid}>
#grid(
  columns: 1fr,
  rows: (auto, auto, auto, auto, auto, 1fr, auto),
  row-gutter: 2.5mm,
  inset: (left: {_INDEX_LEFT_INSET}, bottom: {_INDEX_BOTTOM_INSET}),
  {self._heading(manifest, meetings_cell)},
  {quiet},
  {name_line},
  {topics},
  {self._label("notes")},
  rect_pattern(dotted),
  {actions}
)"""
