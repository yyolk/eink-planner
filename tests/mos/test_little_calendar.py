from parch.i18n import I18n
from parch.mos.components.little_calendar import LittleCalendar
from parch.mos.manifest import Manifest
from tests.helpers import make_day, make_month

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
        "months": {"full": {"february": "February", "january": "January"}},
    }
}


def _i18n() -> I18n:
    return I18n(TRANSLATIONS, locale="en")


def test_february_2021_monday_start_no_padding():
    component = LittleCalendar(
        i18n=_i18n(),
        manifest=Manifest(),
        week_placement="left",
        month=make_month("2021-02"),
        inset="5pt",
    )
    typst = component.generate()
    assert "rows: 1fr" in typst
    assert "columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr)" in typst
    assert "if x == 1" in typst
    assert "[W], [M], [T], [W], [T], [F], [S], [S]" in typst
    assert "[5], [1], [2], [3], [4], [5], [6], [7]" in typst
    assert "[8], [22], [23], [24], [25], [26], [27], [28]" in typst


def test_january_2026_nil_padded_outside_days():
    component = LittleCalendar(
        i18n=_i18n(),
        manifest=Manifest(),
        week_placement="left",
        month=make_month("2026-01"),
        inset="5pt",
    )
    typst = component.generate()
    assert "[1], [], [], [], [1], [2], [3], [4]" in typst
    assert "[5], [26], [27], [28], [29], [30], [31], []" in typst


def test_links_and_highlight():
    manifest = Manifest()
    manifest.register_source("2021-02-01")
    manifest.register_source("2021W05")
    component = LittleCalendar(
        i18n=_i18n(),
        manifest=manifest,
        week_placement="left",
        month=make_month("2021-02"),
        day=make_day("2021-02-15"),
        inset="5pt",
    )
    typst = component.generate()
    assert "padded_link(<2021W05>)[5]" in typst
    assert "padded_link(<2021-02-01>)[1]" in typst
    assert "grid.cell(fill: black, text(white, [15]))" in typst


def test_week_placement_right_and_none():
    right = LittleCalendar(
        i18n=_i18n(),
        manifest=Manifest(),
        week_placement="right",
        month=make_month("2021-02"),
        inset="5pt",
    ).generate()
    assert "if x == 7" in right
    assert "[M], [T], [W], [T], [F], [S], [S], [W]" in right

    none = LittleCalendar(
        i18n=_i18n(),
        manifest=Manifest(),
        week_placement="none",
        month=make_month("2021-02"),
        inset="5pt",
    ).generate()
    assert "stroke: none" in none
    assert "columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr)" in none
    assert "[M], [T], [W], [T], [F], [S], [S]" in none


def test_structural_strokes_are_black():
    named = LittleCalendar(
        i18n=_i18n(),
        manifest=Manifest(),
        week_placement="left",
        month=make_month("2021-02"),
        inset="5pt",
        show_month_name=True,
    ).generate()
    assert "grid.hline(stroke: regular_stroke + black)" in named
    assert "left: regular_stroke + black" in named
    assert named.count("grid.hline(stroke: regular_stroke + black)") == 2
    assert "grid.hline(stroke: regular_stroke)," not in named.replace("regular_stroke + black", "")


def test_hides_week_letter():
    typst = LittleCalendar(
        i18n=_i18n(),
        manifest=Manifest(),
        week_placement="left",
        month=make_month("2021-02"),
        inset="5pt",
        show_week_letter=False,
    ).generate()
    assert "[], [M], [T], [W], [T], [F], [S], [S]" in typst
    assert "[W], [M], [T], [W], [T], [F], [S], [S]" not in typst
