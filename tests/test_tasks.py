"""Weekly Tasks: week index + ticked leftover pages (raw Typst, no MOS)."""

from __future__ import annotations


import pytest

from parch import ConfigError
from parch.config import load
from parch.mos.configurator import Configurator
from parch.sections.tasks import Tasks
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.test_toml_omit_sections import _LABEL_DEF, _PADDED_LINK, compile_pdf
from tests.toml_fixtures import _minimal, short_january
from tests.helpers import base_config, load_default

NOMAD = base_config("supernote-nomad")
_EN_DASH = "–"

# 2026, Monday week start: Jan 1 is Thursday.
# Full year: Dec 29 2025 – Jan 3 2027 → 53 ISO weeks.
# short_january (end 2026-01-14) still walks all of January: 5 weeks.
_JAN_WEEKS = (
    ("2026W01", 1, f"Dec 29 {_EN_DASH} Jan 4"),
    ("2026W02", 2, f"Jan 5 {_EN_DASH} 11"),
    ("2026W03", 3, f"Jan 12 {_EN_DASH} 18"),
    ("2026W04", 4, f"Jan 19 {_EN_DASH} 25"),
    ("2026W05", 5, f"Jan 26 {_EN_DASH} Feb 1"),
)
_W44_RANGE = f"Oct 26 {_EN_DASH} Nov 1"
_W53_RANGE = f"Dec 28 {_EN_DASH} Jan 3"


def _generate(dto) -> str:
    return Generate(i18n=load_default()).generate(dto)


def _tasks(dto) -> Tasks:
    params = {}
    for section in dto["planner"]["sections"]:
        if section.get("class") == "tasks" or section.get("name") == "tasks":
            params = dict(section.get("params") or {})
            break
    return Tasks(
        section_name="tasks",
        i18n=load_default(),
        configurator=Configurator(dto),
        weeks_per_page=params.get("weeks_per_page", Tasks.DEFAULT_WEEKS_PER_PAGE),
    )


def _pages(typst: str) -> list[str]:
    return typst.split("#pagebreak()")


def _index_page(typst: str, page_id: str = "tasks") -> str:
    needle = f"[{'Tasks'} <{page_id}>]"
    for page in _pages(typst):
        if needle in page and "rotate(" not in page:
            return page
    raise AssertionError(f"no Tasks index page {page_id}")


def _week_page(typst: str, week_id: str) -> str:
    marker = f"<tasks-{week_id}>"
    for page in _pages(typst):
        if marker in page and "rotate(" not in page and "[Tasks <tasks-" not in page:
            # week pages define #[] <tasks-WEEK>; index pages only link to it
            if f"#[] <tasks-{week_id}>" in page:
                return page
    raise AssertionError(f"no Tasks week page {week_id}")


def test_listed_without_table_defaults_weeks_per_page():
    dto = parse_toml(_minimal(enable=["tasks"], sections=""), source="default-tasks.toml")
    section = dto["planner"]["sections"][0]
    assert section["name"] == "tasks"
    assert section["class"] == "tasks"
    assert section["params"]["weeks_per_page"] == 13
    tasks = _tasks(dto)
    assert tasks.weeks_per_page == Tasks.DEFAULT_WEEKS_PER_PAGE == 13
    typst = _generate(dto)
    assert "<tasks>" in typst
    for week_id, number, rng in _JAN_WEEKS:
        assert f"<tasks-{week_id}>" in typst
        assert str(number) in typst
        assert rng in typst
    assert "<tasks-2>" in typst
    assert "<tasks-4>" in typst
    assert "<tasks-5>" not in typst


def test_short_january_is_one_index_and_five_weeks():
    dto = parse_toml(_minimal(enable=["tasks"], sections=""), source="short.toml")
    typst = _generate(short_january(dto))
    assert "<tasks>" in typst
    assert "<tasks-2>" not in typst
    for week_id, number, rng in _JAN_WEEKS:
        assert f"<tasks-{week_id}>" in typst
        index = _index_page(typst)
        assert str(number) in index
        assert rng in index
        assert f"W{number}" not in index
        assert f"Week {number}" not in index
    assert typst.count("#pagebreak()") == 5  # 1 index + 5 weeks - 1


