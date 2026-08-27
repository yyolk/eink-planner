"""Wire sections → manifest → pages → builder."""

from __future__ import annotations

from typing import Any

from parch import ConfigError
from parch.config import StrictDict, _to_plain
from parch.i18n import I18n
from parch.mos.builder import Builder
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.mos.sections.annual import Annual
from parch.mos.sections.cover_plain import CoverPlain
from parch.mos.sections.index import Index
from parch.mos.sections.daily import Daily
from parch.mos.sections.daily_notes import DailyNotes
from parch.mos.sections.monthly import Monthly
from parch.mos.sections.quarterly import Quarterly
from parch.mos.sections.habits import Habits
from parch.mos.sections.meetings import Meetings
from parch.mos.sections.projects import Projects
from parch.mos.sections.review import Review
from parch.mos.sections.tasks import Tasks
from parch.mos.sections.weekly import Weekly
from parch.sections.colophon import Colophon


COMPONENTS = {
    "cover_plain": CoverPlain,
    "index": Index,
    "annual": Annual,
    "quarterly": Quarterly,
    "monthly": Monthly,
    "weekly": Weekly,
    "daily": Daily,
    "daily_notes": DailyNotes,
    "projects": Projects,
    "meetings": Meetings,
    "habits": Habits,
    "review": Review,
    "tasks": Tasks,
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
