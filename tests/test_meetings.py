"""Meetings index + per-meeting notes pages."""

import pytest

from parch import ConfigError
from parch.config import load
from parch.mos.configurator import Configurator
from parch.compose.page_data import HeadingMark
from parch.mos.manifest import Manifest
from parch.sections.meetings import Meetings, _NUM_COL
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.test_toml_omit_sections import _LABEL_DEF, _PADDED_LINK, compile_pdf
from tests.toml_fixtures import _minimal, short_january
from tests.helpers import base_config, load_default

NOMAD = base_config("supernote-nomad")

_NOMAD_DEVICE = """[device]
name = "supernote-nomad"
ppi = 300"""

_MARK_RULE = "contents_bars(size:"
_TRAIL_MARK = "padded_link(padding: 0pt, <index>"
_LEAD_PAIR = "lead_pair("
_SEAT_RTL = "spacing: 1fr, direction: rtl"
_FOLLOW_SPACING = "spacing: 0.5em"
_TICK_STROKE = "stroke: (_, _) => (bottom: regular_stroke + black)"


def _generate(dto) -> str:
    return Generate(i18n=load_default()).generate(dto)


def _meetings(dto, index_pages: int | None = None) -> Meetings:
    params = {}
    for section in dto["planner"]["sections"]:
        if section.get("class") == "meetings" or section.get("name") == "meetings":
            params = dict(section.get("params") or {})
            break
    if index_pages is not None:
        params["index_pages"] = index_pages
    return Meetings(
        section_name="meetings",
        i18n=load_default(),
        configurator=Configurator(dto),
        index_pages=params.get("index_pages", Meetings.DEFAULT_INDEX_PAGES),
    )


def _pages(typst: str) -> list[str]:
    return typst.split("#pagebreak()")


def _index_page(typst: str, page_id: str = "meetings") -> str:
    needle = f"[Meetings <{page_id}>]"
    for page in _pages(typst):
        if needle in page:
            return page
    raise AssertionError(f"no Meetings index page {page_id}")


def _meeting_page(typst: str, index: int = 1) -> str:
    marker = f"#[] <meeting-{index}>"
    for page in _pages(typst):
        if marker in page:
            return page
    raise AssertionError(f"no meeting page {index}")


def test_omit_index_pages_defaults_to_one_full_index():
    dto = parse_toml(_minimal(enable=["meetings"], sections=""), source="default-index-pages.toml")
    section = dto["planner"]["sections"][0]
    assert section["name"] == "meetings"
    assert section["class"] == "meetings"
    assert section["params"]["index_pages"] == 1
    meetings = _meetings(dto)
    assert Meetings.DEFAULT_INDEX_PAGES == 1
    rpp = meetings.rows_per_index_page()
    n = meetings.pages_num
    assert rpp >= 1
    assert meetings.index_page_count() == 1
    assert n == rpp
    typst = _generate(dto)
    assert "<meetings>" in typst
    for i in range(1, n + 1):
        assert f"<meeting-{i}>" in typst
    assert f"<meeting-{n + 1}>" not in typst
    assert typst.count("#pagebreak()") == n
    assert "rows: (" + ", ".join(["1fr"] * n) + ")" in typst
    assert "2 * regular_height" not in typst
    assert "→" not in typst


def test_index_row_is_the_meeting_link():
    dto = parse_toml(
        _minimal(
            enable=["annual", "meetings"],
            sections="""[section.annual]
show_month_name = true

[section.meetings]
index_pages = 1
""",
        ),
        source="links.toml",
    )
    meetings = _meetings(dto)
    n = meetings.pages_num
    typst = _generate(dto)
    index = _index_page(typst)
    assert "→" not in index
    assert f"columns: ({_NUM_COL}, 1fr)" in index
    assert "rows: (" + ", ".join(["1fr"] * n) + ")" in index
    for i in (1, n):
        assert f"padded_link(<meeting-{i}>, box(width: 100%, height: 100%" in index
        assert f"padded_link(<meeting-{i}>, [])" not in index
        assert f"padded_link(<meeting-{i}>)[]" not in index
    assert "padded_link(<meetings>)" in typst
    assert "padded_link(<annual>)" not in index
    labels = set(_LABEL_DEF.findall(typst))
    links = set(_PADDED_LINK.findall(typst))
    expected = {"meetings"} | {f"meeting-{i}" for i in range(1, n + 1)}
    assert expected <= labels
    assert expected <= links


