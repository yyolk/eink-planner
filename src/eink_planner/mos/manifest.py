"""Registered page/source ids used for intra-PDF links."""

from __future__ import annotations


class Manifest:
    def __init__(self) -> None:
        self._sources: set[str] = set()
        self._sections: set[str] = set()

    def register_source(self, source_id: str) -> None:
        self._sources.add(source_id)

    def source(self, source_id: str) -> bool:
        return source_id in self._sources

    # Ruby alias source?
    def source_q(self, source_id: str) -> bool:
        return self.source(source_id)

    def register_section(self, name: str) -> None:
        self._sections.add(name)

    def sections(self) -> set[str]:
        return set(self._sections)