def test_index_year_links_to_annual_and_week_crumb_links_back():
    dto = parse_toml(
        _minimal(
            enable=["annual", "tasks"],
            sections="""[section.annual]
show_month_name = true
""",
        ),
        source="links.toml",
    )
    typst = _generate(short_january(dto))
    index = _index_page(typst)
    assert "padded_link(<annual>)" in index
    week = _week_page(typst, "2026W01")
    assert "padded_link(<tasks>)" in week
    assert "padded_link(<tasks-2>)" not in week
    labels = set(_LABEL_DEF.findall(typst))
    links = set(_PADDED_LINK.findall(typst))
    assert {"tasks", "tasks-2026W01", "annual"} <= labels
    assert {"tasks", "tasks-2026W01", "annual"} <= links


def test_year_is_plain_when_annual_omitted():
    dto = parse_toml(_minimal(enable=["tasks"], sections=""), source="no-annual.toml")
    typst = _generate(short_january(dto))
    assert "padded_link(<annual>)" not in typst
    assert "2026" in typst
    assert "<tasks>" in typst


def test_index_is_raw_typst_full_band_no_arrows_no_invert():
    dto = parse_toml(_minimal(enable=["tasks"], sections=""), source="chrome.toml")
    typst = _generate(short_january(dto))
    index = _index_page(typst)
    assert "rotate(" not in index
    assert "→" not in index
    assert "grid.cell(fill: black" not in index
    assert "text(white)" not in index
    assert "Q4" not in index
    assert "Q1" not in index
    assert "columns: 1fr" in index
    assert "columns: (2em, 1fr)" in index
    assert "align: horizon + left" in index
    assert "box(width: 100%, height: 100%" in index
    assert (
        "padded_link(<tasks-2026W01>, box(width: 100%, height: 100%"
        in index
    )
    assert "padded_link(<tasks-2026W01>)[1" not in index
    assert "[W01" not in index
    assert " W01" not in index
    assert "W1 " not in index
    assert "Week 1" not in index
    # no band stroke (Contents / Habits family), no quiet chunk range
    assert "stroke: (bottom: regular_stroke)" not in index
    assert f"Dec 29 {_EN_DASH} Feb 1" not in index


def test_index_range_wording_same_month_cross_month_cross_year():
    dto = parse_toml(_minimal(enable=["tasks"], sections=""), source="ranges.toml")
    typst = _generate(short_january(dto))
    index = _index_page(typst)
    assert f"Dec 29 {_EN_DASH} Jan 4" in index
    assert f"Jan 5 {_EN_DASH} 11" in index
    assert f"Jan 26 {_EN_DASH} Feb 1" in index
    assert "2025" not in index
    assert "2026" in index
    assert "2025-" not in index