def test_no_arrows_title_date_assigned_due_or_mos():
    dto = parse_toml(
        _minimal(enable=["meetings"], sections="[section.meetings]\nindex_pages = 1\n"),
        source="chrome.toml",
    )
    typst = _generate(dto)
    meeting = _meeting_page(typst)
    assert "→" not in typst
    assert "TITLE" not in typst
    assert "DATE" not in typst
    assert "Assigned" not in typst
    assert "Due" not in typst
    assert "side_menu" not in meeting
    assert "rotate(" not in meeting
    assert "grid.cell(fill: black" not in meeting


def test_header_is_meetings_without_year():
    dto = parse_toml(
        _minimal(
            enable=["annual", "meetings"],
            sections="""[section.annual]
show_month_name = true

[section.meetings]
index_pages = 1
""",
        ),
        source="header.toml",
    )
    typst = _generate(dto)
    index = _index_page(typst)
    meeting = _meeting_page(typst)
    for page in (index, meeting):
        assert "padded_link(<annual>)" not in page
        assert "2026 /" not in page
        assert "text(size: h1)[/]" not in page
        assert "1/16" not in page
    assert "text(size: h1, [Meetings <meetings>])" in index
    assert "padded_link(<meetings>)" in meeting
    assert "padded_link(<meetings-2>)" not in meeting
    assert "text(size: 0.85em)[1]" in meeting
    assert "#[] <meeting-1>" in meeting


def test_header_is_meetings_when_annual_omitted():
    dto = parse_toml(_minimal(enable=["meetings"], sections="[section.meetings]\nindex_pages = 1\n"), source="no-annual.toml")
    typst = _generate(dto)
    index = _index_page(typst)
    meeting = _meeting_page(typst)
    for page in (index, meeting):
        assert "padded_link(<annual>)" not in page
        assert "2026 /" not in page
        assert "text(size: h1)[/]" not in page
        assert "pad(right: 3mm" not in page
        assert "padded_link(<index>" not in page
        assert "columns: (auto, auto)" not in page
    assert "column-gutter: 6pt" not in index
    assert "text(size: h1, [Meetings <meetings>])" in index
    assert "stack(" not in index
    assert "padded_link(<meetings>)" in meeting
    assert "<meetings>" in typst


def test_locale_strings_and_line_counts():
    dto = parse_toml(
        _minimal(enable=["meetings"], sections="[section.meetings]\nindex_pages = 1\n"),
        source="strings.toml",
    )
    typst = _generate(dto)
    for label in ("Meetings", "Topics", "Notes", "Action items"):
        assert label in typst
    assert "TITLE" not in typst
    assert "DATE" not in typst
    assert "Assigned to" not in typst
    assert "Due by" not in typst
    assert "rows: (" + ", ".join(["regular_height"] * 4) + ")" in typst
    assert "rows: (" + ", ".join(["regular_height"] * 5) + ")" in typst
    assert "rect_pattern(dotted)" in typst
    assert "rect_pattern(review_lined)" not in typst
    assert "#let review_lined =" not in typst
    meeting = _meeting_page(typst)
    assert meeting.count("rows: (" + ", ".join(["regular_height"] * 4) + ")") == 1
    assert meeting.count("rows: (" + ", ".join(["regular_height"] * 5) + ")") == 1
    assert meeting.count("rect_pattern(dotted)") == 1
    assert "$square.stroked$" in meeting
    assert meeting.count("$square.stroked$") == 9
    assert _TICK_STROKE in meeting
    assert "columns: (regular_height, 1fr)" not in meeting
    assert "stroke: regular_stroke + black" not in meeting
    assert "1/16" not in meeting
    assert "text(size: 0.85em)[1]" in meeting


