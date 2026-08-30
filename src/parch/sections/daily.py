"""One page per day in the configured range."""

from __future__ import annotations

from typing import Any

from parch.calendar import walk
from parch.compose.ctx import ComposeCtx
from parch.mos.manifest import Manifest
from parch.mos.page_data import PageData
from parch.mos.pages.daily import Daily as DailyPage
from parch.sections.annual import Annual


class Daily:
    def __init__(self, section_name: str, ctx: ComposeCtx, **params: Any) -> None:
        self.section_name = section_name
        self.i18n = ctx.i18n
        self.configurator = ctx.configurator
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
