"""Habits index + per-month tracker grids."""

from __future__ import annotations

from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.config import load
from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.sections.habits import Habits
from eink_planner.services.generate import Generate
from eink_planner.toml_config import parse_toml
from tests.test_toml_omit_sections import _LABEL_DEF, _PADDED_LINK, compile_pdf
from tests.toml_fixtures import _minimal, short_january

REPO = Path(__file__).resolve().parents[1]
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
    )


def test_listed_without_table_defaults_columns_and_pages():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="default-habits.toml")
    section = dto["planner"]["sections"][0]
    assert section["name"] == "habits"
    assert section["class"] == "habits"
    assert section["params"]["habit_columns"] == 12
    habits = _habits(dto)
    assert habits.habit_columns == Habits.DEFAULT_COLUMNS == 12
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
    month = next(page for page in pages if "<habits-january>" in page and "rotate(" in page)
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
    habit_jan = next(page for page in pages if "<habits-january>" in page and "rotate(" in page)
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
    habit_jan = next(page for page in pages if "<habits-january>" in page and "rotate(" in page)
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
    habit_jan = next(page for page in pages if "<habits-january>" in page and "rotate(" in page)
    assert "padded_link(<month-2026-01-01>, [Calendar])" not in habit_jan
    assert "grid.cell(fill: black, text(white)[#padded_link(<habits-january>, [Habits])])" not in habit_jan


def test_grid_uses_stroke_boxes_diagonal_header_and_weekend_grey():
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="grid.toml")
    typst = _generate(dto)
    assert "grid.cell(stroke: regular_stroke, [])" in typst
    assert "line(start: (0%, 100%), end: (100%, 0%), stroke: regular_stroke)" in typst
    assert "luma(140)" in typst
    assert "luma(180)" in typst
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
    habit_jan = next(page for page in pages if "<habits-january>" in page and "rotate(" in page)
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
    assert typst.count("grid.cell(stroke: regular_stroke, [])") == 31 * 8


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
    month = next(page for page in pages if "<habits-january>" in page and "rotate(" in page)
    assert "rotate(" in month
    assert "JAN" in index
    assert "→" in index


def test_nomad_full_year_is_thirteen_pages_of_habits():
    dto = load(NOMAD)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-1] == "habits"
    assert dto["planner"]["sections"][-1]["params"]["habit_columns"] == 12
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
