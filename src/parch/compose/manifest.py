"""manifest — set of page ids for this book."""

from parch.typst_emit import typst_emit


class Manifest:
    def __init__(self) -> None:
        self._sources: set[str] = set()
        self._sections: set[str] = set()

    def register_source(self, source_id: str) -> None:
        self._sources.add(source_id)

    def source(self, source_id: str) -> bool:
        return source_id in self._sources

    def link_or_content(self, source_id: str, text: str) -> str:
        """Typst content, optionally a padded_link if that page exists.

        Always returns content ``[text]``. When *source_id* is registered,
        wraps it as ``padded_link(<id>)[text]`` so call sites can drop the
        value into a grid (code) or ``#{...}`` (content) the same way.
        """
        body = typst_emit(t"[{text}]")
        if self.source(source_id):
            return typst_emit(t"padded_link(<{source_id}>){body}")
        return body

    # Ruby alias source?
    def source_q(self, source_id: str) -> bool:
        return self.source(source_id)

    def register_section(self, name: str) -> None:
        self._sections.add(name)

    def sections(self) -> set[str]:
        return set(self._sections)
