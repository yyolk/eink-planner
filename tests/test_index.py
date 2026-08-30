"""Optional Contents page (section key ``index``) and back-link mark."""

from __future__ import annotations

import typing

import pytest

from parch.compose.page_data import HeadingMark
from parch.config import load
from parch.services.config_file import CANONICAL_SECTIONS
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.test_toml_omit_sections import compile_pdf
from tests.toml_fixtures import _minimal, omit_toml_sections, short_january
from tests.helpers import base_config, load_default

NOMAD = base_config("supernote-nomad")
NOMAD_MOS_RIGHT = base_config("supernote-nomad-mos-right")

_TOC_TITLE = 'weight: "bold")[Contents <index>]'
_MARK_RULE = "line(length: 0.844em, stroke: thick_stroke + black)"
_MARK_LINK = "padded_link(<index>"
_MARK_FLUSH = "padded_link(padding: 0pt, <index>"
_SEATED_TRAIL = "box(height: band, align(horizon + left, seated_"
_SEATED_TITLE = "let seated_title ="
_SEATED_MARK = "let seated_mark ="
_SEAT_RTL = "dir: rtl,\n    spacing: 1fr,"
_SEAT_LTR = "dir: ltr,\n    spacing: 1fr,"


def _generate(dto) -> str:
    return Generate(i18n=load_default()).generate(dto)


def _pages(typst: str) -> list[str]:
    return typst.split("#pagebreak()")


def _contents_page(typst: str) -> str:
    for page in _pages(typst):
        if _TOC_TITLE in page:
            return page
    raise AssertionError("no Contents page")


def _cover_page(typst: str) -> str:
    return _pages(typst)[0]


def _annual_page(typst: str) -> str:
    for page in _pages(typst):
        if "2026<annual>" in page:
            return page
    raise AssertionError("no Annual page")


def _colophon_page(typst: str) -> str:
    for page in reversed(_pages(typst)):
        if "[*Device*]" in page and "[*Year*]" in page:
            return page
    raise AssertionError("no Colophon page")


def _slim_text() -> str:
    return omit_toml_sections(
        NOMAD.read_text(encoding="utf-8"),
        [
            "quarterly",
            "monthly",
            "weekly",
            "daily",
            "daily_notes",
            "projects",
            "habits",
            "review",
            "tasks",
            "meetings",
        ],
    )


def test_canonical_sections_starts_with_cover_index():
    assert CANONICAL_SECTIONS[0] == "cover"
    assert CANONICAL_SECTIONS[1] == "index"
    assert CANONICAL_SECTIONS[2] == "annual"


def test_listed_without_table_defaults():
    dto = parse_toml(_minimal(enable=["index"], sections=""), source="default-index.toml")
    section = dto["planner"]["sections"][0]
    assert section["name"] == "index"
    assert section["class"] == "index"
    assert section["params"].to_plain() == {}


def test_contents_lists_enabled_human_names_in_sections_order():
    typst = _generate(load(NOMAD))
    page = _contents_page(typst)
    assert _TOC_TITLE in page
    names = [
        "Calendar",
        "Quarters",
        "Months",
        "Weeks",
        "Days",
        "Projects",
        "Habits",
        "Review",
        "Tasks",
        "Meetings",
        "About this notebook",
    ]
    positions = [page.index(name) for name in names]
    assert positions == sorted(positions)
    assert "Cover" not in page
    assert page.count("Contents") == 1
    assert "daily_notes" not in page
    assert "Notes" not in page
    assert "stroke:" not in page
    assert "2 * regular_height" not in page
    for dest in (
        "annual",
        "quarter-2026-1",
        "month-2026-01-01",
        "2026W01",
        "2026-01-01",
        "projects",
        "habits",
        "review",
        "tasks",
        "meetings",
        "colophon",
    ):
        assert f"padded_link(<{dest}>" in page


def test_slim_lists_calendar_and_about_only():
    dto = parse_toml(_slim_text(), source="slim.toml")
    typst = _generate(dto)
    page = _contents_page(typst)
    assert "Calendar" in page
    assert "About this notebook" in page
    assert page.index("Calendar") < page.index("About this notebook")
    assert "padded_link(<annual>" in page
    assert "padded_link(<colophon>" in page
    for name in ("Quarters", "Months", "Weeks", "Days", "Projects", "Habits", "Review", "Tasks", "Meetings"):
        assert name not in page
    assert "Cover" not in page


