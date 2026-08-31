"""Rotated months strip in the side menu."""

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
        self.highlighted: list[Month] = []
        self.month_link_id = month_link_id

    def highlight(self, items: list[Month] | None = None) -> list[Month]:
        self.highlighted = list(items or [])
        return self.highlighted

    def generate(self) -> str:
        cols = ", ".join(["1fr"] * len(self.range))
        return f"""table(
  stroke: regular_stroke,
  columns: ({cols}),
  rows: 1fr,
  align: horizon + center,

  {self._months()}
)"""

    def _months(self) -> str:
        return ",\n".join(self._format(month) for month in self.range)

    def _target(self, month: Month) -> str:
        if self.month_link_id is None:
            return month.id
        return self.month_link_id(month)

    def _format(self, month: Month) -> str:
        label = self.manifest.link_or_content(self._target(month), self.i18n.t(f"months.short.{month.name}"))
        if month in self.highlighted:
            return f"table.cell(fill: black, text(white)[#{label}])"
        return f"table.cell([#{label}])"
