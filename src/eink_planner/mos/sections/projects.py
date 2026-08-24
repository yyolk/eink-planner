"""Projects index and per-project kanban boards (raw Typst, no MOS chrome)."""

from __future__ import annotations

from typing import Any

from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.manifest import Manifest
from eink_planner.mos.page_data import PageData
from eink_planner.mos.sections.annual import Annual


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
        manifest.register_source(self.ID)
        for index in range(1, self.pages_num + 1):
            manifest.register_source(self.board_id(index))

    @staticmethod
    def board_id(index: int) -> str:
        return f"project-{index}"

    def pages(self, manifest: Manifest) -> list[PageData]:
        out = [PageData(raw_typst=True, content=self._index(manifest))]
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

    def _index(self, manifest: Manifest) -> str:
        label = self.i18n.t("projects")
        n = self.pages_num
        if n:
            rows = []
            for index in range(1, n + 1):
                bid = self.board_id(index)
                number = manifest.link_or_content(bid, str(index))
                arrow = manifest.link_or_content(bid, "→")
                rows.append(f"  {number}, [], {arrow}")
            body = f"""grid(
  columns: (auto, 1fr, auto),
  rows: ({", ".join(["2.5 * regular_height"] * n)}),
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
  row-gutter: 3mm,
  inset: (left: 4mm, bottom: 4mm),
  {self._breadcrumb(manifest, f"[{label} <{self.ID}>]")},
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
        card = "grid.cell(stroke: regular_stroke, inset: 0pt, rect_pattern(dotted))"
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
  {self._breadcrumb(manifest, manifest.link_or_content(self.ID, projects))},
  {header},
  {kanban}
)"""
