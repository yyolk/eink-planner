"""Habits index + per-month tracker grids."""


import pytest

from parch import ConfigError
from parch.compose.page_data import HeadingMark
from parch.config import load
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.sections.habits import Habits, _habit_header
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.test_toml_omit_sections import _LABEL_DEF, _PADDED_LINK, compile_pdf
from tests.toml_fixtures import _minimal, short_january
from tests.helpers import base_config, load_default


def _habit_header_src(name: str) -> str:
    return _habit_header(name)

NOMAD = base_config("supernote-nomad")
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
_MARK_RULE = "contents_bars(size:"
_TRAIL_MARK = "pad(right: 3mm, padded_link(padding: 0pt, <index>"
_SEATED_TRAIL = "box(height: band, align(horizon + left, seated_"
_SEATED_TITLE = "let seated_title ="
_SEATED_MARK = "let seated_mark ="
_SEAT_RTL = "dir: rtl,\n    spacing: 1fr,"
_SEAT_LTR = "dir: ltr,\n    spacing: 1fr,"
_FOLLOW_RTL = "dir: rtl,\n    spacing: 0.5em,"
_HEADER_LINE = "line(start: (0%, 100%), end: (100%, 0%), stroke: regular_stroke)"
_NAMED_MARK = "align(center + horizon, text["
_BOX = "grid.cell(stroke: regular_stroke, [])"
_BOX_FRIDAY = "grid.cell(stroke: (rest: regular_stroke, bottom: thick_stroke), [])"
_WEEK_RULE = "grid.cell(colspan:"
_JAN_DAYS = 31
_DEFAULT_COLUMNS = 4
_RIGHT_MOS = """[mos]
side_menu = "right"
side_menu_width = "10mm"
reverse_months_quarters = true
menu_rotate = "270deg"
column_gutter = "1.5mm"
row_gutter = "1.5mm"
"""


def _generate(dto) -> str:
    return Generate(i18n=load_default()).generate(dto)


def _habits(dto) -> Habits:
    params = {}
    for section in dto["planner"]["sections"]:
        if section.get("class") == "habits" or section.get("name") == "habits":
            params = dict(section.get("params") or {})
            break
    return Habits(
        section_name="habits",
        i18n=load_default(),
        configurator=Configurator(dto),
        habit_columns=params.get("habit_columns", Habits.DEFAULT_COLUMNS),
        names=params.get("names"),
    )


def _pages(typst: str) -> list[str]:
    return typst.split("#pagebreak()")


def _index_page(typst: str) -> str:
    for page in _pages(typst):
        if "[Habits <habits>]" in page and "rotate(" not in page:
            return page
    raise AssertionError("no Habits index page")


def _month_page(typst: str, name: str = "january") -> str:
    needle = f"{name.title()}<habits-{name}>"
    for page in _pages(typst):
        if needle in page and "rotate(" in page:
            return page
    raise AssertionError(f"no Habits month page {name}")


def _habit_rows_spec(page: str) -> str:
    start = page.index("columns: (auto, 1fr")
    chunk = page[start:]
    begin = chunk.index("rows: (") + len("rows: (")
    end = chunk.index(")", begin)
    return chunk[begin:end]


def test_listed_without_table_defaults_columns_and_pages():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="default-habits.toml")
    section = dto["planner"]["sections"][0]
    assert section["name"] == "habits"
    assert section["class"] == "habits"
    assert section["params"]["habit_columns"] == 4
    assert section["params"]["names"] == []
    habits = _habits(dto)
    assert habits.habit_columns == Habits.DEFAULT_COLUMNS == 4
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


def test_index_title_is_habits_and_month_links_back():
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
    index = _index_page(typst)
    month = _month_page(typst)
    assert "padded_link(<annual>)" not in index
    assert "2026 /" not in index
    assert "text(size: h1)[/]" not in index
    assert "text(size: h1, [Habits <habits>])" in index
    assert "padded_link(<habits>)" in month
    assert "2026 /" not in month
    assert "text(size: h1)[/]" not in month
    assert "January<habits-january>" in month
    labels = set(_LABEL_DEF.findall(typst))
    links = set(_PADDED_LINK.findall(typst))
    assert {"habits", "habits-january", "annual"} <= labels
    assert {"habits", "habits-january"} <= links
    assert "annual" not in set(_PADDED_LINK.findall(index + month))


