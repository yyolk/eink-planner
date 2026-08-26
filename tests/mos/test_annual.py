from eink_planner.i18n import I18n
from eink_planner.mos.manifest import Manifest
from eink_planner.mos.sections.annual import Annual
from tests.helpers import make_configurator

MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)

TRANSLATIONS = {
    "en": {
        "weekday": {
            "letter": {
                "monday": "M",
                "tuesday": "T",
                "wednesday": "W",
                "thursday": "T",
                "friday": "F",
                "saturday": "S",
                "sunday": "S",
                "week": "W",
            }
        },
        "months": {"full": {name: name.title() for name in MONTHS}},
    }
}

LITTLE = {"week_placement": "left", "inset": "5pt", "show_month_name": True}


def _i18n() -> I18n:
    return I18n(TRANSLATIONS, locale="en")


def _annual(start_date: str = "2026-01-01", end_date: str = "2026-12-31") -> Annual:
    return Annual(
        section_name="annual",
        i18n=_i18n(),
        configurator=make_configurator(start_date=start_date, end_date=end_date),
        little_calendar=LITTLE,
    )


def test_title_is_year_with_annual_label_not_calendar():
    pages = _annual().pages(Manifest())
    assert len(pages) == 1
    assert pages[0].title == "text(size: h1)[2026<annual>]"
    assert "Calendar" not in pages[0].title
    other = _annual(start_date="2025-01-01", end_date="2025-12-31").pages(Manifest())
    assert other[0].title == "text(size: h1)[2025<annual>]"


def test_three_by_four_grid_has_three_black_quarter_row_hlines():
    content = _annual().pages(Manifest())[0].content
    assert "columns: (1fr, 1fr, 1fr)" in content
    assert "rows: (1fr, 1fr, 1fr, 1fr)" in content
    # 12 month-name hlines + 12 weekday-heading hlines + 3 quarter-row rules
    assert content.count("grid.hline(stroke: regular_stroke + black)") == 27


def test_little_calendars_omit_week_letter():
    content = _annual().pages(Manifest())[0].content
    assert "[], [M], [T], [W], [T], [F], [S], [S]" in content
    assert "[W], [M], [T], [W], [T], [F], [S], [S]" not in content


def _after_month(content: str, name: str) -> str:
    start = content.index(f"[{name}]")
    later = []
    for month in MONTHS:
        title = month.title()
        if title == name:
            continue
        pos = content.find(f"[{title}]", start + 1)
        if pos != -1:
            later.append(pos)
    return content[start : min(later)] if later else content[start:]


def test_quarter_hlines_follow_quarters_not_every_third_item():
    content = _annual(start_date="2026-02-01", end_date="2026-12-31").pages(Manifest())[0].content
    assert "rows: (1fr, 1fr, 1fr, 1fr)" in content
    # 11 month-name hlines + 11 weekday-heading hlines + 3 quarter-row rules
    assert content.count("grid.hline(stroke: regular_stroke + black)") == 25
    quarter = "),\ngrid.hline(stroke: regular_stroke + black)"
    # Feb–Dec: Q1 ends at Mar, then Jun and Sep — not every third item (Apr/Jul/Oct).
    assert quarter in _after_month(content, "March")
    assert quarter in _after_month(content, "June")
    assert quarter in _after_month(content, "September")
    assert quarter not in _after_month(content, "April")
    assert quarter not in _after_month(content, "July")
    assert quarter not in _after_month(content, "October")
