"""Plain cover page (raw Typst, no MOS chrome)."""

from __future__ import annotations

from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.compose.page_data import PageData


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("#", "\\#")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


class CoverPlain:
    def __init__(self, section_name: str, i18n: I18n, configurator: Configurator, name: str, font_size: str) -> None:
        self.section_name = section_name
        self.name = name
        self.font_size = font_size

    def register(self, _manifest) -> None:
        return None

    def pages(self, _manifest) -> list[PageData]:
        return [PageData(raw_typst=True, content=self._cover())]

    def _lines(self) -> list[str]:
        return [line for line in str(self.name).split("\n") if line.strip()]

    def _cover(self) -> str:
        lines = [_escape(line) for line in self._lines()]
        size = self.font_size
        if not lines:
            body = "[]"
        elif len(lines) == 1:
            body = f"text(size: {size})[{lines[0]}]"
        else:
            parts = [f"text(size: {size})[{lines[0]}]"]
            parts.extend(f"text(size: {size} * 0.45)[{line}]" for line in lines[1:])
            body = f"stack(spacing: {size} * 0.12, {', '.join(parts)})"
        return f"""#grid(
  columns: 1fr,
  rows: (1fr, 2fr),
  align: center + horizon,
  {body}
)"""