def test_header_is_habits_without_year_when_contents_off():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="no-annual.toml")
    typst = _generate(dto)
    index = _index_page(typst)
    month = _month_page(typst)
    for page in (index, month):
        assert "padded_link(<annual>)" not in page
        assert "2026 /" not in page
        assert "text(size: h1)[/]" not in page
    assert "pad(right: 3mm" not in index
    assert "padded_link(<index>" not in index
    assert "text(size: h1, [Habits <habits>])" in index
    assert "stack(" not in index
    assert "padded_link(<habits>)" in month
    assert "January<habits-january>" in month


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
    habit_jan = _month_page(typst)
    assert "padded_link(<habits-january>)" in habit_jan
    assert "padded_link(<habits-february>)" in habit_jan
    assert "padded_link(<month-2026-01-01>)" not in habit_jan
    assert habit_jan.count("padded_link(<habits-january>)") >= 1
    cal_jan = next(
        page
        for page in _pages(typst)
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
    habit_jan = _month_page(typst)
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
    habit_jan = _month_page(typst)
    assert "padded_link(<month-2026-01-01>, [Calendar])" not in habit_jan
    assert "grid.cell(fill: black, text(white)[#padded_link(<habits-january>, [Habits])])" not in habit_jan


def _assert_heading_pair(title: str, name: str = "January") -> None:
    """Habits then January on one left-aligned line, descender seated."""
    needle = f"{name}<habits-{name.lower()}>"
    assert "dir: ttb" not in title
    assert _TRAIL_MARK not in title
    assert _MARK_RULE not in title
    assert "column-gutter: 6pt" not in title
    assert "text(size: h1)[/]" not in title
    assert "2026 /" not in title
    assert "spacing: 1fr" not in title
    assert "dir: ltr" in title
    assert "spacing: 0.5em" in title
    assert "width: 90%" in title
    assert "width: 100%" not in title
    assert "height: 100%" not in title
    assert "align(horizon + left" in title
    assert "padded_link(<habits>)" in title
    assert needle in title
    assert title.index("padded_link(<habits>)") < title.index(needle)
    assert 'bottom-edge: "descender"' in title
    assert "inset: (bottom: 0.25em)" in title
    assert 'top-edge: "cap-height"' not in title
    assert "inset: (top: 0.25em)" not in title


def test_habit_month_pages_set_trail_mark_alone():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="trail.toml")
    habits = _habits(dto)
    manifest = Manifest()
    habits.register(manifest)
    pages = habits.pages(manifest)
    assert pages[0].raw_typst is True
    assert pages[0].heading_mark is HeadingMark.LEAD
    month_names = (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )
    for page, name in zip(pages[1:], month_names, strict=True):
        assert page.heading_mark is HeadingMark.TRAIL
        assert page.nav_links == []
        assert page.show_quarters is False
        title = page.title or ""
        content = page.content
        _assert_heading_pair(title, name)
        assert f"{name}<habits-{name.lower()}>" not in content
        assert 'bottom-edge: "descender"' not in content
        assert "inset: (x: 2mm)" in content
        assert "align: horizon + right" in content


def test_mos_right_month_title_is_the_same_heading_pair():
    dto = parse_toml(
        _minimal(enable=["habits"], mos=_RIGHT_MOS, sections=""),
        source="trail-right.toml",
    )
    habits = _habits(dto)
    manifest = Manifest()
    habits.register(manifest)
    january = habits.pages(manifest)[1]
    title = january.title or ""
    assert january.heading_mark is HeadingMark.TRAIL
    assert january.nav_links == []
    _assert_heading_pair(title)
    assert "January<habits-january>" not in january.content
    assert 'bottom-edge: "descender"' not in january.content
    assert "inset: (x: 2mm)" in january.content
    left = parse_toml(_minimal(enable=["habits"], sections=""), source="trail-left.toml")
    left_jan = _habits(left).pages(manifest)[1]
    assert left_jan.title == january.title


