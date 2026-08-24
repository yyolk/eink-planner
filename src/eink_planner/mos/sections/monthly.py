"""One page per month."""

from __future__ import annotations

from typing import Any

from eink_planner.calendar import walk
from eink_planner.config import StrictDict, _to_plain
from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.manifest import Manifest
from eink_planner.mos.page_data import PageData
from eink_planner.mos.pages.monthly import Monthly as MonthlyPage


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
                    title=page.title(),
                    content=page.content(),
                    highlight_months=[month],
                    highlight_quarters=[month.quarter()],
                )
            )
        return out

    def _range(self):
        return walk(self.configurator.start_date().month(), self.configurator.end_date().month())
