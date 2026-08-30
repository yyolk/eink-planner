"""Weekly pages: year / Week N crumb, paper MOS, per-cell pattern."""

from __future__ import annotations


from parch.i18n import I18n
from parch.mos.manifest import Manifest
from parch.mos.pages.weekly import Weekly
from parch.sections.annual import Annual
from parch.sections.weekly import Weekly as WeeklySection
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.helpers import base_config, load_default, make_configurator, make_week
from tests.toml_fixtures import omit_toml_sections

NOMAD = base_config("supernote-nomad")

_BULKY = (
    "daily",
    "daily_notes",
    "colophon",
    "projects",
    "habits",
    "review",
    "tasks",
    "meetings",
)

W01_DAYS = (
    "Monday 29",
    "Tuesday 30",
    "Wednesday 31",
    "Thursday 1",
    "Friday 2",
    "Saturday 3",
    "Sunday 4",
)

OLD_W01_DAYS = (
    "Monday, 29",
    "Tuesday, 30",
    "Wednesday, 31",
    "Thursday,  1",
    "Friday,  2",
    "Saturday,  3",
    "Sunday,  4",
)

_HEADER_CELL = (
    "grid.cell(stroke: (bottom: regular_stroke + black), "
    'inset: (bottom: 0.25em), text(bottom-edge: "descender", '
)

_WRITING_PATTERN = (
    "box(width: 100%, height: 100%, clip: true, "
    "inset: (top: 0.25em, bottom: 0.25em), rect_pattern("
)


def _i18n() -> I18n:
    return load_default()


def _page(date_str: str, pattern: str = "dotted", manifest: Manifest | None = None) -> Weekly:
    return Weekly(
        i18n=_i18n(),
        manifest=manifest or Manifest(),
        week=make_week(date_str),
        column_gutter="4pt",
        pattern=pattern,
    )


def _section() -> WeeklySection:
    return WeeklySection(
        section_name="weekly",
        i18n=_i18n(),
        configurator=make_configurator(),
        column_gutter="4pt",
    )


def _generate(dto) -> str:
    return Generate(i18n=_i18n()).generate(dto)