def test_grid_uses_stroke_boxes_horizontal_names_and_thin_day_rules():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="grid.toml")
    typst = _generate(dto)
    assert "grid.cell(stroke: regular_stroke, [])" in typst
    assert _HEADER_LINE not in typst
    assert "luma(140)" not in typst
    assert "luma(180)" not in typst
    assert "grid.hline" not in typst
    assert _WEEK_RULE not in typst
    assert "0.4mm" not in typst
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
    habit_jan = _month_page(typst)
    assert "padded_link(<2026-01-01>)" in habit_jan
    assert "padded_link(<2026-01-14>)" in habit_jan
    assert "Thu 1" in habit_jan


def test_habit_columns_is_configurable():
    dto = parse_toml(
        _minimal(enable=["habits"], sections="[section.habits]\nhabit_columns = 8\n"),
        source="cols-8.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["habit_columns"] == 8
    habits = _habits(dto)
    assert habits.habit_columns == 8
    typst = _generate(short_january(dto))
    assert typst.count(_BOX) == 8 + _JAN_DAYS * 8
    assert _BOX_FRIDAY not in typst
    assert _WEEK_RULE not in typst
    assert "grid.hline" not in typst
    assert "columns: (auto, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr)" in typst


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
    index = _index_page(typst)
    month = _month_page(typst)
    assert "rotate(" in month
    assert "January" in index
    assert "JAN" not in index
    assert "→" not in index
    assert "columns: 1fr" in index
    assert "columns: (auto, 1fr)" not in index
    assert "grid.cell(fill: black" not in index
    assert "align: horizon + left" in index
    assert "align(horizon + left" in index
    assert "box(width: 100%, height: 100%" in index
    assert "padded_link(<habits-january>, box(width: 100%, height: 100%" in index
    assert "padded_link(<habits-january>)[January]" not in index
    assert "stroke: (bottom: regular_stroke)" not in index
    assert "2026 /" not in index
    assert "text(size: h1, [Habits <habits>])" in index


def test_nomad_full_year_is_thirteen_pages_of_habits():
    dto = load(NOMAD)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert "habits" in names
    assert names[-5:] == ["habits", "review", "tasks", "meetings", "colophon"]
    habits = next(s for s in dto["planner"]["sections"] if s["name"] == "habits")
    assert habits["params"]["habit_columns"] == 4
    assert habits["params"]["names"] == []
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


def test_default_names_are_empty_and_headers_are_blank():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="no-names.toml")
    assert dto["planner"]["sections"][0]["params"]["names"] == []
    habits = _habits(dto)
    assert habits.names == []
    typst = _generate(short_january(dto))
    assert _NAMED_MARK not in typst
    assert _HEADER_LINE not in typst
    assert typst.count(_BOX) == _DEFAULT_COLUMNS + _JAN_DAYS * _DEFAULT_COLUMNS
    assert _BOX_FRIDAY not in typst


def test_two_names_typeset_and_pad_to_four_columns():
    dto = parse_toml(
        _minimal(
            enable=["habits"],
            sections="[section.habits]\nnames = [\"Sleep\", \"Move\"]\n",
        ),
        source="two-names.toml",
    )
    params = dto["planner"]["sections"][0]["params"]
    assert params["habit_columns"] == 4
    assert params["names"] == ["Sleep", "Move"]
    habits = _habits(dto)
    assert habits.names == ["Sleep", "Move"]
    typst = _generate(short_january(dto))
    assert "Sleep" in typst
    assert "Move" in typst
    assert typst.count(_NAMED_MARK) == 2
    assert _HEADER_LINE not in typst
    assert typst.count(_BOX) == 2 + _JAN_DAYS * 4
    assert _BOX_FRIDAY not in typst
    assert "rotate(" not in _habit_header_src("Sleep")
    assert _HEADER_LINE not in _habit_header_src("Sleep")
    assert _HEADER_LINE not in _habit_header_src("")
    assert _BOX == _habit_header_src("")


