"""One page per day in the configured range."""

from __future__ import annotations

from typing import Any

from parch.calendar import walk
from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.mos.page_data import PageData
from parch.mos.pages.daily import Daily as DailyPage
from parch.mos.sections.annual import Annual


class Daily:
    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        **params: Any,
    ) -> None:
        self.section_name = section_name
        self.i18n = i18n
        self.configurator = configurator
        # Coordinator also passes manifest=; do not forward it to the page.
        params.pop("manifest", None)
        self.params = params

    def register(self, manifest: Manifest) -> None:
        for day in self._range():
            manifest.register_source(day.id)

    def pages(self, manifest: Manifest) -> list[PageData]:
        out = []
        year = str(self.configurator.start_date().year)
        for day in self._range():
            page = DailyPage(
                i18n=self.i18n,
                manifest=manifest,
                day=day,
                debug=self.configurator.debug(),
                **self.params,
            )
            out.append(
                PageData(
                    title=page.title(),
                    content=page.content(),
                    highlight_months=[day.month()],
                    highlight_quarters=[],
                    nav_links=[(Annual.ID, year)],
                )
            )
        return out

    def _range(self):
        return walk(self.configurator.start_date(), self.configurator.end_date())
