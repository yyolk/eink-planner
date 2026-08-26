"""Locale models.

TOML keys use underscores; hyphens are OK in filenames only.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from eink_planner.models.base import StrictModel


class Quarter(StrictModel):
    short: str
    long: str


class MonthNames(StrictModel):
    january: str
    february: str
    march: str
    april: str
    may: str
    june: str
    july: str
    august: str
    september: str
    october: str
    november: str
    december: str


class Months(StrictModel):
    short: MonthNames
    full: MonthNames


class WeekdayLetter(StrictModel):
    week: str
    monday: str
    tuesday: str
    wednesday: str
    thursday: str
    friday: str
    saturday: str
    sunday: str


class WeekdayFull(StrictModel):
    monday: str
    tuesday: str
    wednesday: str
    thursday: str
    friday: str
    saturday: str
    sunday: str


class Weekday(StrictModel):
    letter: WeekdayLetter
    full: WeekdayFull
    short: WeekdayFull


class Locale(StrictModel):
    language: str
    week_name: str
    schedule: str
    top_priorities: str
    monthly_notes: str
    daily_notes: str
    more_daily_notes: str
    notes: str
    projects: str
    meetings: str
    habits: str
    review: str
    topics: str
    action_items: str
    todo: str
    doing: str
    done: str
    title: str
    date: str
    quarter: Quarter
    months: Months
    weekday: Weekday


def load_locale(path: Path) -> Locale:
    with path.open("rb") as f:
        return Locale.model_validate(tomllib.load(f))
