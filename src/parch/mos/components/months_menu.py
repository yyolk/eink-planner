"""Year month dest/label pairs for mos_strip."""

from collections.abc import Callable, Sequence

from parch.calendar.month import Month
from parch.i18n import I18n
from parch.mos.manifest import Manifest


class MonthsMenu:
    def __init__(
        self,
        i18n: I18n,
        manifest: Manifest,
        range: Sequence[Month],
        month_link_id: Callable[[Month], str] | None = None,
    ) -> None:
        self.i18n = i18n
        self.manifest = manifest
        self.range = list(range)
        self.month_link_id = month_link_id

    def generate(self) -> str:
        items = ", ".join(self._pair(month) for month in self.range)
        return f"({items},)" if self.range else "()"

    def _target(self, month: Month) -> str:
        if self.month_link_id is None:
            return month.id
        return self.month_link_id(month)

    def _pair(self, month: Month) -> str:
        dest = self.manifest.dest(self._target(month))
        label = self.i18n.t(f"months.short.{month.name}")
        return f"({dest}, [{label}])"