def _week_pages(typst_src: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for page in typst_src.split("#pagebreak()"):
        if "Week 1 <2026W01>" in page:
            found["w01"] = page
        if "Week 28 <2026W28>" in page:
            found["w28"] = page
    return found


def test_w01_title_keeps_week_id_for_finders():
    assert _page("2025-12-29").title() == "text(size: h1)[Week 1 <2026W01>]"


def test_w01_headers_are_weekday_space_day():
    content = _page("2025-12-29").content()
    for label in W01_DAYS:
        assert f"[{label}]" in content
    for label in OLD_W01_DAYS:
        assert f"[{label}]" not in content
    assert "Monday, 29" not in content
    assert "Thursday,  1" not in content
    assert "Thursday, 1" not in content


def test_headers_link_to_daily_when_registered():
    manifest = Manifest()
    manifest.register_source("2025-12-29")
    content = _page("2025-12-29", manifest=manifest).content()
    assert f"{_HEADER_CELL}padded_link(<2025-12-29>)[Monday 29])" in content


def test_thin_black_rule_not_thick_stroke():
    content = _page("2025-12-29").content()
    assert "thick_stroke" not in content
    assert content.count("regular_stroke + black") == 8


def test_header_rule_sits_under_descenders():
    content = _page("2025-12-29").content()
    assert content.count(_HEADER_CELL) == 8
    assert f"{_HEADER_CELL}[Monday 29])" in content
    assert f"{_HEADER_CELL}[Notes])" in content
    assert "rows: (auto, 1fr)" in content
    assert "stroke: (left:" not in content
    assert "stroke: (right:" not in content
    assert "stroke: (top:" not in content
    assert "stroke: regular_stroke + black)" not in content


def test_per_cell_pattern_keeps_white_gutters():
    content = _page("2025-12-29").content()
    assert "grid.cell(colspan: 3, rect_pattern" not in content
    assert "colspan: 3" not in content
    assert content.count("rect_pattern(dotted)") == 8
    assert "columns: (1fr, 1fr, 1fr)" in content
    assert "rows: (1fr, 1fr, 1fr)" in content
    assert "rows: (auto, 1fr)" in content
    assert "column-gutter: 4pt" in content
    assert "[Notes]" in content
    assert "grid.cell(colspan: 2," in content


def test_writing_field_clips_and_insets_pattern():
    content = _page("2025-12-29").content()
    assert content.count(_WRITING_PATTERN) == 8
    assert f"{_WRITING_PATTERN}dotted)" in content
    assert (
        "box(width: 100%, height: 100%, clip: true, "
        "inset: (top: 0.25em, bottom: 0.25em), rect_pattern(dotted))"
    ) in content
    assert content.count("rect_pattern(dotted)") == 8


def test_pattern_switches():
    lined = _page("2025-12-29", pattern="lined").content()
    assert lined.count("rect_pattern(lined)") == 8
    assert lined.count(f"{_WRITING_PATTERN}lined)") == 8
    assert "rect_pattern(dotted)" not in lined


def test_title_is_year_slash_week_crumb_and_kills_calendar_chip():
    manifest = Manifest()
    manifest.register_source(Annual.ID)
    section = _section()
    pages = section.pages(manifest)
    year_cell = manifest.link_or_content(Annual.ID, "2026")
    first = pages[0]
    assert first.nav_links == []
    assert first.show_quarters is True
    assert len(first.highlight_months) == 1
    assert first.highlight_months[0].id == "month-2026-01-01"
    assert first.highlight_months[0].name == "january"
    assert first.highlight_quarters == []
    assert f"text(size: h1, {year_cell})" in first.title
    assert "text(size: h1)[/]" in first.title
    assert "Week 1 <2026W01>" in first.title
    assert "Calendar" not in first.title
    assert "Calendar" not in first.content
    for week, page in zip(section._weeks(), pages, strict=True):
        thursday = next(day for day in week.days() if day.weekday_name == "thursday")
        assert page.nav_links == []
        assert page.highlight_months == [thursday.month()]
        assert len(page.highlight_months) == 1
        assert page.highlight_quarters == []
        assert page.show_quarters is True
        assert "Calendar" not in page.title
        assert "text(size: h1)[/]" in page.title
        assert "Week " in page.title
        assert f"text(size: h1, {year_cell})" in page.title


def test_generated_year_crumb_links_to_annual_and_inverts_thursday_month():
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), _BULKY)
    typst = _generate(parse_toml(text, source="nomad-weekly.toml"))
    pages = _week_pages(typst)
    w01 = pages["w01"]
    w28 = pages["w28"]
    assert "padded_link(<annual>)[2026]" in w01
    assert "text(size: h1)[/]" in w01
    assert "Week 1 <2026W01>" in w01
    assert w01.count("Calendar") == 0
    assert "Calendar" not in w01
    assert "Monday 29" in w01
    assert "Thursday 1" in w01
    assert w01.count(_HEADER_CELL) == 8
    assert f"{_HEADER_CELL}[Notes])" in w01
    assert "Monday, 29" not in w01
    assert "Thursday,  1" not in w01
    assert w01.count("line(length: 0.844em, stroke: thick_stroke + black)") == 5
    assert "grid.cell(stroke: (bottom: thick_stroke" not in w01
    assert "grid.cell(colspan: 3, rect_pattern" not in w01
    assert w01.count("rect_pattern(dotted)") == 8
    assert w01.count(_WRITING_PATTERN) == 8
    assert f"{_WRITING_PATTERN}dotted)" in w01
    assert "[Notes]" in w01
    assert "table.cell(fill: black, text(white)[#padded_link(<month-2026-01-01>)[Jan]])" in w01
    assert "table.cell([#padded_link(<quarter-2026-1>)[Q1]])" in w01
    assert "table.cell(fill: black, text(white)[#padded_link(<quarter-" not in w01
    assert "table.cell(fill: black, text(white)[#padded_link(<month-2025-12-01>)" not in w01
    assert "Q1" in w01 and "Q4" in w01
    assert w01.count("table.cell(fill: black") == 1
    assert "Week 28 <2026W28>" in w28
    assert "Monday 6" in w28
    assert w28.count("Calendar") == 0
    assert w28.count("rect_pattern(dotted)") == 8
    assert "table.cell(fill: black, text(white)[#padded_link(<month-2026-07-01>)[Jul]])" in w28
    assert "table.cell([#padded_link(<quarter-2026-3>)[Q3]])" in w28
    assert "table.cell(fill: black, text(white)[#padded_link(<quarter-" not in w28
    assert w28.count("table.cell(fill: black") == 1
