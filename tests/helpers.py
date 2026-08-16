from __future__ import annotations

from datetime import date

import pytest

from eink_planner.calendar.day import Day
from eink_planner.calendar.month import Month
from eink_planner.calendar.quarter import Quarter
from eink_planner.calendar.week import Week
from eink_planner.config import StrictDict
from eink_planner.mos.configurator import Configurator


def make_day(date_str: str, weekday_start: str = "monday") -> Day:
    return Day(day=date.fromisoformat(date_str), weekday_start=weekday_start)


def make_week(date_str: str, weekday_start: str = "monday") -> Week:
    return Week(weekday_start=weekday_start, day=make_day(date_str, weekday_start))


def make_month(yyyy_mm: str, weekday_start: str = "monday") -> Month:
    return Month(weekday_start=weekday_start, day=make_day(f"{yyyy_mm}-01", weekday_start))


def make_quarter(date_str: str, weekday_start: str = "monday") -> Quarter:
    return Quarter(weekday_start=weekday_start, day=make_day(date_str, weekday_start))


def make_configurator(
    start_date: str = "2026-01-01",
    end_date: str = "2026-12-31",
    weekday_start: str = "Monday",
    debug: bool = False,
) -> Configurator:
    return Configurator(
        StrictDict(
            {
                "debug": debug,
                "planner": {
                    "params": {
                        "start_date": start_date,
                        "end_date": end_date,
                        "weekday_start": weekday_start,
                    }
                },
            }
        )
    )


@pytest.fixture
def helpers():
    return {
        "make_day": make_day,
        "make_week": make_week,
        "make_month": make_month,
        "make_quarter": make_quarter,
        "make_configurator": make_configurator,
    }
