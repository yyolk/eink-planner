"""One page per month."""

from __future__ import annotations

from typing import Any

from parch.calendar import walk
from parch.config import StrictDict, _to_plain
from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.mos.page_data import PageData
from parch.mos.pages.monthly import Monthly as MonthlyPage
from parch.mos.sections.annual import Annual


class Monthly:
    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        month_params: dict[str, Any],
        pattern: str = "dotted",
        **_rest: Any,
    ) -> None:
        self.section_name = section_name
        self.i18n = i18n
        self.configurator = configurator
        if isinstance(month_params, StrictDict):
            month_params = month_params.to_plain()
        self.month_params = _to_plain(month_params)
        self.pattern = pattern

    def register(self, manifest: Manifest) -> None:
        for month in self._range():
            manifest.register_source(month.id)

    def pages(self, manifest: Manifest) -> list[PageData]:
        out = []
        for month in self._range():
            page = MonthlyPage(
                i18n=self.i18n,
                manifest=manifest,
                month=month,
                month_params=self.month_params,
                pattern=self.pattern,
            )
            out.append(
                PageData(
                    title=self._title(manifest, page),
                    content=page.content(),
                    highlight_months=[month],
                    highlight_quarters=[],
                    nav_links=[],
                )
            )
        return out

    def _year(self) -> int:
        return self.configurator.start_date().year

    def _year_cell(self, manifest: Manifest) -> str:
        return manifest.link_or_content(Annual.ID, str(self._year()))

    def _title(self, manifest: Manifest, page: MonthlyPage) -> str:
        return f"""grid(
  columns: (auto, auto, 1fr),
  column-gutter: 6pt,
  align: horizon,
  text(size: h1, {self._year_cell(manifest)}),
  text(size: h1)[/],
  {page.title()}
)"""

    def _range(self):
        return walk(self.configurator.start_date().month(), self.configurator.end_date().month())
