"""Page payload a section hands to compose."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PageData:
    content: str
    raw_typst: bool = False
    title: str | None = None
    page_id: str | None = None
    highlight_months: list[Any] = field(default_factory=list)
    highlight_quarters: list[Any] = field(default_factory=list)
    month_link_id: Callable[[Any], str] | None = None
    nav_links: list[tuple[str, str]] | None = None
    show_quarters: bool = True
    heading_dir: str | None = None

    def raw_typst_q(self) -> bool:
        return self.raw_typst
