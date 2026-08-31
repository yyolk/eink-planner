"""One page per quarter."""

from typing import Any

from parch.calendar import walk
from parch.config import StrictDict, _to_plain
from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.compose.page_data import PageData
from parch.mos.pages.quarterly import Quarterly as QuarterlyPage
from parch.sections._shared import _side_menu_position


class Quarterly:
    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        pattern: str = "dotted",
        **other: Any,
    ) -> None:
        self.section_name = section_name
        self.i18n = i18n
        self.configurator = configurator
        self.pattern = pattern
        base = self.configurator.dig("planner", "params", "little_calendar") or {}
        extra = other.get("little_calendar") or {}
        self.little_calendar = {**_plain(base), **_plain(extra)}
        self.side = _side_menu_position(configurator)

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
                little_calendar=self.little_calendar,
                pattern=self.pattern,
                side=self.side,
            )
            out.append(
                PageData(
                    title=page.title(),
                    content=page.content(),
                    highlight_quarters=[quarter],
                    nav_links=[],
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
