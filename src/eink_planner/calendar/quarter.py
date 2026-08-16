"""Quarter entity — port of LYP::Entities::Calendar::Quarter."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eink_planner.calendar.day import Day
    from eink_planner.calendar.month import Month


class Quarter:
    def __init__(self, weekday_start: str, day: Day) -> None:
        self.weekday_start = weekday_start
        self.day = day.beginning_of_quarter()

    @property
    def id(self) -> str:
        return f"quarter-{self.day.year}-{self.number}"

    @property
    def number(self) -> int:
        return self.day.quarter_number

    def months(self) -> list[Month]:
        from eink_planner.calendar.month import Month

        first = Month(weekday_start=self.weekday_start, day=self.day)
        second = Month(weekday_start=self.weekday_start, day=self.day.next_month())
        third = Month(weekday_start=self.weekday_start, day=self.day.next_month().next_month())
        return [first, second, third]

    def succ(self) -> Quarter:
        return Quarter(weekday_start=self.weekday_start, day=self.day.next_quarter())

    def _require_same(self, other: object) -> Quarter:
        if not isinstance(other, Quarter):
            raise TypeError("must be Quarter")
        if other.weekday_start != self.weekday_start:
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
        if not isinstance(other, Quarter):
            return False
        return self.weekday_start == other.weekday_start and self.day == other.day

    def __hash__(self) -> int:
        return hash((self.weekday_start, self.day))

    def __repr__(self) -> str:
        return f"Quarter({self.id} wd={self.weekday_start})"

    def __str__(self) -> str:
        return f"Q{self.number} (wd: {self.weekday_start})"
