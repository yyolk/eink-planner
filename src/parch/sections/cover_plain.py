"""Plain cover page (raw Typst, no MOS chrome)."""

from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.compose.page_data import PageData
from parch.sections.annual import Annual
from parch.sections.index import Index


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

    def pages(self, manifest) -> list[PageData]:
        return [PageData(raw_typst=True, content=self._cover(manifest))]

    def _lines(self) -> list[str]:
        return [line for line in str(self.name).split("\n") if line.strip()]

    def _dest(self, manifest) -> str | None:
        """Contents if that source is on, else Annual."""
        if manifest is None:
            return None
        if manifest.source(Index.ID):
            return Index.ID
        if manifest.source(Annual.ID):
            return Annual.ID
        return None

    def _year(self, size: str, year: str, dest: str | None, manifest) -> str:
        """Year as a door when dest is registered."""
        if dest is None:
            return f"text(size: {size})[{year}]"
        return f"text(size: {size}, {manifest.link_or_content(dest, year)})"

    def _cover(self, manifest) -> str:
        lines = [_escape(line) for line in self._lines()]
        size = self.font_size
        dest = self._dest(manifest)
        if not lines:
            body = "[]"
        elif len(lines) == 1:
            body = self._year(size, lines[0], dest, manifest)
        else:
            parts = [self._year(size, lines[0], dest, manifest)]
            parts.extend(f"text(size: {size} * 0.45)[{line}]" for line in lines[1:])
            body = f"stack(spacing: {size} * 0.12, {', '.join(parts)})"
        return f"""#grid(
  columns: 1fr,
  rows: (1fr, 2fr),
  align: center + horizon,
  {body}
)"""
