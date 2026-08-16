from datetime import date

import pytest

from tests.helpers import make_day, make_month, make_quarter, make_week


def test_initialize():
    day = make_day("2026-03-15")
    assert day.day == date(2026, 3, 15)
    assert day.weekday_start == "monday"


def test_id_formats_iso():
    assert make_day("2026-02-03").id == "2026-02-03"


def test_beginning_of_month():
    assert make_day("2026-03-15").beginning_of_month() == make_day("2026-03-01")
    assert make_day("2026-03-01").beginning_of_month() == make_day("2026-03-01")


def test_end_of_month():
    assert make_day("2026-03-15").end_of_month() == make_day("2026-03-31")
    assert make_day("2026-03-31").end_of_month() == make_day("2026-03-31")


def test_next_month_clamps_end_of_month():
    assert make_day("2026-03-15").next_month() == make_day("2026-04-15")
    assert make_day("2026-03-31").next_month() == make_day("2026-04-30")


def test_month_and_quarter_and_week():
    assert make_day("2026-03-15").month() == make_month("2026-03")
    assert make_day("2026-03-15").quarter() == make_quarter("2026-03-01")
    assert make_day("2026-03-15").week() == make_week("2026-03-15")


def test_quarter_number():
    assert make_day("2026-03-15").quarter_number == 1
    assert make_day("2026-04-15").quarter_number == 2


def test_beginning_of_quarter():
    assert make_day("2026-03-15").beginning_of_quarter() == make_day("2026-01-01")
    assert make_day("2026-04-15").beginning_of_quarter() == make_day("2026-04-01")


def test_next_quarter_clamps():
    assert make_day("2026-03-31").next_quarter() == make_day("2026-06-30")


def test_beginning_of_week():
    assert make_day("2026-03-15").beginning_of_week() == make_day("2026-03-09")
    assert make_day("2026-03-15", weekday_start="sunday").beginning_of_week() == make_day(
        "2026-03-15", weekday_start="sunday"
    )


def test_end_of_week():
    assert make_day("2026-03-15").end_of_week() == make_day("2026-03-15")
    assert make_day("2026-03-15", weekday_start="sunday").end_of_week() == make_day(
        "2026-03-21", weekday_start="sunday"
    )


def test_month_day_and_weekday_name():
    assert make_day("2026-03-15").month_day == 15
    assert make_day("2026-03-15").weekday_name == "sunday"


def test_add_days():
    assert make_day("2026-03-29") + 3 == make_day("2026-04-01")


def test_compare_requires_matching_weekday_start():
    with pytest.raises(ValueError, match="weekday start must match"):
        _ = make_day("2026-03-15") < make_day("2026-03-16", weekday_start="sunday")
