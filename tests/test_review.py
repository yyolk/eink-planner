"""Weekly Review: week index + lined leftover-notes pages (raw Typst, no MOS)."""


import pytest

from parch import ConfigError
from parch.config import load
from parch.mos.configurator import Configurator
from parch.compose.page_data import HeadingMark
from parch.mos.manifest import Manifest
from parch.sections.review import Review
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.test_toml_omit_sections import _LABEL_DEF, _PADDED_LINK, compile_pdf
from tests.toml_fixtures import _minimal, short_january
from tests.helpers import base_config, load_default

NOMAD = base_config("supernote-nomad")
_EN_DASH = "–"
_MARK_RULE = "contents_bars(size:"
_TRAIL_MARK = "padded_link(padding: 0pt, <index>"
_LEAD_PAIR = "lead_pair("
_SEAT_RTL = "spacing: 1fr, direction: rtl"
_FOLLOW_SPACING = "spacing: 0.5em"

# 2026, Monday week start: Jan 1 is Thursday.
# Walk is start.beginning_of_month().beginning_of_week() through
# end.end_of_month().end_of_week() in 7-day Week chunks.
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


def _review(dto) -> Review:
    params = {}
    for section in dto["planner"]["sections"]:
        if section.get("class") == "review" or section.get("name") == "review":
            params = dict(section.get("params") or {})
            break
    return Review(
        section_name="review",
        i18n=load_default(),
        configurator=Configurator(dto),
        weeks_per_page=params.get("weeks_per_page", Review.DEFAULT_WEEKS_PER_PAGE),
        pattern=params.get("pattern", "lined"),
    )


def _pages(typst: str) -> list[str]:
    return typst.split("#pagebreak()")


def _review_pages(typst: str) -> list[str]:
    """Pages that belong to Review (raw Typst: no MOS rotate)."""
    out = []
    for page in _pages(typst):
        if "rotate(" in page:
            continue
        if "<review" in page or "review_lined" in page:
            out.append(page)
    return out


def _index_page(typst: str, page_id: str = "review") -> str:
    needle = f"[{'Review'} <{page_id}>]"
    for page in _pages(typst):
        if needle in page and "rotate(" not in page:
            return page
    raise AssertionError(f"no Review index page {page_id}")


def _week_page(typst: str, week_id: str) -> str:
    # Week pages define the label next to #h(0.6em); index pages only link to it.
    marker = f"<review-{week_id}> #h(0.6em)"
    for page in _pages(typst):
        if marker in page and "rotate(" not in page:
            return page
    raise AssertionError(f"no Review week page {week_id}")


def test_listed_without_table_defaults_weeks_per_page():
    dto = parse_toml(_minimal(enable=["review"], sections=""), source="default-review.toml")
    section = dto["planner"]["sections"][0]
    assert section["name"] == "review"
    assert section["class"] == "review"
    assert section["params"]["weeks_per_page"] == 13
    assert section["params"]["pattern"] == "lined"
    review = _review(dto)
    assert review.weeks_per_page == Review.DEFAULT_WEEKS_PER_PAGE == 13
    assert review.pattern == "lined"
    typst = _generate(dto)
    assert "<review>" in typst
    for week_id, number, rng in _JAN_WEEKS:
        # Full year of 2026, first index page holds weeks 1–13.
        assert f"<review-{week_id}>" in typst
        assert str(number) in typst
        assert rng in typst
    assert "<review-2>" in typst
    assert "<review-4>" in typst
    assert "<review-5>" not in typst


def test_short_january_is_one_index_and_five_weeks():
    dto = parse_toml(_minimal(enable=["review"], sections=""), source="short.toml")
    typst = _generate(short_january(dto))
    assert "<review>" in typst
    assert "<review-2>" not in typst
    for week_id, number, rng in _JAN_WEEKS:
        assert f"<review-{week_id}>" in typst
        index = _index_page(typst)
        assert str(number) in index
        assert rng in index
        assert f"W{number}" not in index
        assert f"Week {number}" not in index
    assert typst.count("#pagebreak()") == 5  # 1 index + 5 weeks - 1


