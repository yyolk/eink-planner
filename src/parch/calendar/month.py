"""Month entity — port of LYP::Entities::Calendar::Month."""

from typing import TYPE_CHECKING

from parch import InternalError

if TYPE_CHECKING:
    from parch.calendar.day import Day
    from parch.calendar.quarter import Quarter

_MONTH_NAMES = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)


class Month:
    def __init__(self, weekday_start: str, day: Day) -> None:
        from parch.calendar.day import Day as DayCls

        if not isinstance(day, DayCls):
            raise InternalError("Month.day must be a Day")
        self.weekday_start = weekday_start
        self.day = day.beginning_of_month()

    @property
    def id(self) -> str:
        return f"month-{self.day.id}"

    @property
    def name(self) -> str:
        return _MONTH_NAMES[self.day.day.month - 1]

    def succ(self) -> Month:
        return Month(weekday_start=self.weekday_start, day=self.day.next_month())

    def quarter(self) -> Quarter:
        return self.day.quarter()

    def _require_same(self, other: object) -> Month:
        if not isinstance(other, Month):
            raise TypeError("must be Month")
        if self.weekday_start != other.weekday_start:
            raise ValueError("weekday start must match")
        return other

    def __lt__(self, other: object) -> bool:
        return self.day < self._require_same(other).day

    def __le__(self, other: object) -> bool:
        return self.day <= self._require_same(other).day

    def __gt__(self, other: object) -> bool:
        return self.day > self._require_same(other).day

    def __ge__(self, other: object) -> bool:
        return self.day >= self._require_same(other).day

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Month):
            return False
        return self.weekday_start == other.weekday_start and self.day == other.day

    def __hash__(self) -> int:
        return hash((self.weekday_start, self.day))

    def __repr__(self) -> str:
        return f"Month({self.day.strftime('%Y-%m')} wd={self.weekday_start})"

    def __str__(self) -> str:
        return f"{self.day.strftime('%Y, %B')} (wd: {self.weekday_start})"