def test_more_names_than_columns_is_config_error():
    with pytest.raises(ConfigError, match="names has 3 entries but habit_columns is 2"):
        parse_toml(
            _minimal(
                enable=["habits"],
                sections="[section.habits]\nhabit_columns = 2\nnames = [\"A\", \"B\", \"C\"]\n",
            ),
            source="too-many.toml",
        )


def test_empty_string_name_stays_blank_header():
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
    assert _HEADER_LINE not in typst
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
    named = [page for page in _pages(typst) if "align(center + horizon, text[Sleep])" in page]
    assert len(named) == 12
    for page in named:
        assert "align(center + horizon, text[Move])" in page
        assert _HEADER_LINE not in page
        assert "rotate(" in page
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
        _minimal(enable=["habits"], mos=_RIGHT_MOS, sections=""),
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
    assert "columns: (auto, 1fr, 1fr, 1fr, 1fr)" in right_jan
    thu = right_grid.index("Thu 1")
    assert right_grid.index(_BOX, thu) > thu
    right_june = _mos_page(right_typst, "June<habits-june>", "rotate(")
    june_grid = right_june[right_june.index("columns: (auto, 1fr") :]
    assert "Mon 1" in june_grid
    mon = june_grid.index("Mon 1")
    assert june_grid.index(_BOX, mon) > mon

    left = parse_toml(_minimal(enable=["habits"], sections=""), source="habits-mos-left.toml")
    left_jan = _mos_page(_generate(left), "January<habits-january>", "rotate(")
    assert "columns: (8mm, 1fr)" in left_jan
    assert "columns: (1fr, 8mm)" not in left_jan
    left_grid = left_jan[left_jan.index("columns: (auto, 1fr") :]
    assert "Thu 1" in left_grid
    left_thu = left_grid.index("Thu 1")
    assert left_grid.index(_BOX, left_thu) > left_thu
    for page in (right_jan, left_jan):
        assert "grid.cell(inset: (x: 2mm), align: horizon + right, [#[Thu 1]])" in page
        heading = page[page.index("width: 90%") : page.index("Thu 1")]
        assert "dir: ttb" not in heading
        assert "align(horizon + left" in heading
        assert heading.index("padded_link(<habits>)") < heading.index("January<habits-january>")

    monthly = """[section.monthly]
week_placement = "left"
week_label_rotation = "90deg"
daily_cell_height = "16mm"
"""
    both_right = parse_toml(
        _minimal(enable=["monthly", "habits"], mos=_RIGHT_MOS, sections=monthly),
        source="monthly-habits-right.toml",
    )
    monthly_only = parse_toml(
        _minimal(enable=["monthly"], mos=_RIGHT_MOS, sections=monthly),
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


def test_named_header_is_upright_blank_is_empty_cell():
    named = _habit_header("Sleep")
    blank = _habit_header("")
    assert "Sleep" in named
    assert "rotate(" not in named
    assert "atan" not in named
    assert _HEADER_LINE not in named
    assert "align(center + horizon, text[Sleep])" in named
    assert _HEADER_LINE not in blank
    assert blank == _BOX
    assert "Sleep" not in blank


def test_index_is_a_frozen_toc_with_full_names():
    """Yearly PDF: full month names, no current-month invert, labels centered in the band."""
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="index-toc.toml")
    typst = _generate(dto)
    index = _index_page(typst)
    full = (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )
    for name in full:
        wrapped = (
            f"padded_link(<habits-{name.lower()}>, "
            f"box(width: 100%, height: 100%, align(horizon + left, [{name}])))"
        )
        assert wrapped in index
        assert f"padded_link(<habits-{name.lower()}>)[{name}]" not in index
    for abbr in (
        "JAN",
        "FEB",
        "MAR",
        "APR",
        "MAY",
        "JUN",
        "JUL",
        "AUG",
        "SEP",
        "OCT",
        "NOV",
        "DEC",
    ):
        assert abbr not in index
    assert "grid.cell(fill: black" not in index
    assert "text(white)" not in index
    assert "→" not in index
    assert "1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr" in index
    assert "align: horizon + left" in index
    assert "align(horizon + left" in index
    assert "box(width: 100%, height: 100%" in index
    assert "inset: (x: 4pt, y: 0pt)" in index
    assert "align: bottom" not in index
    assert "stroke: (bottom: regular_stroke)" not in index


