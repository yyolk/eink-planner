"""Optional Contents page (section key ``index``) and back-link mark."""

import annotationlib

import pytest

from parch.compose.page_data import HeadingMark
from parch.config import load
from parch.services.config_file import CANONICAL_SECTIONS
from parch.services.generate import Generate
from parch.toml_config import apply_hand, parse_toml
from tests.test_toml_omit_sections import compile_pdf
from tests.toml_fixtures import _minimal, omit_toml_sections, short_january
from tests.helpers import base_config, load_default

NOMAD = base_config("supernote-nomad")
NOMAD_EXTRAS = base_config("supernote-nomad", extras=True)

_TOC_TITLE = 'weight: "bold")[Contents <index>]'
_MARK_RULE = "contents_bars(size:"
_MARK_LINK = "padded_link(<index>"
_MARK_FLUSH = "padded_link(padding: 0pt, <index>"
_TRAIL_HEADING = "trail_heading("
_LEAD_PAIR = "lead_pair("
_FOLLOW_PAIR = "lead_pair("
_FOLLOW_SPACING = "spacing: 0.5em"


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
        "colophon",
    ):
        assert f"padded_link(<{dest}>" in page
    for extra in ("Projects", "Habits", "Review", "Tasks", "Meetings"):
        assert extra not in page


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
    typst = _generate(load(NOMAD_EXTRAS))
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


def test_contents_mark_emits_contents_bars_call():
    from parch.mos.contents_mark import contents_mark
    from parch.mos.manifest import Manifest

    assert contents_mark(None, "h1") == ""
    off = Manifest()
    assert contents_mark(off, "h1") == ""
    manifest = Manifest()
    manifest.register_source("index")
    assert contents_mark(manifest, "h1") == (
        "padded_link(<index>, contents_bars(size: h1))"
    )
    assert contents_mark(manifest, "h1", link_padding="0pt") == (
        "padded_link(padding: 0pt, <index>, contents_bars(size: h1))"
    )


def test_lead_title_emits_lead_pair_or_title():
    from parch.mos.contents_mark import lead_title
    from parch.mos.manifest import Manifest

    title = "text(size: h1)[January]"
    assert lead_title(None, "h1", title) == title
    off = Manifest()
    assert lead_title(off, "h1", title) == title
    manifest = Manifest()
    manifest.register_source("index")
    assert lead_title(manifest, "h1", title) == (
        f"lead_pair(padded_link(<index>, contents_bars(size: h1)), {title})"
    )
    assert "grid(" not in lead_title(manifest, "h1", title)
    assert "columns: (auto, auto)" not in lead_title(manifest, "h1", title)


def test_trail_strip_emits_lead_pair_or_mark():
    from parch.mos.contents_mark import trail_strip
    from parch.mos.manifest import Manifest

    assert trail_strip(None, "h1") is None
    off = Manifest()
    assert trail_strip(off, "h1") is None
    manifest = Manifest()
    manifest.register_source("index")
    mark = "padded_link(padding: 0pt, <index>, contents_bars(size: h1))"
    assert trail_strip(manifest, "h1") == mark
    assert "pad(right: 3mm" not in trail_strip(manifest, "h1")
    chip = "text[Q1]"
    assert trail_strip(manifest, "h1", chip=chip) == (
        f"lead_pair(padded_link(<index>, contents_bars(size: h1)), {chip})"
    )
    assert trail_strip(None, "h1", chip=chip) == chip


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
    assert page.count(_MARK_RULE) == 1


def test_colophon_has_mark_and_unchanged_facts():
    typst = _generate(load(NOMAD))
    page = _colophon_page(typst)
    assert _MARK_FLUSH in page
    assert _MARK_RULE in page
    assert page.count(_MARK_RULE) == 1
    assert _FOLLOW_SPACING in page
    assert _FOLLOW_PAIR in page
    assert _TRAIL_HEADING not in page
    heading = page[page.index(_LEAD_PAIR) :]
    assert "[About this notebook <colophon>]" in heading
    assert page.index(_MARK_FLUSH) < page.index("[About this notebook <colophon>]")
    assert "column-gutter: 6pt" not in page
    assert "columns: (auto, auto)" not in page
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
    typst = _generate(apply_hand(load(NOMAD), "right"))
    page = _annual_page(typst)
    title_at = page.index("2026<annual>")
    mark_at = page.index(_MARK_FLUSH)
    assert title_at < mark_at
    assert _TRAIL_HEADING in page
    assert "direction:" not in page
    assert "#mos_frame(\n  right," in page
    assert "padded_link(<annual>, [Calendar])" not in page
    assert "[Calendar]" not in page
    for label in ("Q1", "Q2", "Q3", "Q4"):
        assert label in page
    assert page.count(_MARK_RULE) == 1