def test_weeks_per_page_paginates_index_ids_and_crumb_targets():
    dto = parse_toml(
        _minimal(enable=["tasks"], sections="[section.tasks]\nweeks_per_page = 2\n"),
        source="paginate.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["weeks_per_page"] == 2
    typst = _generate(short_january(dto))
    assert "<tasks>" in typst
    assert "<tasks-2>" in typst
    assert "<tasks-3>" not in typst
    page1 = _index_page(typst, "tasks")
    page2 = _index_page(typst, "tasks-2")
    assert "<tasks-2026W01>" in page1
    assert "<tasks-2026W02>" in page1
    assert "<tasks-2026W03>" in page2
    assert "<tasks-2026W04>" in page2
    assert "<tasks-2026W05>" in page2
    for page in (page1, page2):
        assert "[Tasks <" in page
        assert "2026" in page
        assert "Q4" not in page
        assert "→" not in page
    w1 = _week_page(typst, "2026W01")
    w3 = _week_page(typst, "2026W03")
    w5 = _week_page(typst, "2026W05")
    assert "padded_link(<tasks>)" in w1
    assert "padded_link(<tasks-2>)" not in w1
    assert "padded_link(<tasks-2>)" in w3
    assert "padded_link(<tasks>)" not in w3
    assert "padded_link(<tasks-2>)" in w5
    assert "padded_link(<tasks>)" not in w5
    assert "padded_link(<tasks-3>)" not in w5


def test_full_year_default_pagination_ids():
    dto = parse_toml(_minimal(enable=["tasks"], sections=""), source="year.toml")
    typst = _generate(dto)
    assert "<tasks>" in typst
    assert "<tasks-2>" in typst
    assert "<tasks-3>" in typst
    assert "<tasks-4>" in typst
    assert "<tasks-5>" not in typst
    page1 = _index_page(typst, "tasks")
    page4 = _index_page(typst, "tasks-4")
    assert "<tasks-2026W01>" in page1
    assert "<tasks-2026W13>" in page1
    assert "<tasks-2026W14>" not in page1
    assert "<tasks-2026W40>" in page4
    assert "<tasks-2026W44>" in page4
    assert "<tasks-2026W52>" in page4
    assert "<tasks-2026W53>" in page4
    assert _W44_RANGE in page4
    assert _W53_RANGE in page4
    w44 = _week_page(typst, "2026W44")
    assert "padded_link(<tasks-4>)" in w44
    assert "padded_link(<tasks>)" not in w44
    w53 = _week_page(typst, "2026W53")
    assert "padded_link(<tasks-4>)" in w53
    assert "padded_link(<tasks-5>)" not in w53


def test_week_page_is_raw_typst_ticked_not_mos():
    dto = parse_toml(_minimal(enable=["tasks"], sections=""), source="week-chrome.toml")
    typst = _generate(short_january(dto))
    week = _week_page(typst, "2026W01")
    assert "rotate(" not in week
    assert "$square.stroked$" in week
    assert "stroke: (_, _) => (bottom: regular_stroke + black)" in week
    assert "size.height / regular_height" in week
    assert "calc.floor" in week
    assert "regular_stroke + luma(130)" not in week
    assert "luma(130)" not in week
    assert "rect_pattern(dotted)" not in week
    assert "Q4" not in week
    assert "Q1" not in week
    assert "→" not in week
    assert "W44" not in week
    assert "[W01" not in week
    assert " W01" not in week
    assert "NOVEMBER" not in week
    assert "January" not in week
    assert "columns: (1fr, 1fr, 1fr)" not in week
    assert "columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr)" in week
    assert "What went" not in week
    assert "prompt" not in week.lower()
    assert "Week 1" in week
    assert f"Dec 29 {_EN_DASH} Jan 4" in week
    assert "text(size: 0.85em)" in week
    assert "luma(" not in week
    # do not box the writing column
    assert "stroke: regular_stroke + black" not in week or "columns: (regular_height, 1fr)" not in week


def test_day_strip_labels_and_links_when_daily_exists():
    dto = parse_toml(
        _minimal(
            enable=["daily", "tasks"],
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
    week = _week_page(typst, "2026W01")
    assert "Monday 29" in week
    assert "Tuesday 30" in week
    assert "Wednesday 31" in week
    assert "box(text(size: 6pt)[Wednesday 31])" in week
    assert "Wed 31" not in week
    assert week.count("line(length: 100%, stroke: regular_stroke + black)") == 7
    assert "Thursday 1" in week
    assert "Friday 2" in week
    assert "Saturday 3" in week
    assert "Sunday 4" in week
    assert "MON / 29" not in week
    assert "MON / 27" not in week
    assert "Mon 29" not in week
    assert "padded_link(<2025-12-29>" not in week
    assert "padded_link(<2026-01-01>" in week
    assert "padded_link(<2026-01-04>" in week
    assert "padded_link(<2026-01-01>, box(width: 100%, height: 100%" in week
    assert "luma(" not in week
    assert "fill: black" not in week


def test_day_cells_plain_when_daily_omitted():
    dto = parse_toml(_minimal(enable=["tasks"], sections=""), source="no-daily.toml")
    typst = _generate(short_january(dto))
    week = _week_page(typst, "2026W01")
    assert "Monday 29" in week
    assert "padded_link(<2025-12-29>" not in week
    assert "padded_link(<2026-01-01>" not in week


def test_week_n_taps_weekly_planner():
    dto = parse_toml(
        _minimal(
            enable=["weekly", "tasks"],
            sections="""[section.weekly]
column_gutter = "4pt"
""",
        ),
        source="week-link.toml",
    )
    typst = _generate(short_january(dto))
    labels = set(_LABEL_DEF.findall(typst))
    assert "2026W01" in labels
    assert "tasks-2026W01" in labels
    assert "tasks" in labels
    week = _week_page(typst, "2026W01")
    assert "padded_link(<2026W01>)[Week 1]" in week
    assert "padded_link(<tasks-2026W01>" in _index_page(typst)
    assert "padded_link(<2026W01>" not in _index_page(typst)


def test_weeks_per_page_bool_and_float_rejected():
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(enable=["tasks"], sections="[section.tasks]\nweeks_per_page = true\n"),
            source="bool.toml",
        )
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(enable=["tasks"], sections="[section.tasks]\nweeks_per_page = 12.5\n"),
            source="float.toml",
        )


def test_weeks_per_page_zero_rejected():
    with pytest.raises(ConfigError, match="weeks_per_page"):
        parse_toml(
            _minimal(enable=["tasks"], sections="[section.tasks]\nweeks_per_page = 0\n"),
            source="zero.toml",
        )


def test_unknown_key_on_section_tasks_raises():
    with pytest.raises(ConfigError, match="unknown key: section.tasks.foo"):
        parse_toml(
            _minimal(enable=["tasks"], sections="[section.tasks]\nfoo = 1\n"),
            source="foo.toml",
        )


def test_nomad_ships_tasks_after_review():
    dto = load(NOMAD)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-5:] == ["habits", "review", "tasks", "meetings", "colophon"]
    tasks = next(s for s in dto["planner"]["sections"] if s["name"] == "tasks")
    assert tasks["params"]["weeks_per_page"] == 13
    assert "tasks" in NOMAD.read_text(encoding="utf-8")