def test_index_has_no_current_month_even_in_another_planner_year():
    dto = parse_toml(
        _minimal(
            enable=["habits"],
            calendar="""[calendar]
year = 2025
week_starts = "Monday"
""",
            sections="",
        ),
        source="index-2025.toml",
    )
    typst = _generate(dto)
    index = _index_page(typst)
    assert "grid.cell(fill: black" not in index
    assert "text(white)" not in index
    assert (
        "padded_link(<habits-january>, "
        "box(width: 100%, height: 100%, align(horizon + left, [January])))"
        in index
    )
    assert "padded_link(<habits-january>)[January]" not in index
    assert "JAN" not in index
    assert "AUG" not in index
    assert "stroke: (bottom: regular_stroke)" not in index


def test_january_has_thin_day_rules_and_four_columns():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="friday.toml")
    typst = _generate(dto)
    january = _month_page(typst, "january")
    december = _month_page(typst, "december")
    assert january.count(_BOX) == _JAN_DAYS * 4 + 4
    assert december.count(_BOX) == 31 * 4 + 4
    assert _WEEK_RULE not in january
    assert _WEEK_RULE not in december
    jan_rows = _habit_rows_spec(january)
    dec_rows = _habit_rows_spec(december)
    assert jan_rows.count("1fr") == _JAN_DAYS
    assert dec_rows.count("1fr") == 31
    assert "0.4mm" not in jan_rows
    assert "0.4mm" not in dec_rows
    assert jan_rows.startswith("regular_height, 1fr, 1fr")
    assert dec_rows.startswith("regular_height, 1fr, 1fr")
    assert "16mm" not in jan_rows
    assert "16mm" not in dec_rows
    for page in (january, december):
        assert "grid.hline" not in page
        assert _BOX_FRIDAY not in page
        assert "bottom: thick_stroke" not in page
        assert 'text(weight: "bold")' not in page
        assert page.count("grid.cell(inset: (x: 2mm), align: horizon + right,") == 31
        assert "colspan:" not in page
        assert "0.4mm" not in page
        assert _HEADER_LINE not in page
    for day in (2, 9, 16, 23, 30):
        assert f"grid.cell(inset: (x: 2mm), align: horizon + right, [#[Fri {day}]])" in january
        assert (
            f"grid.cell(stroke: (rest: regular_stroke, bottom: thick_stroke), "
            f"align(horizon + right, [#[Fri {day}]]))"
        ) not in january
    for day in (4, 11, 18, 25):
        assert f"grid.cell(inset: (x: 2mm), align: horizon + right, [#[Fri {day}]])" in december
        assert (
            f"grid.cell(stroke: (rest: regular_stroke, bottom: thick_stroke), "
            f"align(horizon + right, [#[Fri {day}]]))"
        ) not in december
    assert "grid.cell(inset: (x: 2mm), align: horizon + right, [#[Sat 3]])" in january
    assert "grid.cell(inset: (x: 2mm), align: horizon + right, [#[Sun 4]])" in january
    assert "grid.cell(inset: (x: 2mm), align: horizon + right, [#[Mon 5]])" in january
    assert "Thu 1" in january
    assert "columns: (auto, 1fr, 1fr, 1fr, 1fr)" in january
    assert "columns: (auto, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr)" not in january
    assert "0.8mm" not in january
    assert "luma(140)" not in january
    assert "luma(180)" not in january