def test_index_title_is_review_and_week_links_back():
    dto = parse_toml(
        _minimal(
            enable=["annual", "review"],
            sections="""[section.annual]
show_month_name = true
""",
        ),
        source="links.toml",
    )
    typst = _generate(short_january(dto))
    index = _index_page(typst)
    assert "padded_link(<annual>)" not in index
    assert "2026 /" not in index
    assert "text(size: h1)[/]" not in index
    assert "text(size: h1, [Review <review>])" in index
    week = _week_page(typst, "2026W01")
    assert "padded_link(<review>)" in week
    assert "padded_link(<review-2>)" not in week
    assert "padded_link(<annual>)" not in week
    labels = set(_LABEL_DEF.findall(typst))
    links = set(_PADDED_LINK.findall(typst))
    assert {"review", "review-2026W01", "annual"} <= labels
    assert {"review", "review-2026W01"} <= links
    assert "annual" not in set(_PADDED_LINK.findall(index + week))


def test_header_is_review_without_year_when_contents_off():
    dto = parse_toml(_minimal(enable=["review"], sections=""), source="no-annual.toml")
    typst = _generate(short_january(dto))
    index = _index_page(typst)
    week = _week_page(typst, "2026W01")
    for page in (index, week):
        assert "padded_link(<annual>)" not in page
        assert "2026 /" not in page
        assert "text(size: h1)[/]" not in page
        assert "pad(right: 3mm" not in page
        assert "padded_link(<index>" not in page
        assert "column-gutter: 6pt" not in page
        assert "columns: (auto, auto)" not in page
    assert "text(size: h1, [Review <review>])" in index
    assert "stack(" not in index
    assert "padded_link(<review>)" in week
    assert "<review>" in typst


def test_index_is_raw_typst_full_band_no_arrows_no_invert():
    dto = parse_toml(_minimal(enable=["review"], sections=""), source="chrome.toml")
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
        "padded_link(<review-2026W01>, box(width: 100%, height: 100%"
        in index
    )
    assert "padded_link(<review-2026W01>)[1" not in index
    assert "[1 #text(size: 0.85em)" not in index
    assert "[W01" not in index
    assert " W01" not in index
    assert "W1 " not in index
    assert "Week 1" not in index


def test_index_range_wording_same_month_cross_month_cross_year():
    dto = parse_toml(_minimal(enable=["review"], sections=""), source="ranges.toml")
    typst = _generate(short_january(dto))
    index = _index_page(typst)
    assert f"Dec 29 {_EN_DASH} Jan 4" in index  # cross year, no year digits
    assert f"Jan 5 {_EN_DASH} 11" in index  # same month
    assert f"Jan 26 {_EN_DASH} Feb 1" in index  # cross month
    assert "2025" not in index
    assert "2026 /" not in index
    assert "text(size: h1)[/]" not in index
    assert "text(size: h1, [Review <review>])" in index
    assert "2025-" not in index


def test_index_quiet_span_is_first_through_last_week_on_that_page():
    dto = parse_toml(_minimal(enable=["review"], sections=""), source="span.toml")
    typst = _generate(short_january(dto))
    index = _index_page(typst)
    assert f"Dec 29 {_EN_DASH} Feb 1" in index


