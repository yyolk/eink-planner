"""Select a chase and compose Typst; Coordinator fills the manifest from each section."""

from typing import Any

from parch import ConfigError
from parch.compose.coordinator import Coordinator
from parch.config import StrictDict
from parch.i18n import I18n
from parch.mos.chase import CHASES


class Generate:
    def __init__(self, i18n: I18n) -> None:
        self.i18n = i18n

    def generate(self, data: StrictDict | dict[str, Any]) -> str:
        dto = data if isinstance(data, StrictDict) else StrictDict(data)
        return self._select_chase(dto).generate()

    def _select_chase(self, dto: StrictDict) -> Coordinator:
        name = dto.get("chase", "mos")
        if not isinstance(name, str) or name not in CHASES:
            raise ConfigError(f"unknown chase: {name}")
        return Coordinator(dto, i18n=self.i18n, chase_name=name)