def test_index_heading_is_trail_strip_when_contents_on():
    dto = parse_toml(
        _minimal(enable=["index", "habits"], sections=""),
        source="mark.toml",
    )
    typst = _generate(short_january(dto))
    index = _index_page(typst)
    month = _month_page(typst)
    assert _TRAIL_MARK in index
    assert _TRAIL_MARK in month
    assert index.count(_MARK_RULE) == 1
    assert month.count(_MARK_RULE) == 1
    assert "2026 /" not in index
    assert "text(size: h1)[/]" not in index
    assert "padded_link(<annual>)" not in index
    assert "text(size: h1, [Habits <habits>])" in index
    heading = index[index.index(_SEATED_TITLE) : index.index(_SEATED_MARK)]
    assert "[Habits <habits>]" in heading
    assert _TRAIL_MARK not in heading
    assert _FOLLOW_RTL in index
    assert _SEAT_RTL not in index
    assert _SEATED_TRAIL in index
    assert index.index("[Habits <habits>]") < index.index(_TRAIL_MARK)
    assert "column-gutter: 6pt" not in heading
    month_heading = month[month.index(_SEATED_TITLE) : month.index(_SEATED_MARK)]
    assert _SEAT_RTL in month
    assert _SEATED_TRAIL in month
    assert "dir: ttb" not in month_heading
    assert "column-gutter: 6pt" not in month_heading
    assert "January<habits-january>" in month_heading
    assert "padded_link(<habits>)" in month_heading
    assert month_heading.index("padded_link(<habits>)") < month_heading.index("January<habits-january>")
    pair = month_heading[month_heading.index("dir: ltr") : month_heading.index("January<habits-january>")]
    assert _TRAIL_MARK not in pair
    assert _MARK_RULE not in pair
    assert "width: 90%" in month_heading
    assert "align(horizon + left" in month_heading
    assert "height: 100%" not in month_heading
    assert "align(bottom + left" not in month_heading
    assert "spacing: 0.5em" in month_heading
    assert month.index("January<habits-january>") < month.index(_TRAIL_MARK)
    assert month.index(_TRAIL_MARK) < month.index("Thu 1")
    assert 'bottom-edge: "descender"' in month_heading
    assert "inset: (bottom: 0.25em)" in month_heading
    assert 'top-edge: "cap-height"' not in month
    assert "inset: (top: 0.25em)" not in month
    assert "grid.cell(inset: (x: 2mm), align: horizon + right, [#[Thu 1]])" in month
    assert "padded_link(<habits>)" in month
    assert "2026 /" not in month
    assert "text(size: h1)[/]" not in month
    assert ", [Habits])" not in month
    assert ", [Calendar])" not in month
    contents = next(p for p in _pages(typst) if 'weight: "bold")[Contents <index>]' in p)
    assert "padded_link(<index>" not in contents
    assert "padded_link(<habits>" in contents


def test_mos_right_month_mark_trails_alone_left_of_rail():
    dto = parse_toml(
        _minimal(enable=["index", "habits"], mos=_RIGHT_MOS, sections=""),
        source="habits-mos-right-mark.toml",
    )
    typst = _generate(short_january(dto))
    month = _month_page(typst)
    assert _TRAIL_MARK in month
    assert month.index("January<habits-january>") < month.index(_TRAIL_MARK)
    heading = month[month.index(_SEATED_TITLE) : month.index(_SEATED_MARK)]
    assert _SEAT_LTR in month
    assert _SEATED_TRAIL in month
    assert "dir: ttb" not in heading
    assert "column-gutter: 6pt" not in heading
    assert heading.index("padded_link(<habits>)") < heading.index("January<habits-january>")
    pair = heading[heading.index("dir: ltr") : heading.index("January<habits-january>")]
    assert _TRAIL_MARK not in pair
    assert _MARK_RULE not in pair
    assert "width: 90%" in heading
    assert "align(horizon + left" in heading
    assert "height: 100%" not in heading
    assert "align(bottom + left" not in heading
    assert "spacing: 0.5em" in heading
    assert 'bottom-edge: "descender"' in heading
    assert "inset: (bottom: 0.25em)" in heading
    assert 'top-edge: "cap-height"' not in heading
    assert "inset: (top: 0.25em)" not in heading
    assert "grid.cell(inset: (x: 2mm), align: horizon + right, [#[Thu 1]])" in month
    assert "padded_link(<habits>)" in month
    assert "2026 /" not in month
    assert ", [Habits])" not in month
    assert ", [Calendar])" not in month
    strip_at = month.index("rowspan: 2")
    assert month.index(_TRAIL_MARK) < strip_at
