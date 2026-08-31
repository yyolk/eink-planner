from parch.i18n import I18n
from parch.mos.components.little_calendar import WEEK_ROWS, LittleCalendar
from parch.mos.manifest import Manifest
from tests.helpers import make_day, make_month

PAD8 = "[], [], [], [], [], [], [], []"
PAD7 = "[], [], [], [], [], [], []"

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
        month=make_month("2021-02"),
        inset="5pt",
        side="left",
    )
    typst = component.generate()
    assert "month_grid(" in typst
    assert "month_grid(left," in typst
    assert "rows: 1fr" not in typst
    assert "grid.hline" not in typst
    assert "columns:" not in typst
    assert "stroke:" not in typst
    assert "[W], [M], [T], [W], [T], [F], [S], [S]" in typst
    assert "[5], [1], [2], [3], [4], [5], [6], [7]" in typst
    assert "[8], [22], [23], [24], [25], [26], [27], [28]" in typst
    assert typst.count(PAD8) == WEEK_ROWS - 4
    assert len(component._month_in_weeks()) == WEEK_ROWS
    assert not hasattr(component, "_with_week_column")


def test_january_2026_nil_padded_outside_days():
    component = LittleCalendar(
        i18n=_i18n(),
        manifest=Manifest(),
        month=make_month("2026-01"),
        inset="5pt",
        side="left",
    )
    typst = component.generate()
    assert "[1], [], [], [], [1], [2], [3], [4]" in typst
    assert "[5], [26], [27], [28], [29], [30], [31], []" in typst
    assert typst.count(PAD8) == WEEK_ROWS - 5
    assert len(component._month_in_weeks()) == WEEK_ROWS


def test_links_and_highlight():
    manifest = Manifest()
    manifest.register_source("2021-02-01")
    manifest.register_source("2021W05")
    component = LittleCalendar(
        i18n=_i18n(),
        manifest=manifest,
        month=make_month("2021-02"),
        day=make_day("2021-02-15"),
        inset="5pt",
        side="left",
    )
    typst = component.generate()
    assert "padded_link(<2021W05>)[5]" in typst
    assert "padded_link(<2021-02-01>)[1]" in typst
    assert "grid.cell(fill: black, text(white, [15]))" in typst


def test_hand_right_still_emits_week_first():
    right = LittleCalendar(
        i18n=_i18n(),
        manifest=Manifest(),
        month=make_month("2021-02"),
        inset="5pt",
        side="right",
    ).generate()
    assert "month_grid(right," in right
    assert "[W], [M], [T], [W], [T], [F], [S], [S]" in right
    assert "[M], [T], [W], [T], [F], [S], [S], [W]" not in right
    assert "columns:" not in right
    assert "stroke:" not in right
    assert "if x == 7" not in right


def test_week_placement_none_is_seven_col_without_side():
    none = LittleCalendar(
        i18n=_i18n(),
        manifest=Manifest(),
        week_placement="none",
        month=make_month("2021-02"),
        inset="5pt",
    ).generate()
    assert "month_grid(left," not in none
    assert "month_grid(right," not in none
    assert "month_grid(" not in none
    assert "stroke: none" in none
    assert "columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr)" in none
    assert "[M], [T], [W], [T], [F], [S], [S]" in none
    assert "[W], [M], [T], [W], [T], [F], [S], [S]" not in none
    assert none.count(PAD7) >= WEEK_ROWS - 4


def test_structural_strokes_are_black():
    named = LittleCalendar(
        i18n=_i18n(),
        manifest=Manifest(),
        month=make_month("2021-02"),
        inset="5pt",
        show_month_name=True,
        side="left",
    ).generate()
    assert "month_grid(" in named
    assert "month_grid(left," in named
    assert "grid.hline" not in named
    assert "colspan: 8" in named
    assert "[February]" in named
    assert "grid.hline(stroke: regular_stroke)," not in named.replace("regular_stroke + black", "")


def test_every_month_emits_six_week_rows():
    # 4-week Feb, 5-week Jan, 6-week Mar, leap Feb — same week-rows contract.
    months = ("2021-02", "2026-01", "2026-02", "2026-03", "2024-02")
    for yyyy_mm in months:
        component = LittleCalendar(
            i18n=_i18n(),
            manifest=Manifest(),
            month=make_month(yyyy_mm),
            inset="5pt",
            side="left",
        )
        weeks = component._month_in_weeks()
        assert len(weeks) == WEEK_ROWS, yyyy_mm
        typst = component.generate()
        assert "month_grid(" in typst, yyyy_mm
        assert "rows: 1fr" not in typst, yyyy_mm
        assert "grid.hline" not in typst, yyyy_mm
    march = LittleCalendar(
        i18n=_i18n(),
        manifest=Manifest(),
        month=make_month("2026-03"),
        inset="5pt",
        side="left",
    ).generate()
    assert PAD8 not in march


def test_hides_week_letter():
    typst = LittleCalendar(
        i18n=_i18n(),
        manifest=Manifest(),
        month=make_month("2021-02"),
        inset="5pt",
        show_week_letter=False,
        side="left",
    ).generate()
    assert "[], [M], [T], [W], [T], [F], [S], [S]" in typst
    assert "[W], [M], [T], [W], [T], [F], [S], [S]" not in typst