def test_mos_left_annual_mark_is_trail_strip_sibling():
    typst = _generate(load(NOMAD))
    page = _annual_page(typst)
    title_at = page.index("2026<annual>")
    mark_at = page.index(_MARK_FLUSH)
    assert title_at < mark_at
    heading = page[page.index(_TRAIL_HEADING) : page.index(_MARK_FLUSH)]
    assert "2026<annual>" in heading
    assert "columns: (auto, auto)" not in heading
    assert "direction:" not in heading
    assert "spacing:" not in heading
    assert _TRAIL_HEADING in page
    assert "#mos_frame(" in page
    assert "well_frame(" in page
    assert "rowspan" not in page
    assert "padded_link(<annual>, [Calendar])" not in page
    assert "[Calendar]" not in page
    for label in ("Q1", "Q2", "Q3", "Q4"):
        assert label in page
    assert page.count(_MARK_RULE) == 1


def test_daily_mark_is_trail_strip_alone():
    typst = _generate(load(NOMAD))
    page = next(p for p in _pages(typst) if "1 <2026-01-01>" in p)
    title_at = page.index("1 <2026-01-01>")
    mark_at = page.index(_MARK_FLUSH)
    assert title_at < mark_at
    heading = page[page.index(_TRAIL_HEADING) : page.index(_MARK_FLUSH)]
    assert "1 <2026-01-01>" in heading
    assert "direction:" not in heading
    assert "spacing:" not in heading
    assert _TRAIL_HEADING in page
    assert "pad(right: 3mm" not in page
    assert "column-gutter: 6pt" not in heading
    assert "padded_link(<annual>, [2026])" not in page
    assert page.count(_MARK_RULE) == 1
    assert "#mos_frame(" in page


def test_mos_right_daily_mark_is_trail_strip_alone():
    typst = _generate(apply_hand(load(NOMAD), "right"))
    page = next(p for p in _pages(typst) if "1 <2026-01-01>" in p)
    title_at = page.index("1 <2026-01-01>")
    mark_at = page.index(_MARK_FLUSH)
    assert title_at < mark_at
    heading = page[page.index(_TRAIL_HEADING) : page.index(_MARK_FLUSH)]
    assert "1 <2026-01-01>" in heading
    assert "direction:" not in heading
    assert "spacing:" not in heading
    assert _TRAIL_HEADING in page
    assert "pad(right: 3mm" not in page
    assert "column-gutter: 6pt" not in heading
    assert "padded_link(<annual>, [2026])" not in page
    assert page.count(_MARK_RULE) == 1
    assert "#mos_frame(\n  right," in page


def test_mos_right_habits_mark_sits_next_to_strip():
    typst = _generate(apply_hand(load(NOMAD_EXTRAS), "right"))
    page = next(p for p in _pages(typst) if "January<habits-january>" in p)
    title_at = page.index("January<habits-january>")
    mark_at = page.index(_MARK_FLUSH)
    assert title_at < mark_at
    assert _TRAIL_HEADING in page
    assert "direction:" not in page
    assert "#mos_frame(\n  right," in page
    assert "rowspan: 2" not in page


