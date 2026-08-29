"""Section is the existing MOS contract. Chase is a target protocol."""

from __future__ import annotations

from typing import Protocol

from parch.compose.manifest import Manifest
from parch.compose.page_data import PageData


class Section(Protocol):
    """section — cover, daily, habits, … Owns ids + bodies."""

    section_name: str

    def register(self, manifest: Manifest) -> None: ...

    def pages(self, manifest: Manifest) -> list[PageData]: ...


class Chase(Protocol):
    """chase — frame around a body. MOS is one chase. raw_typst=True means no chase."""

    name: str

    def wrap(self, page: PageData, manifest: Manifest) -> str:
        """If page.raw_typst, return page.content; else apply chase chrome. MOS chromes in Builder.add / Builder._layout_page."""
        ...
