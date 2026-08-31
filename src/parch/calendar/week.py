"""Week entity — port of LYP::Entities::Calendar::Week."""

from typing import TYPE_CHECKING

from parch import InternalError

if TYPE_CHECKING:
    from parch.calendar.day import Day
    from parch.calendar.month import Month
    from parch.calendar.quarter import Quarter


class Week:
    def __init__(self, weekday_start: str, day: Day) -> None:
        from parch.calendar.day import Day as DayCls

        if not isinstance(day, DayCls):
            raise InternalError("Week.day must be a Day")
        self.weekday_start = weekday_start
        self.day = day.beginning_of_week()

    @property
    def id(self) -> str:
        return self._iso_label()

    def _iso_label(self) -> str:
        iso = self.day.day.isocalendar()
        return f"{iso.year}W{iso.week:02d}"

    @property
    def number(self) -> int:
        return self.day.day.isocalendar().week

    def days(self) -> list[Day]:
        return [self.day + i for i in range(7)]

    def in_months(self) -> list[Month]:
        first = self.days()[0]
        last = self.days()[-1]
        months = [first.month(), last.month()]
        out: list[Month] = []
        for month in months:
            if month not in out:
                out.append(month)
        return out

    def in_quarters(self) -> list[Quarter]:
        first = self.days()[0]
        last = self.days()[-1]
        quarters = [first.quarter(), last.quarter()]
        out: list[Quarter] = []
        for quarter in quarters:
            if quarter not in out:
                out.append(quarter)
        return out

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Week):
            return False
        return self.weekday_start == other.weekday_start and self.day == other.day

    def __hash__(self) -> int:
        return hash((self.weekday_start, self.day))

    def __repr__(self) -> str:
        return f"Week({self.id} wd={self.weekday_start})"

    def __str__(self) -> str:
        return self.id
