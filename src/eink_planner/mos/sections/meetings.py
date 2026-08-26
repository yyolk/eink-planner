"""Meetings index and per-meeting notes pages (raw Typst, no MOS chrome)."""

from __future__ import annotations

import math
import re
from typing import Any

from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.manifest import Manifest
from eink_planner.mos.page_data import PageData
from eink_planner.mos.sections.annual import Annual

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
_LENGTH = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))(mm|cm|pt)$")
# Review week field only — do not touch global `#let lined` (luma grey).
_REVIEW_LINED = """tiling(
  size: (regular_height, regular_height),
  place(
    line(
      start: (0%, regular_height - 0.15mm),
      end: (100%, regular_height - 0.15mm),
      stroke: regular_stroke + black
    ),
  )
)"""


def _length_mm(token: str) -> float:
    """Parse a Typst length token (`mm` / `cm` / `pt`) into millimetres."""
    text = str(token).strip()
    match = _LENGTH.fullmatch(text)
    if match is None:
        raise ValueError(f"unrecognized length token: {token!r}")
    value = float(match.group(1))
    unit = match.group(2)
    if unit == "mm":
        return value
    if unit == "cm":
        return value * 10.0
    return value * 25.4 / 72.0


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
        **_rest: Any,
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

    def _year(self) -> int:
        return self.configurator.start_date().year

    def _year_cell(self, manifest: Manifest) -> str:
        return manifest.link_or_content(Annual.ID, str(self._year()))

    def _breadcrumb(self, manifest: Manifest, meetings_cell: str) -> str:
        return f"""grid(
  columns: (auto, auto, 1fr),
  column-gutter: 6pt,
  align: horizon,
  text(size: h1, {self._year_cell(manifest)}),
  text(size: h1)[/],
  text(size: h1, {meetings_cell})
)"""

    def _index_meetings_cell(self, manifest: Manifest, page: int) -> str:
        label = self.i18n.t("meetings")
        page_id = self.index_page_id(page)
        if page <= 1:
            return f"[{label} <{page_id}>]"
        return f"[#{manifest.link_or_content(self.ID, label)} <{page_id}>]"

    def _index_row(self, manifest: Manifest, index: int) -> str:
        mid = self.meeting_id(index)
        number = f"[{index}]"
        hit = f"box(width: 100%, height: 100%, align(horizon + left, {number}))"
        if manifest.source(mid):
            # Number cell only — write-in paper stays unlinkable.
            hit = f"padded_link(<{mid}>, {hit})"
        return (
            "  grid.cell(\n"
            "    align: horizon + left,\n"
            f"    {hit}\n"
            "  ),\n"
            "  []"
        )

    def _index(self, manifest: Manifest, page: int, start: int, end: int) -> str:
        n = max(0, end - start + 1)
        if n:
            rows = [self._index_row(manifest, index) for index in range(start, end + 1)]
            # Every index is full (rpp * index_pages), so 1fr bands eat leftover height.
            body = f"""grid(
  columns: ({_NUM_COL}, 1fr),
  rows: ({", ".join(["1fr"] * n)}),
  align: horizon,
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
  {self._breadcrumb(manifest, self._index_meetings_cell(manifest, page))},
  {body}
)"""

    def _ticked_lines(self, n: int) -> str:
        cells = ",\n    ".join(["[], []"] * n)
        rows = ", ".join(["regular_height"] * n)
        return f"""grid(
  columns: (regular_height, 1fr),
  rows: ({rows}),
  stroke: regular_stroke + black,
  inset: 0pt,
    {cells}
)"""

    def _heading(self, key: str) -> str:
        return f"[{self.i18n.t(key)}]"

    def _meeting(self, manifest: Manifest, index: int) -> str:
        meetings = self.i18n.t("meetings")
        mid = self.meeting_id(index)
        n = self.pages_num
        name_line = f"""grid(
  columns: (1fr, {_DATE_COL}, auto),
  column-gutter: 6pt,
  align: horizon,
  grid.cell(stroke: (bottom: regular_stroke + black), []),
  grid.cell(stroke: (bottom: regular_stroke + black), []),
  text(size: 0.85em)[{index}/{n} <{mid}>]
)"""
        topics = f"""grid(
  columns: 1fr,
  rows: (auto, auto),
  row-gutter: 1.5mm,
  {self._heading("topics")},
  {self._ticked_lines(_TOPIC_LINES)}
)"""
        actions = f"""grid(
  columns: 1fr,
  rows: (auto, auto),
  row-gutter: 1.5mm,
  {self._heading("action_items")},
  {self._ticked_lines(_ACTION_LINES)}
)"""
        prefix = f"#let review_lined = {_REVIEW_LINED}\n"
        return f"""{prefix}#grid(
  columns: 1fr,
  rows: (auto, auto, auto, auto, 1fr, auto),
  row-gutter: 2.5mm,
  inset: (left: {_INDEX_LEFT_INSET}, bottom: {_INDEX_BOTTOM_INSET}),
  {self._breadcrumb(manifest, manifest.link_or_content(self.board_index_id(index), meetings))},
  {name_line},
  {topics},
  {self._heading("notes")},
  rect_pattern(review_lined),
  {actions}
)"""
