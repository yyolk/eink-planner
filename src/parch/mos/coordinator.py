"""compose: resolve each section from SECTIONS, fill the manifest, wrap pages through chase."""

from __future__ import annotations

from typing import Any

from parch import ConfigError
from parch.config import StrictDict, _to_plain
from parch.i18n import I18n
from parch.mos.chase import CHASES
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest


class Coordinator:
    def __init__(self, dto: StrictDict | dict[str, Any], i18n: I18n, chase_name: str = "mos") -> None:
        self.i18n = i18n
        self.configurator = Configurator(dto)
        self.manifest = Manifest()
        if chase_name not in CHASES:
            raise ConfigError(f"unknown chase: {chase_name}")
        self.chase = CHASES[chase_name](
            i18n=self.i18n, configurator=self.configurator, manifest=self.manifest
        )

    def section_pages(self) -> list[tuple[str, list]]:
        """Enabled sections in order, each with the pages it contributes."""
        sections = [self._section(dto) for dto in self.configurator.enabled_sections()]
        for section in sections:
            self.manifest.register_section(section.section_name)
        for section in sections:
            section.register(self.manifest)
        return [(section.section_name, section.pages(self.manifest)) for section in sections]

    def generate(self) -> str:
        for _name, pages in self.section_pages():
            for page in pages:
                self.chase.wrap(page, self.manifest)
        return self.chase.document()

    def _section(self, dto: Any):
        from parch.sections import SECTIONS  # late: sections/__init__ importing MOS pages still runs mos/__init__

        if isinstance(dto, StrictDict):
            klass_name = dto["class"]
            section_name = dto["name"]
            params = dto.get("params", {})
            params = _to_plain(params) if isinstance(params, (StrictDict, dict)) else {}
        else:
            klass_name = dto["class"]
            section_name = dto["name"]
            params = dto.get("params") or {}
        klass = SECTIONS.get(klass_name)
        if klass is None:
            raise ConfigError(f"unknown section: {klass_name}")
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