def test_fullish_list_includes_all_enabled_sections():
    typst = _generate(load(NOMAD))
    page = _contents_page(typst)
    for name in (
        "Quarters",
        "Months",
        "Weeks",
        "Days",
        "Projects",
        "Habits",
        "Review",
        "Tasks",
        "Meetings",
    ):
        assert name in page


def test_omit_index_has_no_contents_and_no_mark():
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), ["index"])
    dto = parse_toml(text, source="no-index.toml")
    typst = _generate(dto)
    assert _TOC_TITLE not in typst
    assert "[Contents <index>]" not in typst
    assert _MARK_LINK not in typst
    assert _MARK_RULE not in typst
    names = [s["name"] for s in dto["planner"]["sections"]]
    assert "index" not in names


def test_index_on_cover_has_no_mark():
    typst = _generate(load(NOMAD))
    cover = _cover_page(typst)
    assert _MARK_RULE not in cover
    assert _MARK_FLUSH not in cover
    assert "padded_link(<index>," not in cover
    assert "padded_link(<index>)[2026]" in cover


def test_contents_page_has_no_back_link_mark():
    typst = _generate(load(NOMAD))
    page = _contents_page(typst)
    assert _TOC_TITLE in page
    assert _MARK_LINK not in page
    assert _MARK_RULE not in page


def test_annual_has_no_calendar_chip_and_links_to_index():
    typst = _generate(load(NOMAD))
    page = _annual_page(typst)
    assert "padded_link(<annual>, [Calendar])" not in page
    assert "[Calendar]" not in page
    assert "grid.cell(fill: black, text(white)[#padded_link(<annual>, [Calendar])])" not in page
    assert "2026<annual>" in page
    assert _MARK_FLUSH in page
    assert _MARK_RULE in page
    assert page.count(_MARK_RULE) == 5


def test_colophon_has_mark_and_unchanged_facts():
    typst = _generate(load(NOMAD))
    page = _colophon_page(typst)
    assert _MARK_LINK in page
    assert _MARK_RULE in page
    assert page.index("columns: (auto, auto)") < page.index(_MARK_LINK)
    assert page.index(_MARK_LINK) < page.index("[About this notebook <colophon>]")
    assert "[*Device*]" in page
    assert "[*Year*]" in page
    assert "[*Version*]" in page
    assert "<colophon>" in page
    assert "Calendar" not in page or "padded_link(<annual>, [Calendar])" not in page


def test_slim_compiles(tmp_path):
    dto = short_january(parse_toml(_slim_text(), source="slim-compile.toml"))
    typst = _generate(dto)
    pdf, stderr = compile_pdf(typst, tmp_path / "slim")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr
    page = _contents_page(typst)
    assert "Calendar" in page
    assert "About this notebook" in page


def test_mos_right_mark_sits_next_to_strip():
    typst = _generate(load(NOMAD_MOS_RIGHT))
    page = _annual_page(typst)
    title_at = page.index("2026<annual>")
    mark_at = page.index(_MARK_FLUSH)
    assert title_at < mark_at
    assert "padded_link(<annual>, [Calendar])" not in page
    assert "[Calendar]" not in page
    for label in ("Q1", "Q2", "Q3", "Q4"):
        assert label in page
    assert page.count(_MARK_RULE) == 5


def test_mos_left_annual_mark_is_trail_strip_sibling():
    typst = _generate(load(NOMAD))
    page = _annual_page(typst)
    title_at = page.index("2026<annual>")
    mark_at = page.index(_MARK_FLUSH)
    assert title_at < mark_at
    heading = page[page.index(_SEATED_TITLE) : page.index(_SEATED_MARK)]
    assert "2026<annual>" in heading
    assert "columns: (auto, auto)" not in heading
    assert _SEAT_RTL in page
    assert _SEATED_TRAIL in page
    assert "padded_link(<annual>, [Calendar])" not in page
    assert "[Calendar]" not in page
    for label in ("Q1", "Q2", "Q3", "Q4"):
        assert label in page
    assert page.count(_MARK_RULE) == 5


