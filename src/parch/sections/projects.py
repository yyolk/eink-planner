"""Projects index and per-project kanban boards (raw Typst, no MOS chrome)."""

from __future__ import annotations

import math

from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.mos.contents_mark import body_size_token, heading_height_token, trail_heading
from parch.compose.page_data import HeadingMark, PageData
from parch.sections._shared import _length_mm

# Match the index page chrome in `_index` so row capacity tracks the layout.
_INDEX_LEFT_INSET = "4mm"
_INDEX_BOTTOM_INSET = "4mm"
_INDEX_ROW_GUTTER = "3mm"
_ROW_HEIGHT = "2 * regular_height"
_ROW_HEIGHT_MULT = 2
# Two figures share an x, like Review week numbers. Write-in is the 1fr paper.
_NUM_COL = "2em"


class Projects:
    ID = "projects"
    DEFAULT_PAGES = 16
    CARDS = 5

    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        pages: int = DEFAULT_PAGES,
        card_rows: int = CARDS,
    ) -> None:
        self.section_name = section_name
        self.i18n = i18n
        self.configurator = configurator
        self.pages_num = int(pages)
        self.card_rows = int(card_rows)

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
            out.append(
                PageData(
                    raw_typst=True,
                    content=self._index(manifest, page, start, end),
                    heading_mark=HeadingMark.FOLLOW,
                )
            )
        for index in range(1, self.pages_num + 1):
            out.append(
                PageData(
                    raw_typst=True,
                    content=self._board(manifest, index),
                    heading_mark=HeadingMark.FOLLOW,
                )
            )
        return out

    def _heading(self, manifest: Manifest, projects_cell: str) -> str:
        return trail_heading(
            manifest,
            heading_height_token(self.configurator),
            f"text(size: h1, {projects_cell})",
            body_size_token(self.configurator),
            direction="rtl",
            edge="follow",
        )

    def _index_projects_cell(self, manifest: Manifest, page: int) -> str:
        label = self.i18n.t("projects")
        page_id = self.index_page_id(page)
        if page <= 1:
            return f"[{label} <{page_id}>]"
        return f"[#{manifest.link_or_content(self.ID, label)} <{page_id}>]"

    def _index_row(self, manifest: Manifest, index: int) -> str:
        bid = self.board_id(index)
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
        if manifest.source(bid):
            band = f"padded_link(<{bid}>, {band})"
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
            # Fixed 2×-regular_height rows. Leftover last pages keep the same
            # height (white below) — never 1fr-fatten a short leftover.
            body = f"""grid(
  columns: 1fr,
  rows: ({", ".join([_ROW_HEIGHT] * n)}),
  align: horizon + left,
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
  {self._heading(manifest, self._index_projects_cell(manifest, page))},
  {body}
)"""

    def _board(self, manifest: Manifest, index: int) -> str:
        projects = self.i18n.t("projects")
        todo = self.i18n.t("todo")
        doing = self.i18n.t("doing")
        done = self.i18n.t("done")
        bid = self.board_id(index)
        projects_cell = manifest.link_or_content(self.board_index_id(index), projects)
        name_line = f"""grid(
  columns: 1fr,
  align: horizon,
  grid.cell(stroke: (bottom: regular_stroke), []),
)"""
        quiet = f"text(size: 0.85em)[{index}]"
        kanban = f"""grid(
  columns: (1fr, 1fr, 1fr),
  rows: (auto, 1fr),
  column-gutter: regular_column_gutter,
  row-gutter: 2mm,
  align(center)[*{todo}*],
  align(center)[*{doing}*],
  align(center)[*{done}*],
  rect_pattern(dotted),
  rect_pattern(dotted),
  rect_pattern(dotted)
)"""
        return f"""#[] <{bid}>
#grid(
  columns: 1fr,
  rows: (auto, auto, auto, 1fr),
  row-gutter: 2.5mm,
  inset: (left: 4mm, bottom: 4mm),
  {self._heading(manifest, projects_cell)},
  {quiet},
  {name_line},
  {kanban}
)"""
