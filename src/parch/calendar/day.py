"""Day entity — port of LYP::Entities::Calendar::Day."""

import calendar as pycal
from datetime import date, timedelta
from typing import TYPE_CHECKING

from parch import InternalError

if TYPE_CHECKING:
    from parch.calendar.month import Month
    from parch.calendar.quarter import Quarter
    from parch.calendar.week import Week

WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

_WEEKDAY_INDEX = {name: i for i, name in enumerate(WEEKDAYS)}
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


def normalize_weekday(value: str) -> str:
    name = str(value).strip().lower()
    if name not in _WEEKDAY_INDEX:
        raise ValueError(f"Bad weekday {value!r}, allowed values are {list(WEEKDAYS)}")
    return name


def add_months(d: date, months: int) -> date:
    """ActiveSupport-style month arithmetic (clamp to last day of target month)."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    last = pycal.monthrange(year, month)[1]
    return date(year, month, min(d.day, last))


class Day:
    def __init__(self, weekday_start: str, day: date) -> None:
        if type(day) is not date:
            raise TypeError("day must be datetime.date")
        self.weekday_start = normalize_weekday(weekday_start)
        self.day = day

    @property
    def year(self) -> int:
        return self.day.year

    def strftime(self, fmt: str) -> str:
        # Ruby %e is space-padded day-of-month; Python's %e is not portable.
        if "%e" in fmt:
            fmt = fmt.replace("%e", f"{self.day.day:2d}")
        if "%k" in fmt:
            # not used on Day, but keep for completeness
            pass
        return self.day.strftime(fmt)

    @property
    def id(self) -> str:
        return self.day.strftime("%Y-%m-%d")

    def beginning_of_month(self) -> Day:
        return Day(weekday_start=self.weekday_start, day=self.day.replace(day=1))

    def end_of_month(self) -> Day:
        last = pycal.monthrange(self.day.year, self.day.month)[1]
        return Day(weekday_start=self.weekday_start, day=self.day.replace(day=last))

    def next_month(self) -> Day:
        return Day(weekday_start=self.weekday_start, day=add_months(self.day, 1))

    def month(self) -> Month:
        from parch.calendar.month import Month

        return Month(weekday_start=self.weekday_start, day=self)

    def quarter(self) -> Quarter:
        from parch.calendar.quarter import Quarter

        return Quarter(weekday_start=self.weekday_start, day=self)

    def week(self) -> Week:
        from parch.calendar.week import Week

        return Week(weekday_start=self.weekday_start, day=self.beginning_of_week())

    @property
    def quarter_number(self) -> int:
        return (self.day.month - 1) // 3 + 1

    def next_quarter(self) -> Day:
        return Day(weekday_start=self.weekday_start, day=add_months(self.day, 3))

    def beginning_of_week(self) -> Day:
        start = _WEEKDAY_INDEX[self.weekday_start]
        delta = (self.day.weekday() - start) % 7
        return Day(weekday_start=self.weekday_start, day=self.day - timedelta(days=delta))

    def end_of_week(self) -> Day:
        return self.beginning_of_week() + 6

    @property
    def month_day(self) -> int:
        return self.day.day

    @property
    def weekday_name(self) -> str:
        return WEEKDAYS[self.day.weekday()]

    def succ(self) -> Day:
        return Day(weekday_start=self.weekday_start, day=self.day + timedelta(days=1))

    def beginning_of_quarter(self) -> Day:
        start_month = (self.quarter_number - 1) * 3 + 1
        return Day(weekday_start=self.weekday_start, day=date(self.day.year, start_month, 1))

    def __add__(self, other: object) -> Day:
        if not isinstance(other, int):
            return NotImplemented
        return Day(weekday_start=self.weekday_start, day=self.day + timedelta(days=other))

    def __radd__(self, other: object) -> Day:
        return self.__add__(other)

    def _require_same(self, other: object, kind: str) -> Day:
        if not isinstance(other, Day):
            raise TypeError(f"must be {kind}")
        if other.weekday_start != self.weekday_start:
            raise ValueError("weekday start must match")
        return other

    def __lt__(self, other: object) -> bool:
        other_day = self._require_same(other, "Day")
        return self.day < other_day.day

    def __le__(self, other: object) -> bool:
        other_day = self._require_same(other, "Day")
        return self.day <= other_day.day

    def __gt__(self, other: object) -> bool:
        other_day = self._require_same(other, "Day")
        return self.day > other_day.day

    def __ge__(self, other: object) -> bool:
        other_day = self._require_same(other, "Day")
        return self.day >= other_day.day

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Day):
            return False
        return self.weekday_start == other.weekday_start and self.day == other.day

    def __hash__(self) -> int:
        return hash((self.weekday_start, self.day))

    def __repr__(self) -> str:
        return f"Day({self.day} wd={self.weekday_start})"

    def __str__(self) -> str:
        return f"{self.day} (wd: {self.weekday_start}, {self.weekday_name})"
