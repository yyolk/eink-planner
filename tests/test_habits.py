"""Habits index + per-month tracker grids."""

from __future__ import annotations

from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.config import load
from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.sections.habits import Habits, _habit_header, is_current_index_month
from eink_planner.services.generate import Generate
from eink_planner.toml_config import parse_toml
from tests.test_toml_omit_sections import _LABEL_DEF, _PADDED_LINK, compile_pdf
from tests.toml_fixtures import _minimal, short_january

REPO = Path(__file__).resolve().parents[1]

def _habit_header_src(name: str) -> str:
    return _habit_header(name)

NOMAD = REPO / "configs/supernote-nomad.toml"
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


def _generate(dto) -> str:
    return Generate(i18n=I18n.load_default(REPO, "en")).generate(dto)


def _habits(dto) -> Habits:
    params = {}
    for section in dto["planner"]["sections"]:
        if section.get("class") == "habits" or section.get("name") == "habits":
            params = dict(section.get("params") or {})
            break
    return Habits(
        section_name="habits",
        i18n=I18n.load_default(REPO, "en"),
        configurator=Configurator(dto),
        habit_columns=params.get("habit_columns", Habits.DEFAULT_COLUMNS),
        names=params.get("names"),
    )


def test_listed_without_table_defaults_columns_and_pages():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="default-habits.toml")
    section = dto["planner"]["sections"][0]
    assert section["name"] == "habits"
    assert section["class"] == "habits"
    assert section["params"]["habit_columns"] == 6
    assert section["params"]["names"] == []
    habits = _habits(dto)
    assert habits.habit_columns == Habits.DEFAULT_COLUMNS == 6
    assert habits.names == []
    typst = _generate(dto)
    assert "<habits>" in typst
    for name in MONTHS:
        assert f"<habits-{name}>" in typst
    assert typst.count("#pagebreak()") == 12  # 1 index + 12 months - 1


def test_short_january_is_one_index_and_one_month():
    dto = parse_toml(
        _minimal(enable=["habits"], sections="[section.habits]\nhabit_columns = 12\n"),
        source="short.toml",
    )
    typst = _generate(short_january(dto))
    assert "<habits>" in typst
    assert "<habits-january>" in typst
    for name in MONTHS[1:]:
        assert f"<habits-{name}>" not in typst
    assert typst.count("#pagebreak()") == 1


def test_index_year_links_to_annual_and_month_links_back_to_index():
    dto = parse_toml(
        _minimal(
            enable=["annual", "habits"],
            sections="""[section.annual]
show_month_name = true
""",
        ),
        source="links.toml",
    )
    typst = _generate(dto)
    assert "padded_link(<annual>)" in typst
    pages = typst.split("#pagebreak()")
    index = next(page for page in pages if "<habits>" in page and "rotate(" not in page)
    assert "padded_link(<annual>)" in index
    month = next(page for page in pages if "January<habits-january>" in page and "rotate(" in page)
    assert "padded_link(<habits>)" in month
    labels = set(_LABEL_DEF.findall(typst))
    links = set(_PADDED_LINK.findall(typst))
    assert {"habits", "habits-january", "annual"} <= labels
    assert {"habits", "habits-january", "annual"} <= links


def test_year_is_plain_when_annual_omitted():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="no-annual.toml")
    typst = _generate(dto)
    assert "padded_link(<annual>)" not in typst
    assert "2026" in typst
    assert "<habits>" in typst


def test_mos_month_cells_on_habit_page_target_habit_ids():
    dto = parse_toml(
        _minimal(
            enable=["annual", "monthly", "habits"],
            sections="""[section.annual]
show_month_name = true

[section.monthly]
week_placement = "left"
week_label_rotation = "90deg"
daily_cell_height = "16mm"
""",
        ),
        source="mos-retarget.toml",
    )
    typst = _generate(dto)
    pages = typst.split("#pagebreak()")
    habit_jan = next(page for page in pages if "January<habits-january>" in page and "rotate(" in page)
    assert "padded_link(<habits-january>)" in habit_jan
    assert "padded_link(<habits-february>)" in habit_jan
    assert "padded_link(<month-2026-01-01>)" not in habit_jan
    # MOS month cells must not use calendar month.id as the only target
    assert habit_jan.count("padded_link(<habits-january>)") >= 1
    cal_jan = next(
        page
        for page in pages
        if "<month-2026-01-01>" in page and "rotate(" in page and "<habits-january>" not in page
    )
    assert "padded_link(<month-2026-02-01>)" in cal_jan
    assert "padded_link(<habits-february>)" not in cal_jan
    assert "Q1" in cal_jan
    assert "columns: (1fr, 3fr)" in cal_jan or "columns: (3fr, 1fr)" in cal_jan


