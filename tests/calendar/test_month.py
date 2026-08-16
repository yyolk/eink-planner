import pytest

from tests.helpers import make_day, make_month, make_quarter


def test_initialize():
    month = make_month("2026-03")
    assert month.day == make_day("2026-03-01")
    assert month.weekday_start == "monday"


def test_id():
    assert make_month("2026-03").id == "month-2026-03-01"
    assert make_month("2026-12").id == "month-2026-12-01"


def test_name():
    assert make_month("2026-03").name == "march"
    assert make_month("2026-12").name == "december"


def test_quarter():
    assert make_month("2026-03").quarter() == make_quarter("2026-01-01")
    assert make_month("2026-04").quarter() == make_quarter("2026-04-01")
    assert make_month("2026-12").quarter() == make_quarter("2026-10-01")


def test_compare():
    assert (make_month("2026-03") < make_month("2026-04")) is True
    assert make_month("2026-03") == make_month("2026-03", weekday_start="monday")
    assert (make_month("2026-04") > make_month("2026-03")) is True


def test_compare_type_error():
    with pytest.raises(TypeError, match="must be Month"):
        _ = make_month("2026-03") < make_day("2026-03-01")


def test_compare_weekday_mismatch():
    with pytest.raises(ValueError, match="weekday start must match"):
        _ = make_month("2026-03") < make_month("2026-03", weekday_start="sunday")
