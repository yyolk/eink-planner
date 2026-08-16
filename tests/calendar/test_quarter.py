import pytest

from tests.helpers import make_day, make_month, make_quarter


def test_initialize_snaps_to_quarter_start():
    quarter = make_quarter("2026-03-15")
    assert quarter.day == make_day("2026-01-01")
    assert quarter.weekday_start == "monday"


def test_id():
    assert make_quarter("2026-01-01").id == "quarter-2026-1"
    assert make_quarter("2026-04-01").id == "quarter-2026-2"
    assert make_quarter("2026-07-01").id == "quarter-2026-3"
    assert make_quarter("2026-10-01").id == "quarter-2026-4"


def test_number():
    assert make_quarter("2026-01-01").number == 1
    assert make_quarter("2026-04-01").number == 2
    assert make_quarter("2026-07-01").number == 3
    assert make_quarter("2026-10-01").number == 4


def test_months():
    assert make_quarter("2026-01-01").months() == [
        make_month("2026-01"),
        make_month("2026-02"),
        make_month("2026-03"),
    ]
    assert make_quarter("2026-10-01").months() == [
        make_month("2026-10"),
        make_month("2026-11"),
        make_month("2026-12"),
    ]


def test_compare():
    assert make_quarter("2026-01-01") < make_quarter("2026-04-01")
    assert make_quarter("2026-01-01") == make_quarter("2026-01-01", weekday_start="monday")
    assert make_quarter("2026-04-01") > make_quarter("2026-01-01")


def test_compare_errors():
    with pytest.raises(TypeError, match="must be Quarter"):
        _ = make_quarter("2026-01-01") < make_day("2026-01-01")
    with pytest.raises(ValueError, match="weekday start must match"):
        _ = make_quarter("2026-01-01") < make_quarter("2026-01-01", weekday_start="sunday")