def test_habit_month_mos_is_months_only():
    """Habits-only generate: month MOS is months, no quarters, no heading toggle."""
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="months-only.toml")
    typst = _generate(dto)
    pages = typst.split("#pagebreak()")
    habit_jan = next(page for page in pages if "January<habits-january>" in page and "rotate(" in page)
    for name in MONTHS:
        assert f"padded_link(<habits-{name}>)" in habit_jan
    assert "Q1" not in habit_jan
    assert "Q2" not in habit_jan
    assert "Q3" not in habit_jan
    assert "Q4" not in habit_jan
    assert "columns: (1fr, 3fr)" not in habit_jan
    assert "columns: (3fr, 1fr)" not in habit_jan
    assert ", [Calendar])" not in habit_jan
    assert ", [Habits])" not in habit_jan


def test_habit_month_has_no_heading_toggle():
    dto = parse_toml(
        _minimal(
            enable=["monthly", "habits"],
            sections="""[section.monthly]
week_placement = "left"
week_label_rotation = "90deg"
daily_cell_height = "16mm"
""",
        ),
        source="toggle.toml",
    )
    typst = _generate(dto)
    pages = typst.split("#pagebreak()")
    habit_jan = next(page for page in pages if "January<habits-january>" in page and "rotate(" in page)
    assert "padded_link(<month-2026-01-01>, [Calendar])" not in habit_jan
    assert "grid.cell(fill: black, text(white)[#padded_link(<habits-january>, [Habits])])" not in habit_jan


def test_grid_uses_stroke_boxes_writein_slash_and_friday_rule():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="grid.toml")
    typst = _generate(dto)
    assert "grid.cell(stroke: regular_stroke, [])" in typst
    assert "line(start: (0%, 100%), end: (100%, 0%), stroke: regular_stroke)" in typst
    assert "luma(140)" not in typst
    assert "luma(180)" not in typst
    assert "grid.hline(y:" in typst
    assert "grid.cell(stroke: (rest: regular_stroke, bottom: thick_stroke)" not in typst
    assert 'text(weight: "bold")' not in typst
    assert "columns: (auto, 0.8mm" not in typst
    assert "Mon 1" in typst
    assert "Sat" in typst
    assert "Sun" in typst


def test_day_cells_link_when_daily_exists():
    dto = parse_toml(
        _minimal(
            enable=["daily", "habits"],
            sections="""[section.daily]
columns = ["3fr", "5fr"]
item_spacing = "4mm"

[section.daily.left.schedule]
hour_from = 8
hour_to = 20

[section.daily.right.priorities]
count = 1
""",
        ),
        source="daily-links.toml",
    )
    typst = _generate(short_january(dto))
    pages = typst.split("#pagebreak()")
    habit_jan = next(page for page in pages if "January<habits-january>" in page and "rotate(" in page)
    assert "padded_link(<2026-01-01>)" in habit_jan
    assert "padded_link(<2026-01-14>)" in habit_jan


def test_habit_columns_is_configurable():
    dto = parse_toml(
        _minimal(enable=["habits"], sections="[section.habits]\nhabit_columns = 8\n"),
        source="cols-8.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["habit_columns"] == 8
    habits = _habits(dto)
    assert habits.habit_columns == 8
    typst = _generate(short_january(dto))
    assert typst.count(_BOX) == _JAN_DAYS * 8
    assert _BOX_FRIDAY not in typst


def test_unknown_key_on_section_habits_raises():
    with pytest.raises(ConfigError, match="unknown key: section.habits.foo"):
        parse_toml(
            _minimal(enable=["habits"], sections="[section.habits]\nfoo = 1\n"),
            source="foo.toml",
        )


def test_habit_columns_bool_and_float_rejected():
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(enable=["habits"], sections="[section.habits]\nhabit_columns = true\n"),
            source="bool.toml",
        )
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(enable=["habits"], sections="[section.habits]\nhabit_columns = 12.5\n"),
            source="float.toml",
        )


def test_index_is_raw_typst_month_pages_use_mos():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="chrome.toml")
    typst = _generate(short_january(dto))
    pages = typst.split("#pagebreak()")
    index = next(page for page in pages if "<habits>" in page and "rotate(" not in page)
    month = next(page for page in pages if "January<habits-january>" in page and "rotate(" in page)
    assert "rotate(" in month
    assert "JAN" in index
    assert "→" not in index
    assert "columns: (auto, 1fr)" in index