def test_weeks_per_page_paginates_index_ids_and_crumb_targets():
    dto = parse_toml(
        _minimal(enable=["review"], sections="[section.review]\nweeks_per_page = 2\n"),
        source="paginate.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["weeks_per_page"] == 2
    typst = _generate(short_january(dto))
    assert "<review>" in typst
    assert "<review-2>" in typst
    assert "<review-3>" not in typst
    page1 = _index_page(typst, "review")
    page2 = _index_page(typst, "review-2")
    assert "<review-2026W01>" in page1
    assert "<review-2026W02>" in page1
    assert "<review-2026W03>" in page2
    assert "<review-2026W04>" in page2
    assert "<review-2026W05>" in page2
    assert f"Dec 29 {_EN_DASH} Jan 11" in page1
    assert f"Jan 12 {_EN_DASH} Feb 1" in page2
    for page in (page1, page2):
        assert "[Review <" in page
        assert "2026 /" not in page
        assert "text(size: h1)[/]" not in page
        assert "padded_link(<annual>)" not in page
        assert "Q4" not in page
        assert "→" not in page
    w1 = _week_page(typst, "2026W01")
    w3 = _week_page(typst, "2026W03")
    w5 = _week_page(typst, "2026W05")
    assert "padded_link(<review>)" in w1
    assert "padded_link(<review-2>)" not in w1
    assert "padded_link(<review-2>)" in w3
    assert "padded_link(<review>)" not in w3
    assert "padded_link(<review-2>)" in w5
    assert "padded_link(<review>)" not in w5
    assert "padded_link(<review-3>)" not in w5


def test_full_year_default_pagination_ids():
    dto = parse_toml(_minimal(enable=["review"], sections=""), source="year.toml")
    typst = _generate(dto)
    assert "<review>" in typst
    assert "<review-2>" in typst
    assert "<review-3>" in typst
    assert "<review-4>" in typst
    assert "<review-5>" not in typst
    page1 = _index_page(typst, "review")
    page4 = _index_page(typst, "review-4")
    assert "<review-2026W01>" in page1
    assert "<review-2026W13>" in page1
    assert "<review-2026W14>" not in page1
    assert "<review-2026W40>" in page4
    assert "<review-2026W44>" in page4
    assert "<review-2026W52>" in page4
    assert "<review-2026W53>" in page4
    assert _W44_RANGE in page4
    assert _W53_RANGE in page4
    w44 = _week_page(typst, "2026W44")
    assert "padded_link(<review-4>)" in w44
    assert "padded_link(<review>)" not in w44
    w53 = _week_page(typst, "2026W53")
    assert "padded_link(<review-4>)" in w53
    assert "padded_link(<review-5>)" not in w53


def test_week_page_is_raw_typst_lined_not_mos():
    dto = parse_toml(_minimal(enable=["review"], sections=""), source="week-chrome.toml")
    typst = _generate(short_january(dto))
    week = _week_page(typst, "2026W01")
    assert "rotate(" not in week
    assert "rect_pattern(lined)" not in week
    assert "rect_pattern(review_lined)" in week
    assert "regular_stroke + black" in week
    assert "regular_stroke + luma(130)" not in week
    assert "luma(130)" not in week
    assert "rect_pattern(dotted)" not in week
    assert "Q4" not in week
    assert "Q1" not in week
    assert "→" not in week
    assert "W44" not in week
    assert "Week 1" not in week
    assert "[W01" not in week
    assert " W01" not in week
    assert "NOVEMBER" not in week
    assert "January" not in week
    assert "columns: (1fr, 1fr, 1fr)" not in week
    assert "columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr)" in week
    # writing field is one full-width lined column, not 7 or 3 day columns
    assert week.count("rect_pattern(review_lined)") == 1
    assert "grid.cell(colspan: 3, rect_pattern" not in week
    assert "What went" not in week
    assert "prompt" not in week.lower()
    assert f"1 <review-2026W01>" in week
    assert f"Dec 29 {_EN_DASH} Jan 4" in week
    assert "luma(" not in week


def test_day_strip_labels_and_links_when_daily_exists():
    dto = parse_toml(
        _minimal(
            enable=["daily", "review"],
            sections="""[section.daily]
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
    assert "Mon 29" in week
    assert "Tue 30" in week
    assert "Wed 31" in week
    assert "Thu 1" in week
    assert "Fri 2" in week
    assert "Sat 3" in week
    assert "Sun 4" in week
    assert "MON / 29" not in week
    assert "MON / 27" not in week
    # Daily only covers the configured dates; the week-padded Dec days stay plain.
    assert "padded_link(<2025-12-29>" not in week
    assert "Mon 29" in week
    assert "padded_link(<2026-01-01>" in week
    assert "padded_link(<2026-01-04>" in week
    # whole cell is the tap target
    assert "padded_link(<2026-01-01>, box(width: 100%, height: 100%" in week
    # same ink sat/sun — no grey, no weekend fill
    assert "luma(" not in week
    assert "fill: black" not in week


def test_day_cells_plain_when_daily_omitted():
    dto = parse_toml(_minimal(enable=["review"], sections=""), source="no-daily.toml")
    typst = _generate(short_january(dto))
    week = _week_page(typst, "2026W01")
    assert "Mon 29" in week
    assert "padded_link(<2025-12-29>" not in week
    assert "padded_link(<2026-01-01>" not in week


def test_review_ids_do_not_collide_with_weekly():
    dto = parse_toml(
        _minimal(
            enable=["weekly", "review"],
            sections="""[section.weekly]
column_gutter = "4pt"
""",
        ),
        source="collide.toml",
    )
    typst = _generate(short_january(dto))
    labels = set(_LABEL_DEF.findall(typst))
    assert "2026W01" in labels
    assert "review-2026W01" in labels
    assert "review" in labels
    weekly = next(page for page in _pages(typst) if "<2026W01>" in page and "rotate(" in page)
    review = _week_page(typst, "2026W01")
    assert "padded_link(<review-2026W01>" in _index_page(typst)
    assert "padded_link(<2026W01>" not in _index_page(typst)
    assert "<2026W01>" in weekly
    assert "<review-2026W01>" not in weekly
    assert "<review-2026W01>" in review
    assert "Week 1" in weekly
    assert "Week 1" not in review
    # weekly planner is house week_matrix; review is not
    assert "week_matrix(" in weekly
    assert "week_matrix(" not in review
    assert "columns: (1fr, 1fr, 1fr)" not in review


def test_weeks_per_page_bool_and_float_rejected():
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(enable=["review"], sections="[section.review]\nweeks_per_page = true\n"),
            source="bool.toml",
        )
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(enable=["review"], sections="[section.review]\nweeks_per_page = 12.5\n"),
            source="float.toml",
        )


def test_weeks_per_page_zero_rejected():
    with pytest.raises(ConfigError, match="weeks_per_page"):
        parse_toml(
            _minimal(enable=["review"], sections="[section.review]\nweeks_per_page = 0\n"),
            source="zero.toml",
        )


def test_unknown_key_on_section_review_raises():
    with pytest.raises(ConfigError, match="unknown key: section.review.foo"):
        parse_toml(
            _minimal(enable=["review"], sections="[section.review]\nfoo = 1\n"),
            source="foo.toml",
        )


def test_nomad_ships_review_after_habits():
    dto = load(NOMAD)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-5:] == ["habits", "review", "tasks", "meetings", "colophon"]
    review = next(s for s in dto["planner"]["sections"] if s["name"] == "review")
    assert review["params"]["weeks_per_page"] == 13
    assert review["params"]["pattern"] == "lined"
    assert "pattern" not in NOMAD.read_text(encoding="utf-8").split("[section.habits]")[-1]


def test_short_january_review_compiles(tmp_path):
    dto = parse_toml(_minimal(enable=["review"], sections=""), source="compile.toml")
    typst = _generate(short_january(dto))
    pdf, stderr = compile_pdf(typst, tmp_path / "review")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_tiny_annual_review_compiles(tmp_path):
    dto = parse_toml(
        _minimal(
            enable=["annual", "review"],
            sections="""[section.annual]
show_month_name = true
""",
        ),
        source="tiny-review.toml",
    )
    typst = _generate(short_january(dto))
    pdf, stderr = compile_pdf(typst, tmp_path / "tiny-review")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_range_helper_matches_locale_short_months():
    dto = parse_toml(_minimal(enable=["review"], sections=""), source="helper.toml")
    review = _review(short_january(dto))
    weeks = review._weeks()
    assert len(weeks) == 5
    assert review.range_label(weeks[0].days()[0], weeks[0].days()[-1]) == f"Dec 29 {_EN_DASH} Jan 4"
    assert review.range_label(weeks[1].days()[0], weeks[1].days()[-1]) == f"Jan 5 {_EN_DASH} 11"
    assert review.range_label(weeks[4].days()[0], weeks[4].days()[-1]) == f"Jan 26 {_EN_DASH} Feb 1"


def test_chunks_pack_53_weeks_as_13_13_13_14():
    dto = parse_toml(_minimal(enable=["review"], sections=""), source="pack.toml")
    review = _review(dto)
    weeks = review._weeks()
    assert len(weeks) == 53
    assert review._page_sizes(53) == [13, 13, 13, 14]
    chunks = review._chunks(weeks)
    assert [len(c) for c in chunks] == [13, 13, 13, 14]
    assert [w.number for w in chunks[-1]] == list(range(40, 54))
    assert review._index_count(53) == 4


def test_short_index_keeps_13_row_height():
    dto = parse_toml(_minimal(enable=["review"], sections=""), source="short-height.toml")
    typst = _generate(short_january(dto))
    index = _index_page(typst)
    assert "rows: (5fr, 8fr)" in index
    assert "columns: (2em, 1fr)" in index


def test_page_sizes_absorb_only_when_previous_stays_at_most_14():
    dto = parse_toml(
        _minimal(enable=["review"], sections="[section.review]\nweeks_per_page = 20\n"),
        source="leftover.toml",
    )
    review = _review(dto)
    assert review.weeks_per_page == 20
    assert review._page_sizes(21) == [20, 1]
    assert review._page_sizes(53) == [20, 20, 13]
    two = _review(
        parse_toml(
            _minimal(enable=["review"], sections="[section.review]\nweeks_per_page = 2\n"),
            source="two.toml",
        )
    )
    assert two._page_sizes(5) == [2, 3]


def test_house_dotted_does_not_flip_review_from_lined():
    style = """[style]
scratch_pad = "dotted"

[style.stroke]
regular = "0.3pt"
thick = "0.6pt"

[style.type]
body = "8pt"
h1 = "8mm"


[style.gutter]
column = "8pt"
"""
    dto = parse_toml(
        _minimal(enable=["review"], style=style, sections=""),
        source="house-dotted.toml",
    )
    assert dto["planner"]["params"]["scratch_pad"] == "dotted"
    assert dto["planner"]["sections"][0]["params"]["pattern"] == "lined"
    typst = _generate(short_january(dto))
    week = _week_page(typst, "2026W01")
    assert "rect_pattern(review_lined)" in week
    assert "rect_pattern(lined)" not in week
    assert "rect_pattern(dotted)" not in week


def test_review_pattern_dotted_uses_house_dotted_tiling():
    dto = parse_toml(
        _minimal(enable=["review"], sections='[section.review]\npattern = "dotted"\n'),
        source="dotted.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["pattern"] == "dotted"
    typst = _generate(short_january(dto))
    week = _week_page(typst, "2026W01")
    assert "rect_pattern(dotted)" in week
    assert "review_lined" not in week
    assert "rect_pattern(review_lined)" not in week
    assert "rect_pattern(lined)" not in week
    index = _index_page(typst)
    assert "review_lined" not in index
    assert "rect_pattern(review_lined)" not in index


def test_review_invalid_pattern_rejected():
    with pytest.raises(ConfigError, match="unknown"):
        parse_toml(
            _minimal(enable=["review"], sections='[section.review]\npattern = "grid"\n'),
            source="grid.toml",
        )


def test_contents_mark_on_review_when_index_on():
    dto = parse_toml(
        _minimal(enable=["index", "review"], sections=""),
        source="mark.toml",
    )
    typst = _generate(short_january(dto))
    index = _index_page(typst)
    week = _week_page(typst, "2026W01")
    assert _TRAIL_MARK in index
    assert _TRAIL_MARK in week
    assert index.count(_MARK_RULE) == 1
    assert week.count(_MARK_RULE) == 1
    for page in (index, week):
        assert "column-gutter: 6pt" not in page
        assert "columns: (auto, auto)" not in page
        assert "2026 /" not in page
        assert "text(size: h1)[/]" not in page
        assert "padded_link(<annual>)" not in page
    assert "text(size: h1, [Review <review>])" in index
    assert "padded_link(<review>)" in week
    assert "[Review <review>]" in index
    assert _LEAD_PAIR in index
    assert _FOLLOW_SPACING in index
    assert _SEAT_RTL not in index
    assert "trail_heading(" not in index
    assert index.index(_TRAIL_MARK) < index.index("[Review <review>]")
    assert "padded_link(<review>)" in week
    assert _LEAD_PAIR in week
    assert _FOLLOW_SPACING in week
    assert _SEAT_RTL not in week
    assert "trail_heading(" not in week
    contents = next(p for p in _pages(typst) if 'weight: "bold")[Contents <index>]' in p)
    assert "padded_link(<index>" not in contents
    assert "padded_link(<review>" in contents
    review = _review(dto)
    manifest = Manifest()
    review.register(manifest)
    for page in review.pages(manifest):
        assert page.heading_mark is HeadingMark.LEAD
        assert page.raw_typst is True

