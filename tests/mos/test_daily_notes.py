"""Daily notes: overflow behind More, year chip, paper MOS, no Calendar."""

from __future__ import annotations


from parch.i18n import I18n
from parch.mos.manifest import Manifest
from parch.mos.sections.annual import Annual
from parch.mos.sections.daily_notes import DailyNotes
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.helpers import base_config, load_default, make_configurator
from tests.toml_fixtures import omit_toml_sections

NOMAD = base_config("supernote-nomad")

_BULKY = (
    "colophon",
    "projects",
    "habits",
    "review",
    "tasks",
    "meetings",
)

_BANNED_BODY = (
    "[Notes]",
    "[Schedule]",
    "[Priorities]",
    "Top priorities",
    "little_calendar",
    "Calendar",
)


def _i18n() -> I18n:
    return load_default()


def _section(
    pages: int = 2,
    pattern: str = "dotted",
    start_date: str = "2026-01-01",
    end_date: str = "2026-01-04",
) -> DailyNotes:
    return DailyNotes(
        section_name="daily_notes",
        i18n=_i18n(),
        configurator=make_configurator(start_date=start_date, end_date=end_date),
        pages=pages,
        pattern=pattern,
    )


def _generate(dto) -> str:
    return Generate(i18n=_i18n()).generate(dto)