def test_unknown_key_on_section_meetings_raises():
    with pytest.raises(ConfigError, match="unknown key: section.meetings.pattern"):
        parse_toml(
            _minimal(enable=["meetings"], sections="[section.meetings]\nindex_pages = 1\npattern = \"dotted\"\n"),
            source="extra.toml",
        )
    with pytest.raises(ConfigError, match="unknown key: section.meetings.foo"):
        parse_toml(
            _minimal(enable=["meetings"], sections="[section.meetings]\nfoo = 1\n"),
            source="foo.toml",
        )


def test_index_pages_bool_and_float_rejected():
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(enable=["meetings"], sections="[section.meetings]\nindex_pages = true\n"),
            source="bool.toml",
        )
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(enable=["meetings"], sections="[section.meetings]\nindex_pages = 3.5\n"),
            source="float.toml",
        )


def test_index_pages_zero_rejected():
    with pytest.raises(ConfigError, match="index_pages"):
        parse_toml(
            _minimal(enable=["meetings"], sections="[section.meetings]\nindex_pages = 0\n"),
            source="zero.toml",
        )


def test_pages_key_is_unknown():
    with pytest.raises(ConfigError, match="unknown key: section.meetings.pages"):
        parse_toml(
            _minimal(enable=["meetings"], sections="[section.meetings]\npages = 16\n"),
            source="pages-unknown.toml",
        )


def test_pages_are_raw_typst_without_mos_chrome():
    dto = parse_toml(
        _minimal(enable=["meetings"], sections="[section.meetings]\nindex_pages = 1\n"),
        source="raw.toml",
    )
    typst = _generate(dto)
    assert "side_menu" not in typst
    assert "rotate(" not in typst
    assert "<meetings>" in typst
    assert "<meeting-1>" in typst


def test_index_pages_two_is_two_full_stretched_indexes():
    slim = parse_toml(
        _minimal(
            device=_NOMAD_DEVICE,
            enable=["meetings"],
            sections="""[section.meetings]
index_pages = 2
""",
        ),
        source="index-pages-2.toml",
    )
    meetings = _meetings(slim)
    assert meetings.rows_per_index_page() == 16
    assert meetings.index_page_count() == 2
    assert meetings.pages_num == 32
    typst = _generate(slim)
    assert "<meetings>" in typst
    assert "<meetings-2>" in typst
    assert "<meeting-32>" in typst
    assert "<meeting-33>" not in typst
    full = "rows: (" + ", ".join(["1fr"] * 16) + ")"
    leftover = "rows: (" + ", ".join(["2 * regular_height"] * 4) + ")"
    assert full in typst
    assert leftover not in typst
    assert typst.count(full) == 2
    pages = _pages(typst)
    first = next(page for page in pages if "<meetings>" in page and "<meetings-2>" not in page)
    second = next(page for page in pages if "<meetings-2>" in page)
    assert full in first
    assert full in second
    assert leftover not in first
    assert leftover not in second
    assert "→" not in second
    board_late = _meeting_page(typst, 17)
    assert "padded_link(<meetings-2>)" in board_late
    assert "padded_link(<meetings>)" not in board_late
    assert "text(size: 0.85em)[17]" in board_late
    assert "17/32" not in board_late
    first_meeting = _meeting_page(typst, 1)
    assert "padded_link(<meetings>)" in first_meeting
    assert "padded_link(<meetings-2>)" not in first_meeting
    assert "text(size: 0.85em)[1]" in first_meeting
    assert "1/32" not in first_meeting
    assert typst.count("2 * regular_height") == 0


