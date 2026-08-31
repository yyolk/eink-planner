"""Dated extra-note page — port of LYP::Entities::DatedNote."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from parch.calendar.day import Day


class DatedNote:
    def __init__(self, weekday_start: str, day: Day, page: int = 1) -> None:
        self.weekday_start = weekday_start
        self.day = day
        self.page = page

    @property
    def id(self) -> str:
        return f"daily-note-{self.day.strftime('%Y-%m-%d')}-page-{self.page}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DatedNote):
            return False
        return (
            self.weekday_start == other.weekday_start
            and self.day == other.day
            and self.page == other.page
        )

    def __hash__(self) -> int:
        return hash((self.weekday_start, self.day, self.page))

    def __repr__(self) -> str:
        return f"DatedNote({self.id})"
