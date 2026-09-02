"""Side-menu and heading navigation (port of LYP::Planners::MOS::Navigation)."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from parch.calendar import walk
from parch.calendar.month import Month
from parch.i18n import I18n
from parch.mos.components.months_menu import MonthsMenu
from parch.mos.components.quarters_menu import QuartersMenu
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest


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

    def year_month_items(self, month_link_id: Callable[[Month], str] | None = None) -> str:
        months = list(walk(self.start_date.month(), self.end_date.month()))
        if _v(self.mos_layout, "reverse_months_quarters_items"):
            months.reverse()
        return MonthsMenu(
            i18n=self.i18n,
            manifest=self.manifest,
            range=months,
            month_link_id=month_link_id,
        ).generate()

    def year_quarter_items(self) -> str:
        quarters = list(walk(self.start_date.quarter(), self.end_date.quarter()))
        if _v(self.mos_layout, "reverse_months_quarters_items"):
            quarters.reverse()
        return QuartersMenu(i18n=self.i18n, manifest=self.manifest, range=quarters).generate()

    def side_menu_cell(
        self,
        highlight_months: list[Any],
        highlight_quarters: list[Any],
        month_link_id: Callable[[Month], str] | None = None,
        show_quarters: bool = True,
    ) -> str:
        month_dests = self._highlight_dests(highlight_months, month_link_id)
        quarter_dests = self._highlight_dests(highlight_quarters)
        parts = [
            f"highlight-months: {_dest_array(month_dests)}",
            f"highlight-quarters: {_dest_array(quarter_dests)}",
        ]
        if month_link_id is not None:
            parts.insert(0, f"months: {self.year_month_items(month_link_id)}")
        if not show_quarters:
            parts.append("show-quarters: false")
        return f"mos_strip({', '.join(parts)})"

    def heading_menu_grid(
        self,
        page_id: str | None,
        nav_links: list[tuple[str, str] | NavLink] | None = None,
    ) -> str | None:
        links = self._nav_links(page_id, nav_links)
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

    def _coerce_nav_links(
        self, nav_links: list[tuple[str, str] | NavLink] | None
    ) -> list[NavLink]:
        out: list[NavLink] = []
        if not nav_links:
            return out
        for item in nav_links:
            if isinstance(item, NavLink):
                out.append(item)
            else:
                out.append(NavLink(id=item[0], label=item[1]))
        return out

    def _nav_links(
        self,
        page_id: str | None,
        nav_links: list[tuple[str, str] | NavLink] | None = None,
    ) -> list[str]:
        out: list[str] = []
        for nav in self._coerce_nav_links(nav_links):
            if not self.manifest.source(nav.id):
                continue
            link = f"padded_link(<{nav.id}>, [{nav.label}])"
            if page_id == nav.id:
                out.append(f"grid.cell(fill: black, text(white)[#{link}])")
            else:
                out.append(link)
        return out

    def _highlight_dests(
        self,
        items: list[Any],
        month_link_id: Callable[[Month], str] | None = None,
    ) -> list[str]:
        dests: list[str] = []
        for item in items:
            source_id = month_link_id(item) if month_link_id is not None else item.id
            dest = self.manifest.dest(source_id)
            if dest != "none":
                dests.append(dest)
        return dests


def _dest_array(dests: list[str]) -> str:
    if not dests:
        return "()"
    return f"({', '.join(dests)},)"


def _v(mapping, key: str):
    if hasattr(mapping, "__getitem__"):
        return mapping[key]
    return mapping[key]
