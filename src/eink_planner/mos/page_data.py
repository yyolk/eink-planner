"""Page payload handed from a section to the builder."""

from __future__ import annotations

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

    def raw_typst_q(self) -> bool:
        return self.raw_typst