def test_builder_trail_and_raw_headings_call_trail_heading():
    import inspect

    from parch.mos.builder import Builder
    from parch.mos.contents_mark import trail_heading
    from parch.sections.colophon import Colophon
    from parch.sections.habits import Habits
    from parch.sections.meetings import Meetings
    from parch.sections.projects import Projects
    from parch.sections.review import Review
    from parch.sections.tasks import Tasks

    helper = inspect.getsource(trail_heading)
    assert "trail_heading({title}, {mark})" in helper
    assert "lead_pair({mark}, {title}, spacing: 0.5em)" in helper
    assert "direction" not in helper
    assert "spacing: 1fr" not in helper
    assert "let seated_title" not in helper
    assert "measure(seated_title)" not in helper
    assert "trail_strip(" in helper
    assert "match edge:" in helper
    assert "case HeadingMark.FOLLOW:" in helper
    assert "case HeadingMark.TRAIL:" in helper
    assert annotationlib.get_annotations(trail_heading)["edge"] is HeadingMark
    layout = inspect.getsource(Builder._layout_page)
    assert "mos_frame(" in layout
    assert "well_frame(" in layout
    assert "row.reverse" not in layout
    assert "list(reversed" not in layout
    builder = inspect.getsource(Builder._heading_stack)
    assert "trail_heading(" in builder
    assert "trail_strip(" not in builder
    assert "edge=HeadingMark.FOLLOW" in builder
    assert "edge=HeadingMark.TRAIL" in builder
    assert "if chip:" in builder
    assert "mos_right" not in builder
    assert "match heading_mark:" in builder
    assert builder.index("if chip:") < builder.index("match heading_mark:")
    assert "case HeadingMark.FOLLOW:" in builder
    assert "case HeadingMark.TRAIL:" in builder
    assert "case HeadingMark.LEAD:" in builder
    for cls in (Habits, Tasks, Meetings, Projects, Review, Colophon):
        heading = inspect.getsource(cls._heading)
        assert "trail_heading(" in heading
        assert "edge=HeadingMark.FOLLOW" in heading
        assert "direction" not in heading
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
    assert follow.startswith("lead_pair(")
    assert "spacing: 0.5em" in follow
    assert "spacing: 1fr" not in follow
    assert "direction:" not in follow
    assert "let seated_title" not in follow
    trail = trail_heading(
        manifest, "h1", "text(size: h1)[Tasks]", edge=HeadingMark.TRAIL,
    )
    assert trail.startswith("trail_heading(")
    assert "spacing:" not in trail
    assert "direction:" not in trail
    assert trail_heading(None, "h1", "text(size: h1)[Tasks]") == "text(size: h1)[Tasks]"
    assert trail_heading(manifest, "h1", None) == (
        "padded_link(padding: 0pt, <index>, contents_bars(size: h1))"
    )
    for bad in ("FOLLOW", HeadingMark.LEAD):
        with pytest.raises(ValueError, match="TRAIL or FOLLOW"):
            trail_heading(manifest, "h1", "text(size: h1)[Tasks]", edge=bad)


def test_heading_stack_matches_follow_trail_lead_after_chip_guard():
    from parch.compose.coordinator import Coordinator
    from parch.mos.builder import Builder

    title = "text(size: h1)[Title]"
    dto = load(NOMAD)
    coord = Coordinator(dto, i18n=load_default())
    builder = Builder(
        i18n=coord.i18n, configurator=coord.configurator, manifest=coord.manifest,
    )
    builder.manifest.register_source("index")
    follow = builder._heading_stack(None, title, None, HeadingMark.FOLLOW)
    assert follow.startswith("lead_pair(")
    assert "spacing: 0.5em" in follow
    assert "spacing: 1fr" not in follow
    trail = builder._heading_stack(None, title, None, HeadingMark.TRAIL)
    assert trail.startswith("trail_heading(")
    assert "spacing:" not in trail
    assert "direction:" not in trail
    lead = builder._heading_stack(None, title, None, HeadingMark.LEAD)
    assert _LEAD_PAIR in lead
    assert "columns: (auto, auto)" not in lead
    assert "spacing: 0.5em" not in lead
    assert "spacing: 1fr" not in lead
    assert builder._heading_stack(None, None, None, HeadingMark.LEAD) == ""
    with pytest.raises(ValueError, match="FOLLOW, TRAIL, or LEAD"):
        builder._heading_stack(None, title, None, "nope")
    builder.manifest.register_source("chip-page")
    chipped = builder._heading_stack(
        None, title, [("chip-page", "Chip")], HeadingMark.LEAD,
    )
    assert chipped.startswith("trail_heading(")
    assert "spacing: 1fr" not in chipped
    assert "direction:" not in chipped
    assert _TRAIL_HEADING in chipped
    assert _LEAD_PAIR in chipped

    right = apply_hand(load(NOMAD), "right")
    right_coord = Coordinator(right, i18n=load_default())
    right_builder = Builder(
        i18n=right_coord.i18n,
        configurator=right_coord.configurator,
        manifest=right_coord.manifest,
    )
    right_builder.manifest.register_source("index")
    glued = right_builder._heading_stack(None, title, None, HeadingMark.LEAD)
    assert _LEAD_PAIR in glued
    assert "spacing: 1fr" not in glued
    assert "columns: (auto, auto)" not in glued
