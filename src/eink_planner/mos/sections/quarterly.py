"""One page per quarter."""

from __future__ import annotations

from typing import Any

from eink_planner.calendar import walk
from eink_planner.config import StrictDict, _to_plain
from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.manifest import Manifest
from eink_planner.mos.page_data import PageData
from eink_planner.mos.pages.quarterly import Quarterly as QuarterlyPage


class Quarterly:
    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        months_column: str,
        **other: Any,
    ) -> None:
        self.section_name = section_name
        self.i18n = i18n
        self.configurator = configurator
        self.months_column = str(months_column).lstrip(":").lower()
        base = configurator.dig("planner", "params", "little_calendar") or {}
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
            )
            out.append(
                PageData(
                    title=page.title(),
                    content=page.content(),
                    highlight_quarters=[quarter],
                )
            )
        return out

    def _range(self):
        return walk(self.configurator.start_date().quarter(), self.configurator.end_date().quarter())


def _plain(value: Any) -> dict:
    if isinstance(value, StrictDict):
        return value.to_plain()
    if isinstance(value, dict):
        return _to_plain(value)
    return {}
