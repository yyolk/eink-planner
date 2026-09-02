"""Weekly pages: Week N + range title, paper MOS, week_matrix emit."""


from parch.compose.page_data import HeadingMark
from parch.i18n import I18n
from parch.mos.manifest import Manifest
from parch.mos.pages.weekly import Weekly
from parch.sections.annual import Annual
from parch.sections.weekly import Weekly as WeeklySection
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.helpers import base_config, load_default, make_configurator, make_week
from tests.toml_fixtures import omit_toml_sections

_EN_DASH = "–"
_W01_RANGE = f"Dec 29 {_EN_DASH} Jan 4"
_W28_RANGE = f"Jul 6 {_EN_DASH} 12"

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

_CELL_CHROME = (
    "grid.cell(stroke: (bottom: regular_stroke + black), "
    'inset: (bottom: 0.25em), text(bottom-edge: "descender", '
)

_WRITING_PATTERN = (
    "box(width: 100%, height: 100%, clip: true, "
    "inset: (top: 0.25em, bottom: 0.25em), lined_well("
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


def _assert_week_matrix_emit(content: str, *, gutter: str, pattern: str, notes: str = "[Notes]") -> None:
    assert "week_matrix(" in content
    assert f"column-gutter: {gutter}" in content
    assert "header-stroke" not in content
    assert f"pattern: {pattern}" in content
    assert content.count(f"pattern: {pattern}") == 1
    assert "week_cell(" not in content
    assert "lined_well(" not in content
    assert "regular-height" not in content
    assert "grid.cell" not in content
    assert "grid.cell(colspan" not in content
    assert "side:" not in content
    assert _CELL_CHROME not in content
    assert _WRITING_PATTERN not in content
    assert "rows: (auto, 1fr)" not in content
    assert "columns: (1fr, 1fr, 1fr)" not in content
    assert "rows: (1fr, 1fr, 1fr)" not in content
    assert notes in content


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
    assert "padded_link(<2025-12-29>)[Monday 29]" in content
    assert _CELL_CHROME not in content


def test_thin_black_rule_not_thick_stroke():
    content = _page("2025-12-29").content()
    assert "thick_stroke" not in content
    assert "regular_stroke + black" not in content
    assert "header-stroke" not in content


def test_eight_contents_then_notes_no_python_grid_cell():
    content = _page("2025-12-29").content()
    _assert_week_matrix_emit(content, gutter="4pt", pattern="dotted_centered")
    for label in W01_DAYS:
        assert f"[{label}]" in content
    assert content.index("[Monday 29]") < content.index("[Tuesday 30]")
    assert content.index("[Saturday 3]") < content.index("[Sunday 4]")
    assert content.index("[Sunday 4]") < content.index("[Notes]")


def test_per_cell_pattern_is_house_owned():
    content = _page("2025-12-29").content()
    _assert_week_matrix_emit(content, gutter="4pt", pattern="dotted_centered")
    assert "grid.cell(colspan: 3, lined_well" not in content
    assert "colspan: 3" not in content
    assert "lined_well(" not in content
    assert "colspan:" not in content


def test_writing_field_chrome_stays_in_house():
    content = _page("2025-12-29").content()
    assert _WRITING_PATTERN not in content
    assert "week_cell(" not in content
    assert 'bottom-edge: "descender"' not in content


def test_pattern_switches():
    lined = _page("2025-12-29", pattern="lined").content()
    _assert_week_matrix_emit(lined, gutter="4pt", pattern="lined_fill")
    assert "pattern: dotted" not in lined
    assert "pattern: dotted_centered" not in lined
    assert "week_cell(" not in lined
    assert "lined_well(" not in lined


def test_title_is_week_and_range_without_year_and_kills_calendar_chip():
    manifest = Manifest()
    manifest.register_source(Annual.ID)
    section = _section()
    pages = section.pages(manifest)
    first = pages[0]
    assert first.nav_links == []
    assert first.heading_mark is HeadingMark.TRAIL
    assert first.show_quarters is True
    assert len(first.highlight_months) == 1
    assert first.highlight_months[0].id == "month-2026-01-01"
    assert first.highlight_months[0].name == "january"
    assert first.highlight_quarters == []
    assert "padded_link(<annual>)" not in first.title
    assert "text(size: h1)[/]" not in first.title
    assert "2026 /" not in first.title
    assert f"Week 1 <2026W01> #h(0.6em) {_W01_RANGE}" in first.title
    assert "Calendar" not in first.title
    assert "Calendar" not in first.content
    for week, page in zip(section._weeks(), pages, strict=True):
        thursday = next(day for day in week.days() if day.weekday_name == "thursday")
        days = week.days()
        rng = section.range_label(days[0], days[-1])
        assert page.nav_links == []
        assert page.highlight_months == [thursday.month()]
        assert len(page.highlight_months) == 1
        assert page.highlight_quarters == []
        assert page.show_quarters is True
        assert page.heading_mark is HeadingMark.TRAIL
        assert "Calendar" not in page.title
        assert "text(size: h1)[/]" not in page.title
        assert "2026 /" not in page.title
        assert f"Week {week.number} <{week.id}> #h(0.6em) {rng}" in page.title


def test_generated_week_title_is_range_and_inverts_thursday_month():
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), _BULKY)
    typst = _generate(parse_toml(text, source="nomad-weekly.toml"))
    pages = _week_pages(typst)
    w01 = pages["w01"]
    w28 = pages["w28"]
    assert "padded_link(<annual>)[2026]" not in w01
    assert "text(size: h1)[/]" not in w01
    assert "2026 /" not in w01
    assert f"Week 1 <2026W01> #h(0.6em) {_W01_RANGE}" in w01
    heading = w01[w01.index("trail_heading(") : w01.index("week_matrix(")]
    assert heading.startswith("trail_heading(")
    assert "lead_pair(" not in heading
    assert "column-gutter: 6pt" not in heading
    assert "pad(right: 3mm" not in heading
    assert "contents_bars(size:" in heading
    assert "padded_link(<annual>)[2026]" not in heading
    assert w01.count("Calendar") == 0
    assert "Calendar" not in w01
    assert "Monday 29" in w01
    assert "Thursday 1" in w01
    _assert_week_matrix_emit(w01, gutter="4pt", pattern="dotted_centered")
    assert "Monday, 29" not in w01
    assert "Thursday,  1" not in w01
    assert w01.count("contents_bars(size:") == 1
    assert "grid.cell(stroke: (bottom: thick_stroke" not in w01
    assert "grid.cell(colspan: 3, lined_well" not in w01
    assert "week_cell(" not in w01
    assert _WRITING_PATTERN not in w01
    assert "[Notes]" in w01
    bind = typst[typst.index("#let mos_strip = mos_strip.with(months:") :].split("\n", 1)[0]
    assert "(<month-2026-01-01>, [Jan])" in bind
    assert "(<quarter-2026-1>, [Q1])" in bind
    assert "(<quarter-2026-4>, [Q4])" in bind
    assert "mos_strip(highlight-months: (<month-2026-01-01>,), highlight-quarters: ())" in w01
    assert "mos_tabs(" not in w01
    assert "table.cell(fill: black" not in w01
    assert "highlight-months: (<month-2025-12-01>," not in w01
    assert f"Week 28 <2026W28> #h(0.6em) {_W28_RANGE}" in w28
    assert "Monday 6" in w28
    assert w28.count("Calendar") == 0
    _assert_week_matrix_emit(w28, gutter="4pt", pattern="dotted_centered")
    assert "week_cell(" not in w28
    assert "mos_strip(highlight-months: (<month-2026-07-01>,), highlight-quarters: ())" in w28
    assert "table.cell(fill: black" not in w28