def _note_pages(typst_src: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for page in typst_src.split("#pagebreak()"):
        if "1 <daily-note-2026-01-01-page-1>" in page:
            found["p1"] = page
        if "1 <daily-note-2026-01-01-page-2>" in page:
            found["p2"] = page
    return found


def _register_jan1(manifest: Manifest, pages: int = 2) -> Manifest:
    manifest.register_source(Annual.ID)
    manifest.register_source("2026-01-01")
    manifest.register_source("2026W01")
    for page in range(1, pages + 1):
        manifest.register_source(f"daily-note-2026-01-01-page-{page}")
    return manifest


def test_nav_links_are_year_chip_not_calendar():
    manifest = _register_jan1(Manifest())
    section = _section()
    pages = section.pages(manifest)
    assert len(pages) == 8
    for note, page in zip(section._range(), pages, strict=True):
        assert page.nav_links == [(Annual.ID, "2026")]
        assert page.nav_links != []
        assert page.highlight_months == [note.day.month()]
        assert len(page.highlight_months) == 1
        assert page.highlight_quarters == []
        assert page.show_quarters is True
        assert "Calendar" not in page.title
        assert "Calendar" not in page.content
        assert "2026 /" not in page.title
        assert "text(size: h1)[/]" not in page.title
        assert f"text(size: h1)[{note.day.month_day} <{note.id}>]" in page.title
        weekday = _i18n().t(f"weekday.full.{note.day.weekday_name}")
        assert f"[*{weekday}*]" in page.title
        assert "Week " in page.title


def test_highlight_months_is_this_days_month_only():
    manifest = Manifest()
    pages = _section().pages(manifest)
    first = pages[0]
    assert first.highlight_months[0].id == "month-2026-01-01"
    assert first.highlight_months[0].name == "january"
    assert first.highlight_quarters == []
    assert first.show_quarters is True
    fourth = pages[3]
    assert fourth.highlight_months[0].id == "month-2026-01-01"
    assert fourth.highlight_quarters == []


def test_heading_keeps_day_weekday_and_week_n():
    manifest = _register_jan1(Manifest())
    title = _section().pages(manifest)[0].title
    assert "text(size: h1)[1 <daily-note-2026-01-01-page-1>]" in title
    assert "padded_link(<2026-01-01>)" in title
    assert "[*Thursday*]" in title
    assert "padded_link(<2026W01>)[Week 1]" in title
    assert "2026 /" not in title
    assert "text(size: h1)[/]" not in title
    assert "Calendar" not in title


def test_calendar_appears_nowhere_on_title_or_content():
    pages = _section().pages(Manifest())
    for page in pages:
        assert "Calendar" not in page.title
        assert "Calendar" not in page.content


def test_content_is_rect_pattern_dotted_by_default():
    page = _section().pages(Manifest())[0]
    assert page.content == "rect_pattern(dotted)"
    for banned in _BANNED_BODY:
        assert banned not in page.title
        assert banned not in page.content


def test_pattern_switches():
    for pattern in ("lined", "review_lined", "dotted", "dotted_centered"):
        page = _section(pattern=pattern).pages(Manifest())[0]
        assert page.content == f"rect_pattern({pattern})"
        assert "rect_pattern(grid)" not in page.content


def test_no_notes_schedule_priorities_or_little_cal():
    page = _section().pages(Manifest())[0]
    blob = page.title + "\n" + page.content
    assert "[Notes]" not in blob
    assert "Notes" not in page.content
    assert "[Schedule]" not in blob
    assert "[Priorities]" not in blob
    assert "Top priorities" not in blob
    assert "little_calendar" not in blob
    assert "$square.stroked$" not in blob


def test_pages_two_have_quiet_fractions_linking_siblings():
    manifest = _register_jan1(Manifest(), pages=2)
    pages = _section(pages=2).pages(manifest)
    p1, p2 = pages[0], pages[1]
    assert "1/2" in p1.title
    assert "2/2" in p2.title
    assert "padded_link(<daily-note-2026-01-01-page-2>)[1/2]" in p1.title
    assert "padded_link(<daily-note-2026-01-01-page-1>)[2/2]" in p2.title
    assert "text(size: 0.85em, padded_link(<daily-note-2026-01-01-page-2>)[1/2])" in p1.title
    assert "text(size: 0.85em, padded_link(<daily-note-2026-01-01-page-1>)[2/2])" in p2.title
    assert "1/1" not in p1.title
    assert "1/1" not in p2.title
    assert "3/2" not in p1.title
    assert "page-3" not in p1.title
    assert "page-3" not in p2.title
    assert "1/2" not in p1.content
    assert "2/2" not in p2.content


def test_pages_one_omits_fraction():
    manifest = _register_jan1(Manifest(), pages=1)
    pages = _section(pages=1).pages(manifest)
    assert len(pages) == 4
    title = pages[0].title
    assert "1/1" not in title
    assert "1/2" not in title
    assert "2/2" not in title
    assert "0.85em" not in title
    assert "text(size: h1)[1 <daily-note-2026-01-01-page-1>]" in title
    assert "padded_link(<2026-01-01>)" in title
    assert "[*Thursday*]" in title
    assert "padded_link(<2026W01>)[Week 1]" in title


def test_generated_year_chip_links_to_annual_and_inverts_january_only():
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), _BULKY)
    typst = _generate(parse_toml(text, source="nomad-daily-notes.toml"))
    pages = _note_pages(typst)
    p1 = pages["p1"]
    p2 = pages["p2"]
    assert "padded_link(<annual>, [2026])" in p1
    assert "grid.cell(fill: black, text(white)[#padded_link(<annual>, [2026])])" not in p1
    assert "text(size: h1)[1 <daily-note-2026-01-01-page-1>]" in p1
    assert "padded_link(<2026-01-01>)" in p1
    assert "[*Thursday*]" in p1
    assert "Week 1" in p1
    assert "2026 /" not in p1
    assert "text(size: h1)[/]" not in p1
    assert p1.count("Calendar") == 0
    assert "Calendar" not in p1
    assert "Calendar" not in p2
    assert "[Notes]" not in p1
    assert "[Schedule]" not in p1
    assert "[Priorities]" not in p1
    assert "Top priorities" not in p1
    assert "rect_pattern(dotted)" in p1
    assert "padded_link(<daily-note-2026-01-01-page-2>)[1/2]" in p1
    assert "text(size: 0.85em, padded_link(<daily-note-2026-01-01-page-2>)[1/2])" in p1
    assert "padded_link(<daily-note-2026-01-01-page-1>)[2/2]" in p2
    assert "text(size: 0.85em, padded_link(<daily-note-2026-01-01-page-1>)[2/2])" in p2
    assert "table.cell(fill: black, text(white)[#padded_link(<month-2026-01-01>)[Jan]])" in p1
    assert "table.cell([#padded_link(<quarter-2026-1>)[Q1]])" in p1
    assert "table.cell(fill: black, text(white)[#padded_link(<quarter-" not in p1
    assert "Q1" in p1 and "Q4" in p1
    assert "Jan" in p1 and "Dec" in p1
    assert p1.count("table.cell(fill: black") == 1
    assert p2.count("table.cell(fill: black") == 1