def test_daily_mark_is_trail_strip_alone():
    typst = _generate(load(NOMAD))
    page = next(p for p in _pages(typst) if "1 <2026-01-01>" in p)
    title_at = page.index("1 <2026-01-01>")
    mark_at = page.index(_MARK_FLUSH)
    trail_at = page.index("pad(right: 3mm")
    assert title_at < trail_at <= mark_at
    heading = page[page.index(_SEATED_TITLE) : page.index(_SEATED_MARK)]
    assert "1 <2026-01-01>" in heading
    assert _SEAT_RTL in page
    assert _SEATED_TRAIL in page
    assert "column-gutter: 6pt" not in heading
    assert "padded_link(<annual>, [2026])" not in page
    assert page.count(_MARK_RULE) == 5


def test_mos_right_daily_mark_is_trail_strip_alone():
    typst = _generate(load(NOMAD_MOS_RIGHT))
    page = next(p for p in _pages(typst) if "1 <2026-01-01>" in p)
    title_at = page.index("1 <2026-01-01>")
    mark_at = page.index(_MARK_FLUSH)
    trail_at = page.index("pad(right: 3mm")
    assert title_at < trail_at <= mark_at
    heading = page[page.index(_SEATED_TITLE) : page.index(_SEATED_MARK)]
    assert "1 <2026-01-01>" in heading
    assert _SEAT_LTR in page
    assert _SEATED_TRAIL in page
    assert "column-gutter: 6pt" not in heading
    assert "padded_link(<annual>, [2026])" not in page
    assert page.count(_MARK_RULE) == 5


def test_mos_right_habits_mark_sits_next_to_strip():
    typst = _generate(load(NOMAD_MOS_RIGHT))
    page = next(p for p in _pages(typst) if "January<habits-january>" in p)
    title_at = page.index("January<habits-january>")
    mark_at = page.index(_MARK_FLUSH)
    strip_at = page.index("rowspan: 2")
    assert title_at < mark_at < strip_at
    assert page[mark_at:strip_at].count("padded_link") == 1
    assert _SEATED_TRAIL in page


def test_builder_trail_and_raw_headings_call_trail_heading():
    import inspect

    from parch.mos.builder import Builder
    from parch.mos.contents_mark import trail_heading
    from parch.sections.colophon import Colophon
    from parch.sections.habits import Habits
    from parch.sections.meetings import Meetings
    from parch.sections.projects import Projects
    from parch.sections.tasks import Tasks

    helper = inspect.getsource(trail_heading)
    assert "box(height: band, align(horizon + left, seated_title))" in helper
    assert "box(height: band, align(horizon + left, seated_mark))" in helper
    assert "trail_strip(" in helper
    assert "edge is HeadingMark.FOLLOW" in helper
    assert "edge is HeadingMark.TRAIL" in helper
    assert typing.get_type_hints(trail_heading)["edge"] is HeadingMark
    builder = inspect.getsource(Builder._heading_stack)
    assert "trail_heading(" in builder
    assert "trail_strip(" not in builder
    assert "edge=HeadingMark.FOLLOW" in builder
    assert "edge=HeadingMark.TRAIL" in builder
    for cls in (Habits, Tasks, Meetings, Projects, Colophon):
        heading = inspect.getsource(cls._heading)
        assert "trail_heading(" in heading
        assert "edge=HeadingMark.FOLLOW" in heading
        assert "lead_title" not in heading
        assert "heading_mark=HeadingMark.FOLLOW" not in inspect.getsource(cls.pages)
        assert "stack(" not in heading
        assert "trail_strip(" not in heading


def test_trail_heading_rejects_string_edge_fallthrough():
    from parch.mos.contents_mark import trail_heading
    from parch.mos.manifest import Manifest

    manifest = Manifest()
    manifest.register_source("index")
    follow = trail_heading(
        manifest, "h1", "text(size: h1)[Tasks]", edge=HeadingMark.FOLLOW,
    )
    assert "spacing: 0.5em" in follow
    assert "spacing: 1fr" not in follow
    trail = trail_heading(
        manifest, "h1", "text(size: h1)[Tasks]", edge=HeadingMark.TRAIL,
    )
    assert "spacing: 1fr" in trail
    for bad in ("follow", "trail", "FOLLOW", HeadingMark.LEAD):
        with pytest.raises(ValueError, match="TRAIL or FOLLOW"):
            trail_heading(manifest, "h1", "text(size: h1)[Tasks]", edge=bad)
