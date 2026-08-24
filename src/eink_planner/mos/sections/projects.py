"""Projects index and per-project kanban boards (raw Typst, no MOS chrome)."""

from __future__ import annotations

import math
import re
from typing import Any

from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.manifest import Manifest
from eink_planner.mos.page_data import PageData
from eink_planner.mos.sections.annual import Annual

# Match the index page chrome in `_index` so row capacity tracks the layout.
_INDEX_LEFT_INSET = "4mm"
_INDEX_BOTTOM_INSET = "4mm"
_INDEX_ROW_GUTTER = "3mm"
_ROW_HEIGHT = "2 * regular_height"
_ROW_HEIGHT_MULT = 2
_LENGTH = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))(mm|cm|pt)$")


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


class Projects:
    ID = "projects"
    DEFAULT_PAGES = 20
    CARDS = 8

    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        pages: int = DEFAULT_PAGES,
        **_rest: Any,
    ) -> None:
        self.section_name = section_name
        self.i18n = i18n
        self.configurator = configurator
        self.pages_num = int(pages)

    def register(self, manifest: Manifest) -> None:
        for page in range(1, self.index_page_count() + 1):
            manifest.register_source(self.index_page_id(page))
        for index in range(1, self.pages_num + 1):
            manifest.register_source(self.board_id(index))

    @staticmethod
    def board_id(index: int) -> str:
        return f"project-{index}"

    @staticmethod
    def index_page_id(page: int) -> str:
        return Projects.ID if page <= 1 else f"{Projects.ID}-{page}"

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
        if self.pages_num <= 0:
            return 1
        rpp = self.rows_per_index_page()
        return math.ceil(self.pages_num / rpp)

    def board_index_id(self, index: int) -> str:
        page = (index - 1) // self.rows_per_index_page() + 1
        return self.index_page_id(page)

    def pages(self, manifest: Manifest) -> list[PageData]:
        rpp = self.rows_per_index_page()
        out: list[PageData] = []
        for page in range(1, self.index_page_count() + 1):
            start = (page - 1) * rpp + 1
            end = min(page * rpp, self.pages_num)
            out.append(PageData(raw_typst=True, content=self._index(manifest, page, start, end)))
        for index in range(1, self.pages_num + 1):
            out.append(PageData(raw_typst=True, content=self._board(manifest, index)))
        return out

    def _year(self) -> int:
        return self.configurator.start_date().year

    def _year_cell(self, manifest: Manifest) -> str:
        return manifest.link_or_content(Annual.ID, str(self._year()))

    def _breadcrumb(self, manifest: Manifest, projects_cell: str) -> str:
        return f"""grid(
  columns: (auto, auto, 1fr),
  column-gutter: 6pt,
  align: horizon,
  text(size: h1, {self._year_cell(manifest)}),
  text(size: h1)[/],
  text(size: h1, {projects_cell})
)"""

    def _index_projects_cell(self, manifest: Manifest, page: int) -> str:
        label = self.i18n.t("projects")
        page_id = self.index_page_id(page)
        if page <= 1:
            return f"[{label} <{page_id}>]"
        return f"[#{manifest.link_or_content(self.ID, label)} <{page_id}>]"

    def _index(self, manifest: Manifest, page: int, start: int, end: int) -> str:
        n = max(0, end - start + 1)
        if n:
            rows = []
            for index in range(start, end + 1):
                bid = self.board_id(index)
                number = manifest.link_or_content(bid, str(index))
                arrow = manifest.link_or_content(bid, "→")
                rows.append(f"  {number}, [], {arrow}")
            body = f"""grid(
  columns: (auto, 1fr, auto),
  rows: ({", ".join([_ROW_HEIGHT] * n)}),
  align: horizon,
  stroke: (bottom: regular_stroke),
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
  {self._breadcrumb(manifest, self._index_projects_cell(manifest, page))},
  {body}
)"""

    def _board(self, manifest: Manifest, index: int) -> str:
        projects = self.i18n.t("projects")
        title = self.i18n.t("title")
        date = self.i18n.t("date")
        todo = self.i18n.t("todo")
        doing = self.i18n.t("doing")
        done = self.i18n.t("done")
        bid = self.board_id(index)
        n = self.pages_num
        header = f"""grid(
  columns: (auto, 1fr, auto, 1fr, auto),
  column-gutter: 6pt,
  align: horizon,
  [*{title}*],
  grid.cell(stroke: (bottom: regular_stroke), []),
  [*{date}*],
  grid.cell(stroke: (bottom: regular_stroke), []),
  [{index}/{n} <{bid}>]
)"""
        card = "grid.cell(stroke: regular_stroke + luma(180), inset: 0pt, rect_pattern(dotted))"
        cards = ",\n    ".join([card] * self.CARDS)
        column = f"""grid(
  columns: 1fr,
  rows: ({", ".join(["1fr"] * self.CARDS)}),
  row-gutter: 2mm,
    {cards}
)"""
        kanban = f"""grid(
  columns: (1fr, 1fr, 1fr),
  rows: (auto, 1fr),
  column-gutter: regular_column_gutter,
  row-gutter: 2mm,
  align(center)[*{todo}*],
  align(center)[*{doing}*],
  align(center)[*{done}*],
  {column},
  {column},
  {column}
)"""
        return f"""#grid(
  columns: 1fr,
  rows: (auto, auto, 1fr),
  row-gutter: 2.5mm,
  inset: (left: 4mm, bottom: 4mm),
  {self._breadcrumb(manifest, manifest.link_or_content(self.board_index_id(index), projects))},
  {header},
  {kanban}
)"""