def test_nomad_default_is_one_index_page():
    dto = load(NOMAD)
    meetings = _meetings(dto)
    assert meetings.pages_num == 16
    assert meetings.rows_per_index_page() == 16
    assert meetings.index_page_count() == 1
    typst = _generate(short_january(dto))
    assert "<meetings>" in typst
    assert "<meetings-2>" not in typst
    assert "<meeting-1>" in typst
    assert "<meeting-16>" in typst
    assert "<meeting-17>" not in typst
    index = _index_page(typst)
    meeting = _meeting_page(typst)
    assert "→" not in index
    assert f"columns: ({_NUM_COL}, 1fr)" in index
    assert "rows: (" + ", ".join(["1fr"] * 16) + ")" in index
    assert "2 * regular_height" not in index
    assert "padded_link(<annual>)" not in index
    assert "padded_link(<annual>)" not in meeting
    assert "2026 /" not in index
    assert "2026 /" not in meeting
    assert "1/16" not in meeting
    assert "text(size: 0.85em)[1]" in meeting
    assert (
        "padded_link(<meeting-1>, box(width: 100%, height: 100%"
        in index
    )


def test_contents_mark_on_meetings_when_index_on():
    dto = parse_toml(
        _minimal(enable=["index", "meetings"], sections=""),
        source="mark.toml",
    )
    typst = _generate(dto)
    index = _index_page(typst)
    meeting = _meeting_page(typst)
    assert _TRAIL_MARK in index
    assert _TRAIL_MARK in meeting
    assert index.count(_MARK_RULE) == 1
    assert meeting.count(_MARK_RULE) == 1
    for page in (index, meeting):
        assert "columns: (auto, auto)" not in page
        assert "2026 /" not in page
        assert "text(size: h1)[/]" not in page
        assert "padded_link(<annual>)" not in page
    assert "column-gutter: 6pt" not in index
    assert "text(size: h1, [Meetings <meetings>])" in index
    assert "padded_link(<meetings>)" in meeting
    assert "[Meetings <meetings>]" in index
    assert _LEAD_PAIR in index
    assert _FOLLOW_SPACING in index
    assert _SEAT_RTL not in index
    assert "trail_heading(" not in index
    assert index.index(_TRAIL_MARK) < index.index("[Meetings <meetings>]")
    assert "padded_link(<meetings>)" in meeting
    assert _LEAD_PAIR in meeting
    assert _FOLLOW_SPACING in meeting
    assert _SEAT_RTL not in meeting
    assert "trail_heading(" not in meeting
    meetings = _meetings(dto)
    manifest = Manifest()
    meetings.register(manifest)
    for page in meetings.pages(manifest):
        assert page.heading_mark is HeadingMark.LEAD
        assert page.raw_typst is True
    contents = next(p for p in _pages(typst) if 'weight: "bold")[Contents <index>]' in p)
    assert "padded_link(<index>" not in contents
    assert "padded_link(<meetings>" in contents


def test_tiny_cover_annual_meetings_compiles(tmp_path):
    dto = parse_toml(
        _minimal(
            enable=["cover", "annual", "meetings"],
            sections="""[section.cover]
title = "Hi"
font_size = "12pt"

[section.annual]
show_month_name = true

[section.meetings]
index_pages = 1
""",
        ),
        source="tiny.toml",
    )
    typst = _generate(dto)
    pdf, stderr = compile_pdf(typst, tmp_path / "tiny-meetings")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_nomad_parses_and_compiles(tmp_path):
    dto = load(NOMAD)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert "meetings" in names
    meetings = next(s for s in dto["planner"]["sections"] if s["name"] == "meetings")
    assert meetings["params"]["index_pages"] == 1
    typst = _generate(short_january(dto))
    assert "<meetings>" in typst
    assert "<meeting-1>" in typst
    assert "<meeting-16>" in typst
    pdf, stderr = compile_pdf(typst, tmp_path / "nomad-meetings")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr
