"""Plain cover page (raw Typst, no MOS chrome)."""

from __future__ import annotations

from typing import Any

from eink_planner.mos.page_data import PageData


class CoverPlain:
    def __init__(self, section_name: str, name: str, font_size: str, **_rest: Any) -> None:
        self.section_name = section_name
        self.name = name
        self.font_size = font_size

    def register(self, _manifest) -> None:
        return None

    def pages(self, _manifest) -> list[PageData]:
        return [PageData(raw_typst=True, content=self._cover())]

    def _cover(self) -> str:
        # YAML "2026\\n\\nPlanner" → Typst line breaks
        name = str(self.name).replace("\n", " \\ ")
        return f"""#grid(
  columns: 1fr,
  rows: 1fr,
  align: center + horizon,

  text(size: {self.font_size})[{name}]
)"""
