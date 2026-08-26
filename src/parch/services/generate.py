"""Select a planner template and emit Typst source."""

from __future__ import annotations

from typing import Any

from parch import ConfigError
from parch.config import StrictDict
from parch.i18n import I18n
from parch.mos.coordinator import Coordinator


class Generate:
    def __init__(self, i18n: I18n) -> None:
        self.i18n = i18n

    def generate(self, data: StrictDict | dict[str, Any]) -> str:
        dto = data if isinstance(data, StrictDict) else StrictDict(data)
        return self._select_planner(dto).generate()

    def _select_planner(self, dto: StrictDict) -> Coordinator:
        template = dto.get("template")
        if template == "mos":
            return Coordinator(dto, i18n=self.i18n)
        raise ConfigError(f"Bad template: {template}")