def test_short_january_tasks_compiles(tmp_path):
    dto = parse_toml(_minimal(enable=["tasks"], sections=""), source="compile.toml")
    typst = _generate(short_january(dto))
    pdf, stderr = compile_pdf(typst, tmp_path / "tasks")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_tiny_annual_tasks_compiles(tmp_path):
    dto = parse_toml(
        _minimal(
            enable=["annual", "tasks"],
            sections="""[section.annual]
show_month_name = true
""",
        ),
        source="tiny-tasks.toml",
    )
    typst = _generate(short_january(dto))
    pdf, stderr = compile_pdf(typst, tmp_path / "tiny-tasks")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_range_helper_matches_locale_short_months():
    dto = parse_toml(_minimal(enable=["tasks"], sections=""), source="helper.toml")
    tasks = _tasks(short_january(dto))
    weeks = tasks._weeks()
    assert len(weeks) == 5
    assert tasks.range_label(weeks[0].days()[0], weeks[0].days()[-1]) == f"Dec 29 {_EN_DASH} Jan 4"
    assert tasks.range_label(weeks[1].days()[0], weeks[1].days()[-1]) == f"Jan 5 {_EN_DASH} 11"
    assert tasks.range_label(weeks[4].days()[0], weeks[4].days()[-1]) == f"Jan 26 {_EN_DASH} Feb 1"


def test_chunks_pack_53_weeks_as_13_13_13_14():
    dto = parse_toml(_minimal(enable=["tasks"], sections=""), source="pack.toml")
    tasks = _tasks(dto)
    weeks = tasks._weeks()
    assert len(weeks) == 53
    assert tasks._page_sizes(53) == [13, 13, 13, 14]
    chunks = tasks._chunks(weeks)
    assert [len(c) for c in chunks] == [13, 13, 13, 14]
    assert [w.number for w in chunks[-1]] == list(range(40, 54))
    assert tasks._index_count(53) == 4


def test_short_index_keeps_13_row_height():
    dto = parse_toml(_minimal(enable=["tasks"], sections=""), source="short-height.toml")
    typst = _generate(short_january(dto))
    index = _index_page(typst)
    assert "rows: (5fr, 8fr)" in index
    assert "columns: (2em, 1fr)" in index


def test_page_sizes_absorb_only_when_previous_stays_at_most_14():
    dto = parse_toml(
        _minimal(enable=["tasks"], sections="[section.tasks]\nweeks_per_page = 20\n"),
        source="leftover.toml",
    )
    tasks = _tasks(dto)
    assert tasks.weeks_per_page == 20
    assert tasks._page_sizes(21) == [20, 1]
    assert tasks._page_sizes(53) == [20, 20, 13]
    two = _tasks(
        parse_toml(
            _minimal(enable=["tasks"], sections="[section.tasks]\nweeks_per_page = 2\n"),
            source="two.toml",
        )
    )
    assert two._page_sizes(5) == [2, 3]


def test_contents_mark_on_tasks_when_index_on():
    dto = parse_toml(
        _minimal(enable=["index", "tasks"], sections=""),
        source="mark.toml",
    )
    typst = _generate(short_january(dto))
    index = _index_page(typst)
    week = _week_page(typst, "2026W01")
    assert "padded_link(<index>" in index
    assert "padded_link(<index>" in week
    assert "line(length: 0.844em, stroke: thick_stroke + black)" in index
    contents = next(p for p in _pages(typst) if 'weight: "bold")[Contents <index>]' in p)
    assert "padded_link(<index>" not in contents
    assert "padded_link(<tasks>" in contents
