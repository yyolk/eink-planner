"""Select a chase from template and compose Typst; Coordinator fills the manifest from each section."""

from __future__ import annotations

from typing import Any

from parch import ConfigError
from parch.config import StrictDict
from parch.i18n import I18n
from parch.mos.chase import CHASES
from parch.mos.coordinator import Coordinator


class Generate:
    def __init__(self, i18n: I18n) -> None:
        self.i18n = i18n

    def generate(self, data: StrictDict | dict[str, Any]) -> str:
        dto = data if isinstance(data, StrictDict) else StrictDict(data)
        return self._select_planner(dto).generate()

    def _select_planner(self, dto: StrictDict) -> Coordinator:
        name = dto.get("template") or "mos"
        if name not in CHASES:
            raise ConfigError(f"unknown chase: {name}")
        return Coordinator(dto, i18n=self.i18n, chase_name=name)
