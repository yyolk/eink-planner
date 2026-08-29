"""Assemble preamble + section pages; chase and compose share render() for one manifest."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.mos.navigation import NavLink, Navigation
from parch.mos.page_data import PageData
from parch.mos.contents_mark import body_size_token, lead_title, trail_strip
from parch.mos.preamble import Preamble


class Builder:
    def __init__(self, i18n: I18n, configurator: Configurator, manifest: Manifest) -> None:
        self.configurator = configurator
        self.manifest = manifest
        self.pages: list[str] = []
        self.preamble = Preamble(configurator)
        self.navigation = Navigation(i18n=i18n, manifest=manifest, configurator=configurator)
        self.mos_layout = configurator.dig_bang("planner", "params", "mos_layout")
        self.heading = configurator.dig_bang("planner", "params", "heading")

    def generate(self) -> str:
        body = "\n#pagebreak()\n".join(self.pages)
        return f"{self.preamble.generate()}\n{body}"

    def render(self, page: PageData) -> str:
        if page.raw_typst:
            return page.content
        return self._layout_page(page)

    def add(self, page_spec: PageData) -> str:
        typst = self.render(page_spec)
        self.pages.append(typst)
        return typst

    def _layout_page(self, page_spec: PageData) -> str:
        debug_stroke = "stroke: regular_stroke,\n      " if self.configurator.debug() else ""
        heading = self._heading_content(
            title=page_spec.title,
            highlight_months=page_spec.highlight_months,
            highlight_quarters=page_spec.highlight_quarters,
            page_id=page_spec.page_id,
            month_link_id=page_spec.month_link_id,
            nav_links=page_spec.nav_links,
            show_quarters=page_spec.show_quarters,
            heading_dir=page_spec.heading_dir,
        )
        return f"""#grid(
  columns: ({self._heading_columns()}),
  rows: ({_v(self.heading, 'height')}, 1fr),
  column-gutter: {_v(self.mos_layout, 'column_gutter')},
  row-gutter: {_v(self.mos_layout, 'row_gutter')},
  {debug_stroke}
  {heading},
  {page_spec.content}
)"""

    def _heading_columns(self) -> str:
        columns = [_v(self.mos_layout, "side_menu_width"), "1fr"]
        if _v(self.mos_layout, "side_menu_position") == "right":
            columns = list(reversed(columns))
        return ", ".join(str(c) for c in columns)

    def _heading_content(
        self,
        title: str | None,
        page_id: str | None,
        highlight_months,
        highlight_quarters,
        month_link_id: Callable[[Any], str] | None = None,
        nav_links: list[tuple[str, str] | NavLink] | None = None,
        show_quarters: bool = True,
        heading_dir: str | None = None,
    ) -> str:
        row = [
            self.navigation.side_menu_cell(
                highlight_months=highlight_months,
                highlight_quarters=highlight_quarters,
                month_link_id=month_link_id,
                show_quarters=show_quarters,
            ),
            f"grid.cell(align: {_v(self.heading, 'align')}, {self._heading_stack(page_id, title, nav_links, heading_dir)})",
        ]
        if _v(self.mos_layout, "side_menu_position") == "right":
            row.reverse()
        return ", ".join(row)

    def _heading_stack(
        self,
        page_id: str | None,
        title: str | None,
        nav_links: list[tuple[str, str] | NavLink] | None = None,
        heading_dir: str | None = None,
    ) -> str:
        mos_right = _v(self.mos_layout, "side_menu_position") == "right"
        if heading_dir is None:
            direction = "ltr" if mos_right else "rtl"
        else:
            direction = heading_dir
        chip = self.navigation.heading_menu_grid(page_id=page_id, nav_links=nav_links)
        height = _v(self.heading, "height")
        body = body_size_token(self.configurator)
        trailing = trail_strip(self.manifest, height, body, chip)
        if mos_right or chip or (trailing and page_id == "annual"):
            parts = [p for p in (title, trailing) if p]
        elif title:
            parts = [lead_title(self.manifest, height, title, body)]
        else:
            parts = []
        joined = ",\n".join(parts)
        return f"""stack(
  dir: {direction},
  spacing: 1fr,
  {joined}
)"""


def _v(mapping, key: str):
    return mapping[key]
