"""Wire sections → manifest → pages → builder."""

from __future__ import annotations

from typing import Any

from eink_planner import ConfigError
from eink_planner.config import StrictDict, _to_plain
from eink_planner.i18n import I18n
from eink_planner.mos.builder import Builder
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.manifest import Manifest
from eink_planner.mos.sections.annual import Annual
from eink_planner.mos.sections.cover_plain import CoverPlain
from eink_planner.mos.sections.daily import Daily
from eink_planner.mos.sections.daily_notes import DailyNotes
from eink_planner.mos.sections.monthly import Monthly
from eink_planner.mos.sections.quarterly import Quarterly
from eink_planner.mos.sections.projects import Projects
from eink_planner.mos.sections.weekly import Weekly
from eink_planner.sections.colophon import Colophon


COMPONENTS = {
    "cover_plain": CoverPlain,
    "annual": Annual,
    "quarterly": Quarterly,
    "monthly": Monthly,
    "weekly": Weekly,
    "daily": Daily,
    "daily_notes": DailyNotes,
    "projects": Projects,
    "colophon": Colophon,
}


class Coordinator:
    def __init__(self, dto: StrictDict | dict[str, Any], i18n: I18n) -> None:
        self.i18n = i18n
        self.configurator = Configurator(dto)
        self.manifest = Manifest()

    def generate(self) -> str:
        builder = Builder(i18n=self.i18n, configurator=self.configurator, manifest=self.manifest)
        sections = [self._section(dto) for dto in self.configurator.enabled_sections()]
        for section in sections:
            self.manifest.register_section(section.section_name)
        for section in sections:
            section.register(self.manifest)
        pages = []
        for section in sections:
            pages.extend(section.pages(self.manifest))
        for page in pages:
            builder.add(page)
        return builder.generate()

    def _section(self, dto: Any):
        if isinstance(dto, StrictDict):
            klass_name = dto["class"]
            section_name = dto["name"]
            params = dto.get("params", {})
            params = _to_plain(params) if isinstance(params, (StrictDict, dict)) else {}
        else:
            klass_name = dto["class"]
            section_name = dto["name"]
            params = dto.get("params") or {}
        klass = COMPONENTS.get(klass_name)
        if klass is None:
            raise ConfigError(f"unknown component: {klass_name}")
        return klass(
            section_name=section_name,
            i18n=self.i18n,
            manifest=self.manifest,
            configurator=self.configurator,
            **_normalize_keys(params),
        )


def _normalize_keys(params: dict[str, Any]) -> dict[str, Any]:
    """Accept YAML hyphen keys (row-gutter) as snake_case kwargs."""
    out: dict[str, Any] = {}
    for key, value in params.items():
        out[str(key).replace("-", "_")] = value
    return out
