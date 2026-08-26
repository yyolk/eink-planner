"""Calendar entities (Day / Week / Month / Quarter) with Ruby-style succ ranges."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, TypeVar

from parch.calendar.day import WEEKDAYS, Day
from parch.calendar.month import Month
from parch.calendar.quarter import Quarter
from parch.calendar.week import Week
from parch.calendar.dated_note import DatedNote

T = TypeVar("T", bound="ComparableSucc")


class ComparableSucc(Protocol):
    def succ(self) -> T: ...  # type: ignore[misc]

    def __le__(self, other: object) -> bool: ...


def walk(start: T, end: T) -> Iterator[T]:
    """Inclusive range ``start..end`` using ``succ``, like Ruby."""
    current = start
    while current <= end:
        yield current
        current = current.succ()  # type: ignore[assignment]


__all__ = [
    "WEEKDAYS",
    "Day",
    "Week",
    "Month",
    "Quarter",
    "DatedNote",
    "walk",
]
