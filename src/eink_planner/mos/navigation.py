"""Side-menu and heading navigation (port of LYP::Planners::MOS::Navigation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eink_planner.calendar import walk
from eink_planner.i18n import I18n
from eink_planner.mos.components.months_menu import MonthsMenu
from eink_planner.mos.components.quarters_menu import QuartersMenu
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.manifest import Manifest
from eink_planner.mos.sections.annual import Annual


@dataclass(frozen=True)
class NavLink:
    id: str
    label: str


class Navigation:
    def __init__(self, i18n: I18n, manifest: Manifest, configurator: Configurator) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.mos_layout = configurator.dig_bang("planner", "params", "mos_layout")
        self.heading = configurator.dig_bang("planner", "params", "heading")
        self.start_date = configurator.start_date()
        self.end_date = configurator.end_date()

    def side_menu_cell(self, highlight_months: list[Any], highlight_quarters: list[Any]) -> str:
        cols = ["1fr", "3fr"]
        items = [
            self._quarters_menu(highlight_quarters),
            self._months_menu(highlight_months),
        ]
        if _v(self.mos_layout, "reverse_months_quarters"):
            cols.reverse()
            items.reverse()
        return f"""grid.cell(
  rowspan: 2,

  rotate(
    {_v(self.mos_layout, 'menu_rotate')},
    origin: center + horizon,
    reflow: true,

    table(
      columns: ({", ".join(cols)}),
      rows: 1fr,
      inset: 0pt,
      column-gutter: regular_column_gutter,
      stroke: 0pt,

      {",\n".join(items)}
    )
  )
)"""

    def heading_menu_grid(self, page_id: str | None) -> str | None:
        links = self._nav_links(page_id)
        if not links:
            return None
        height = _v(self.heading, "height")
        return f"""grid(
  rows: {height},
  columns: {len(links)},
  inset: 7pt,

  stroke: (x, y)  => if x > 0 {{ ( left: regular_stroke ) }},
  {", ".join(links)}
)"""

    def _candidate_links(self) -> list[NavLink]:
        return [NavLink(id=Annual.ID, label="Calendar")]

    def _nav_links(self, page_id: str | None) -> list[str]:
        out: list[str] = []
        for nav in self._candidate_links():
            if not self.manifest.source(nav.id):
                continue
            link = f"padded_link(<{nav.id}>, [{nav.label}])"
            if page_id == nav.id:
                out.append(f"grid.cell(fill: black, text(white)[#{link}])")
            else:
                out.append(link)
        return out

    def _months_menu(self, highlight_months: list[Any]) -> str:
        months = list(walk(self.start_date.month(), self.end_date.month()))
        if _v(self.mos_layout, "reverse_months_quarters_items"):
            months.reverse()
        menu = MonthsMenu(i18n=self.i18n, manifest=self.manifest, range=months)
        menu.highlight(highlight_months)
        return menu.generate()

    def _quarters_menu(self, highlight_quarters: list[Any]) -> str:
        quarters = list(walk(self.start_date.quarter(), self.end_date.quarter()))
        if _v(self.mos_layout, "reverse_months_quarters_items"):
            quarters.reverse()
        menu = QuartersMenu(i18n=self.i18n, manifest=self.manifest, range=quarters)
        menu.highlight(highlight_quarters)
        return menu.generate()


def _v(mapping, key: str):
    if hasattr(mapping, "__getitem__"):
        return mapping[key]
    return mapping[key]