def test_nomad_full_year_is_thirteen_pages_of_habits():
    dto = load(NOMAD)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-1] == "habits"
    assert dto["planner"]["sections"][-1]["params"]["habit_columns"] == 6
    assert dto["planner"]["sections"][-1]["params"]["names"] == []
    typst = _generate(dto)
    assert "<habits>" in typst
    for name in MONTHS:
        assert f"<habits-{name}>" in typst


def test_tiny_annual_habits_compiles(tmp_path):
    dto = parse_toml(
        _minimal(
            enable=["annual", "habits"],
            sections="""[section.annual]
show_month_name = true
""",
        ),
        source="tiny-habits.toml",
    )
    typst = _generate(dto)
    pdf, stderr = compile_pdf(typst, tmp_path / "tiny-habits")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_short_january_nomad_compiles(tmp_path):
    dto = short_january(load(NOMAD))
    typst = _generate(dto)
    assert "<habits>" in typst
    assert "<habits-january>" in typst
    assert "<habits-february>" not in typst
    pdf, stderr = compile_pdf(typst, tmp_path / "nomad-habits")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr

_HEADER_LINE = "line(start: (0%, 100%), end: (100%, 0%), stroke: regular_stroke)"
_NAMED_MARK = "align(center + horizon, text["
_BOX = "grid.cell(stroke: regular_stroke, [])"
_BOX_FRIDAY = "grid.cell(stroke: (rest: regular_stroke, bottom: thick_stroke), [])"
_JAN_DAYS = 31
_JAN_FRIDAYS = 5


def test_default_names_are_empty_and_headers_are_line_only():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="no-names.toml")
    assert dto["planner"]["sections"][0]["params"]["names"] == []
    habits = _habits(dto)
    assert habits.names == []
    typst = _generate(short_january(dto))
    assert _NAMED_MARK not in typst
    assert typst.count(_HEADER_LINE) == 6
    assert typst.count(_BOX) == _JAN_DAYS * 6
    assert _BOX_FRIDAY not in typst


def test_two_names_typeset_and_pad_to_six_columns():
    dto = parse_toml(
        _minimal(
            enable=["habits"],
            sections="[section.habits]\nnames = [\"Sleep\", \"Move\"]\n",
        ),
        source="two-names.toml",
    )
    params = dto["planner"]["sections"][0]["params"]
    assert params["habit_columns"] == 6
    assert params["names"] == ["Sleep", "Move"]
    habits = _habits(dto)
    assert habits.names == ["Sleep", "Move"]
    typst = _generate(short_january(dto))
    assert "Sleep" in typst
    assert "Move" in typst
    assert typst.count(_NAMED_MARK) == 2
    assert typst.count(_HEADER_LINE) == 4
    assert typst.count(_BOX) == _JAN_DAYS * 6
    assert _BOX_FRIDAY not in typst
    assert "rotate(" not in _habit_header_src("Sleep")
    assert _HEADER_LINE not in _habit_header_src("Sleep")
    assert _HEADER_LINE in _habit_header_src("")


def test_more_names_than_columns_is_config_error():
    with pytest.raises(ConfigError, match="names has 3 entries but habit_columns is 2"):
        parse_toml(
            _minimal(
                enable=["habits"],
                sections="[section.habits]\nhabit_columns = 2\nnames = [\"A\", \"B\", \"C\"]\n",
            ),
            source="too-many.toml",
        )


