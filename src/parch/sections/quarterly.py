"""One page per quarter."""

from __future__ import annotations

from typing import Any

from parch.calendar import walk
from parch.compose.ctx import ComposeCtx
from parch.config import StrictDict, _to_plain
from parch.mos.manifest import Manifest
from parch.mos.page_data import PageData
from parch.mos.pages.quarterly import Quarterly as QuarterlyPage
from parch.sections.annual import Annual


class Quarterly:
    def __init__(
        self,
        section_name: str,
        ctx: ComposeCtx,
        months_column: str,
        pattern: str = "dotted",
        **other: Any,
    ) -> None:
        self.section_name = section_name
        self.i18n = ctx.i18n
        self.configurator = ctx.configurator
        self.months_column = str(months_column).lstrip(":").lower()
        self.pattern = pattern
        base = self.configurator.dig("planner", "params", "little_calendar") or {}
        extra = other.get("little_calendar") or {}
        self.little_calendar = {**_plain(base), **_plain(extra)}

    def register(self, manifest: Manifest) -> None:
        for quarter in self._range():
            manifest.register_source(quarter.id)

    def pages(self, manifest: Manifest) -> list[PageData]:
        out = []
        for quarter in self._range():
            page = QuarterlyPage(
                i18n=self.i18n,
                manifest=manifest,
                quarter=quarter,
                months_column=self.months_column,
                little_calendar=self.little_calendar,
                pattern=self.pattern,
            )
            out.append(
                PageData(
                    title=self._title(manifest, page),
                    content=page.content(),
                    highlight_quarters=[quarter],
                    nav_links=[],
                )
            )
        return out

    def _year(self) -> int:
        return self.configurator.start_date().year

    def _year_cell(self, manifest: Manifest) -> str:
        return manifest.link_or_content(Annual.ID, str(self._year()))

    def _title(self, manifest: Manifest, page: QuarterlyPage) -> str:
        return f"""grid(
  columns: (auto, auto, auto),
  column-gutter: 6pt,
  align: horizon,
  text(size: h1, {self._year_cell(manifest)}),
  text(size: h1)[/],
  {page.title()}
)"""

    def _range(self):
        return walk(self.configurator.start_date().quarter(), self.configurator.end_date().quarter())


def _plain(value: Any) -> dict:
    if isinstance(value, StrictDict):
        return value.to_plain()
    if isinstance(value, dict):
        return _to_plain(value)
    return {}
