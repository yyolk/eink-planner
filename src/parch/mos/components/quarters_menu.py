"""Year quarter dest/label pairs for mos_strip."""

from collections.abc import Sequence

from parch.calendar.quarter import Quarter
from parch.i18n import I18n
from parch.mos.manifest import Manifest


class QuartersMenu:
    def __init__(self, i18n: I18n, manifest: Manifest, range: Sequence[Quarter]) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.range = list(range)

    def generate(self) -> str:
        items = ", ".join(self._pair(quarter) for quarter in self.range)
        return f"({items},)" if self.range else "()"

    def _pair(self, quarter: Quarter) -> str:
        dest = self.manifest.dest(quarter.id)
        label = f"{self.i18n.t('quarter.short')}{quarter.number}"
        return f"({dest}, [{label}])"
