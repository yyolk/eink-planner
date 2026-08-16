from tests.helpers import make_day, make_month, make_quarter, make_week


def test_monday_start():
    week = make_week("2026-03-15", weekday_start="monday")
    assert week.day == make_day("2026-03-09", weekday_start="monday")
    assert week.weekday_start == "monday"


def test_sunday_start():
    week = make_week("2026-03-15", weekday_start="sunday")
    assert week.day == make_day("2026-03-15", weekday_start="sunday")
    assert week.weekday_start == "sunday"


def test_id_iso_week():
    assert make_week("2026-03-15").id == "2026W11"
    assert make_week("2025-12-29").id == "2026W01"
    assert make_week("2026-12-28").id == "2026W53"
    assert make_week("2027-01-03").id == "2026W53"


def test_number():
    assert make_week("2026-03-15").number == 11
    assert make_week("2025-12-29").number == 1
    assert make_week("2026-12-28").number == 53
    assert make_week("2027-01-03").number == 53


def test_days():
    assert make_week("2026-03-15").days() == [make_day("2026-03-09") + i for i in range(7)]


def test_in_months():
    assert make_week("2026-03-15").in_months() == [make_month("2026-03")]
    assert make_week("2026-03-30").in_months() == [make_month("2026-03"), make_month("2026-04")]
    assert make_week("2026-04-04").in_months() == [make_month("2026-03"), make_month("2026-04")]


def test_in_quarters():
    assert make_week("2026-03-15").in_quarters() == [make_quarter("2026-03-01")]
    assert make_week("2026-03-31").in_quarters() == [
        make_quarter("2026-03-01"),
        make_quarter("2026-04-01"),
    ]
    assert make_week("2026-04-03").in_quarters() == [
        make_quarter("2026-03-01"),
        make_quarter("2026-04-01"),
    ]
