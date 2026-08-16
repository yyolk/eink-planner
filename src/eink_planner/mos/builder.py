"""Assemble preamble + laid-out pages into one Typst document."""

from __future__ import annotations

from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.manifest import Manifest
from eink_planner.mos.navigation import Navigation
from eink_planner.mos.page_data import PageData
from eink_planner.mos.preamble import Preamble


class Builder:
    def __init__(self, i18n: I18n, configurator: Configurator, manifest: Manifest) -> None:
        self.configurator = configurator
        self.pages: list[str] = []
        self.preamble = Preamble(configurator)
        self.navigation = Navigation(i18n=i18n, manifest=manifest, configurator=configurator)
        self.mos_layout = configurator.dig_bang("planner", "params", "mos_layout")
        self.heading = configurator.dig_bang("planner", "params", "heading")

    def generate(self) -> str:
        body = "\n#pagebreak()\n".join(self.pages)
        return f"{self.preamble.generate()}\n{body}"

    def add(self, page_spec: PageData) -> None:
        if page_spec.raw_typst:
            self.pages.append(page_spec.content)
        else:
            self.pages.append(self._layout_page(page_spec))

    def _layout_page(self, page_spec: PageData) -> str:
        debug_stroke = "stroke: regular_stroke,\n      " if self.configurator.debug() else ""
        heading = self._heading_content(
            title=page_spec.title,
            highlight_months=page_spec.highlight_months,
            highlight_quarters=page_spec.highlight_quarters,
            page_id=page_spec.page_id,
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
    ) -> str:
        row = [
            self.navigation.side_menu_cell(
                highlight_months=highlight_months,
                highlight_quarters=highlight_quarters,
            ),
            f"grid.cell(align: {_v(self.heading, 'align')}, {self._heading_stack(page_id, title)})",
        ]
        if _v(self.mos_layout, "side_menu_position") == "right":
            row.reverse()
        return ", ".join(row)

    def _heading_stack(self, page_id: str | None, title: str | None) -> str:
        direction = "ltr" if _v(self.mos_layout, "side_menu_position") == "right" else "rtl"
        parts = [p for p in (title, self.navigation.heading_menu_grid(page_id=page_id)) if p]
        joined = ",\n".join(parts)
        return f"""stack(
  dir: {direction},
  spacing: 1fr,
  {joined}
)"""


def _v(mapping, key: str):
    return mapping[key]