def test_empty_string_name_stays_line_only():
    dto = parse_toml(
        _minimal(
            enable=["habits"],
            sections="[section.habits]\nnames = [\"Sleep\", \"\", \"Water\"]\n",
        ),
        source="blank-slot.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["names"] == ["Sleep", "", "Water"]
    typst = _generate(short_january(dto))
    assert "Sleep" in typst
    assert "Water" in typst
    assert typst.count(_NAMED_MARK) == 2
    assert typst.count(_HEADER_LINE) == 4
    # the blank slot must not emit an empty typeset word
    assert "align(center + horizon, text[])" not in typst


def test_same_names_on_every_month_page():
    dto = parse_toml(
        _minimal(
            enable=["habits"],
            sections="[section.habits]\nnames = [\"Sleep\", \"Move\"]\n",
        ),
        source="every-month.toml",
    )
    typst = _generate(dto)
    pages = typst.split("#pagebreak()")
    named = [page for page in pages if "align(center + horizon, text[Sleep])" in page]
    assert len(named) == 12
    for page in named:
        assert "align(center + horizon, text[Move])" in page
        assert page.count(_HEADER_LINE) == 4
        assert "rotate(" in page  # MOS chrome, not the habit name
        sleep_cell = page[page.index("align(center + horizon, text[Sleep])") :]
        sleep_cell = sleep_cell[: sleep_cell.index("grid.cell(stroke: regular_stroke, [])")]
        assert "rotate(" not in sleep_cell


def test_names_escape_typst_specials():
    dto = parse_toml(
        _minimal(
            enable=["habits"],
            sections="""[section.habits]
names = ["Caffeine#1", "A[B]", "C\\\\D"]
""",
        ),
        source="escape.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["names"] == ["Caffeine#1", "A[B]", r"C\D"]
    typst = _generate(short_january(dto))
    assert r"Caffeine\#1" in typst
    assert r"A\[B\]" in typst
    assert r"C\\D" in typst
    assert "align(center + horizon, text[Caffeine#1])" not in typst


def test_named_headers_compile(tmp_path):
    dto = parse_toml(
        _minimal(
            enable=["habits"],
            sections="[section.habits]\nnames = [\"Sleep\", \"Move\", \"Water\"]\n",
        ),
        source="named-compile.toml",
    )
    typst = _generate(short_january(dto))
    pdf, stderr = compile_pdf(typst, tmp_path / "named-habits")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


_RIGHT_LAYOUT = """[layout]
name = "mos"
side_menu = "right"
side_menu_width = "10mm"
reverse_months_quarters = true
menu_rotate = "270deg"
column_gutter = "1.5mm"
row_gutter = "1.5mm"
"""


def _mos_page(typst: str, *needles: str, exclude: str | None = None) -> str:
    for page in typst.split("#pagebreak()"):
        if all(needle in page for needle in needles) and (
            exclude is None or exclude not in page
        ):
            return page
    raise AssertionError(f"no page matching {needles!r}")


def test_habit_month_follows_side_menu_dates_stay_left():
    """MOS-right moves the months strip; habit dates stay left of the grid."""
    right = parse_toml(
        _minimal(enable=["habits"], layout=_RIGHT_LAYOUT, sections=""),
        source="habits-mos-right.toml",
    )
    right_typst = _generate(right)
    right_jan = _mos_page(right_typst, "January<habits-january>", "rotate(")
    assert "columns: (1fr, 10mm)" in right_jan
    assert "columns: (10mm, 1fr)" not in right_jan
    assert "columns: (8mm, 1fr)" not in right_jan
    right_grid = right_jan[right_jan.index("columns: (auto, 1fr") :]
    assert "Thu 1" in right_grid
    assert "Mon 5" in right_grid
    assert right_grid.index("Thu 1") < right_grid.index(
        "grid.cell(stroke: regular_stroke, [])"
    )
    right_june = _mos_page(right_typst, "June<habits-june>", "rotate(")
    june_grid = right_june[right_june.index("columns: (auto, 1fr") :]
    assert "Mon 1" in june_grid
    assert june_grid.index("Mon 1") < june_grid.index(
        "grid.cell(stroke: regular_stroke, [])"
    )

    left = parse_toml(_minimal(enable=["habits"], sections=""), source="habits-mos-left.toml")
    left_jan = _mos_page(_generate(left), "January<habits-january>", "rotate(")
    assert "columns: (8mm, 1fr)" in left_jan
    assert "columns: (1fr, 8mm)" not in left_jan
    left_grid = left_jan[left_jan.index("columns: (auto, 1fr") :]
    assert "Thu 1" in left_grid
    assert left_grid.index("Thu 1") < left_grid.index(
        "grid.cell(stroke: regular_stroke, [])"
    )

    monthly = """[section.monthly]
week_placement = "left"
week_label_rotation = "90deg"
daily_cell_height = "16mm"
"""
    both_right = parse_toml(
        _minimal(enable=["monthly", "habits"], layout=_RIGHT_LAYOUT, sections=monthly),
        source="monthly-habits-right.toml",
    )
    monthly_only = parse_toml(
        _minimal(enable=["monthly"], layout=_RIGHT_LAYOUT, sections=monthly),
        source="monthly-right.toml",
    )
    cal_both = _mos_page(
        _generate(both_right),
        "<month-2026-01-01>",
        "rotate(",
        exclude="<habits-january>",
    )
    cal_only = _mos_page(_generate(monthly_only), "<month-2026-01-01>", "rotate(")
    assert "columns: (1fr, 10mm)" in cal_both
    assert "columns: (10mm, 1fr)" not in cal_both
    assert "Q1" in cal_both
    assert "padded_link(<month-2026-02-01>)" in cal_both
    assert "padded_link(<habits-february>)" not in cal_both
    assert "columns: (auto, 1fr, 1fr" not in cal_both
    assert "columns: (1fr, 10mm)" in cal_only
    assert "Q1" in cal_only
    assert "padded_link(<month-2026-02-01>)" in cal_only


def test_named_header_is_upright_blank_keeps_slash():
    named = _habit_header("Sleep")
    blank = _habit_header("")
    assert "Sleep" in named
    assert "rotate(" not in named
    assert "atan" not in named
    assert _HEADER_LINE not in named
    assert "align(center + horizon, text[Sleep])" in named
    assert _HEADER_LINE in blank
    assert "Sleep" not in blank


def test_index_inverts_current_month_in_planner_year():
    from datetime import date

    from eink_planner.calendar.day import Day
    from eink_planner.calendar.month import Month

    aug = Month(weekday_start="monday", day=Day("monday", date(2026, 8, 1)))
    jan = Month(weekday_start="monday", day=Day("monday", date(2026, 1, 1)))
    assert is_current_index_month(aug, today=date(2026, 8, 25))
    assert not is_current_index_month(jan, today=date(2026, 8, 25))
    assert not is_current_index_month(aug, today=date(2025, 8, 25))
    assert is_current_index_month(aug) is (date.today().year == 2026 and date.today().month == 8)

    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="invert.toml")
    typst = _generate(dto)
    index = next(
        page for page in typst.split("#pagebreak()") if "<habits>" in page and "rotate(" not in page
    )
    assert "→" not in index
    if date.today() == date(2026, 8, 25) or (
        date.today().year == 2026 and date.today().month == 8
    ):
        assert "grid.cell(fill: black, text(white)[#padded_link(<habits-august>)[AUG]])" in index
        assert "grid.cell(fill: black, text(white)[#padded_link(<habits-january>)[JAN]])" not in index


def test_index_inverts_none_when_today_is_outside_planner_year():
    from datetime import date

    dto = parse_toml(
        _minimal(
            enable=["habits"],
            calendar="""[calendar]
year = 2025
week_starts = "Monday"
""",
            sections="",
        ),
        source="invert-2025.toml",
    )
    typst = _generate(dto)
    index = next(
        page for page in typst.split("#pagebreak()") if "<habits>" in page and "rotate(" not in page
    )
    if date.today().year != 2025:
        assert "grid.cell(fill: black" not in index


def test_january_has_friday_rules_and_no_weekend_bar():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="friday.toml")
    typst = _generate(dto)
    pages = typst.split("#pagebreak()")
    january = next(
        page for page in pages if "January<habits-january>" in page and "rotate(" in page
    )
    december = next(
        page for page in pages if "December<habits-december>" in page and "rotate(" in page
    )
    assert january.count(_BOX) == _JAN_DAYS * 6
    assert december.count(_BOX) == 31 * 6
    assert january.count("grid.hline(y:") == _JAN_FRIDAYS
    assert december.count("grid.hline(y:") == 4
    for y in (3, 10, 17, 24, 31):
        assert f"grid.hline(y: {y}, stroke: thick_stroke)" in january
    for y in (5, 12, 19, 26):
        assert f"grid.hline(y: {y}, stroke: thick_stroke)" in december
    for page in (january, december):
        assert _BOX_FRIDAY not in page
        assert "bottom: thick_stroke" not in page
        assert 'text(weight: "bold")' not in page
        assert page.count("align(horizon + right,") == 31
        last_box = page.rfind(_BOX)
        first_hline = page.find("grid.hline(y:")
        assert last_box != -1 and first_hline != -1 and last_box < first_hline
    for day in (2, 9, 16, 23, 30):
        assert f"align(horizon + right, [#[Fri {day}]])" in january
        assert (
            f"grid.cell(stroke: (rest: regular_stroke, bottom: thick_stroke), "
            f"align(horizon + right, [#[Fri {day}]]))"
        ) not in january
    for day in (4, 11, 18, 25):
        assert f"align(horizon + right, [#[Fri {day}]])" in december
        assert (
            f"grid.cell(stroke: (rest: regular_stroke, bottom: thick_stroke), "
            f"align(horizon + right, [#[Fri {day}]]))"
        ) not in december
    assert "align(horizon + right, [#[Sat 3]])" in january
    assert "align(horizon + right, [#[Sun 4]])" in january
    assert "align(horizon + right, [#[Mon 5]])" in january
    assert "columns: (auto, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr)" in january
    assert "0.8mm" not in january
    assert "luma(140)" not in january
    assert "luma(180)" not in january
