"""Daily pages: date block, Contents mark alone, paper MOS, no year chip."""


from parch.calendar.dated_note import DatedNote
from parch.i18n import I18n
from parch.mos.manifest import Manifest
from parch.mos.pages.daily import Daily
from parch.compose.page_data import HeadingMark
from parch.sections.daily import Daily as DailySection
from parch.services.generate import Generate
from parch.toml_config import apply_hand, parse_toml
from tests.helpers import base_config, load_default, make_configurator, make_day
from tests.toml_fixtures import omit_toml_sections

NOMAD = base_config("supernote-nomad")

_MARK_RULE = "contents_bars(size:"
_MARK_FLUSH = "padded_link(padding: 0pt, <index>"
_TRAIL_MARK = "padded_link(padding: 0pt, <index>"
_TRAIL_HEADING = "trail_heading("

_BULKY = (
    "colophon",
    "projects",
    "habits",
    "review",
    "tasks",
    "meetings",
)

_LEFT = [
    {
        "class": "schedule",
        "enabled": True,
        "params": {"from": 8, "to": 20, "time_format": "%k", "trailing_30_minutes": True},
    },
    {
        "class": "little_calendar",
        "enabled": True,
        "params": {"week_placement": "left", "inset": "3pt"},
    },
]
_RIGHT = [
    {"class": "priorities", "enabled": True, "params": {"number": 5}},
    {
        "class": "notes",
        "enabled": True,
        "params": {"title_height": "4mm", "notes_height": "1fr", "pattern": "dotted"},
    },
]


def _i18n() -> I18n:
    return load_default()


def _page(date_str: str, manifest: Manifest | None = None, **overrides) -> Daily:
    params = {
        "items_spacing": "4mm",
        "left_column": _LEFT,
        "right_column": _RIGHT,
    }
    params.update(overrides)
    return Daily(
        i18n=_i18n(),
        manifest=manifest or Manifest(),
        day=make_day(date_str),
        **params,
    )


def _section(start_date: str = "2026-01-01", end_date: str = "2026-01-04") -> DailySection:
    return DailySection(
        section_name="daily",
        i18n=_i18n(),
        configurator=make_configurator(start_date=start_date, end_date=end_date),
        items_spacing="4mm",
        left_column=_LEFT,
        right_column=_RIGHT,
    )


def _generate(dto) -> str:
    return Generate(i18n=_i18n()).generate(dto)


def _daily_pages(typst_src: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for page in typst_src.split("#pagebreak()"):
        if "1 <2026-01-01>" in page:
            found["jan1"] = page
        if "4 <2026-01-04>" in page:
            found["jan4"] = page
    return found


def test_title_keeps_day_weekday_and_week_n():
    manifest = Manifest()
    manifest.register_source("2026W01")
    title = _page("2026-01-01", manifest=manifest).title()
    assert "text(size: h1)[1 <2026-01-01>]" in title
    assert "[*Thursday*]" in title
    assert "padded_link(<2026W01>)[Week 1]" in title
    assert "2026 /" not in title
    assert "text(size: h1)[/]" not in title
    assert "Calendar" not in title


def test_nav_links_empty_not_year_chip_or_calendar():
    section = _section()
    pages = section.pages(Manifest())
    assert len(pages) == 4
    for day, page in zip(section._range(), pages, strict=True):
        assert page.nav_links == []
        assert page.heading_mark is HeadingMark.TRAIL
        assert page.page_id == DailySection.ID
        assert page.highlight_months == [day.month()]
        assert len(page.highlight_months) == 1
        assert page.highlight_quarters == []
        assert page.show_quarters is True
        assert "Calendar" not in page.title
        assert "Calendar" not in page.content
        assert "2026 /" not in page.title
        assert "text(size: h1)[/]" not in page.title
        assert f"text(size: h1)[{day.month_day} <{day.id}>]" in page.title
        weekday = _i18n().t(f"weekday.full.{day.weekday_name}")
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


def test_content_emits_daily_well_hours_then_writing():
    content = _page("2026-01-01").content()
    assert "daily_well(" in content
    assert "daily_well(left," in content
    well = content[content.index("daily_well(") :]
    assert well.index("left,") < well.index("[Schedule]")
    assert well.index("[Schedule]") < well.index("[Priorities]")
    assert well.index("[Priorities]") < well.index("[Notes]")
    assert "columns: (3fr, 5fr)" not in content
    assert "columns: (5fr, 3fr)" not in content


def test_content_hand_right_still_passes_hours_then_writing():
    content = _page("2026-01-01", side="right").content()
    assert "daily_well(right," in content
    well = content[content.index("daily_well(") :]
    assert well.index("right,") < well.index("[Schedule]")
    assert well.index("[Schedule]") < well.index("[Priorities]")
    assert "daily_well(left," not in content


def test_schedule_has_no_gray_and_uses_thin_black_rules():
    content = _page("2026-01-01").content()
    assert "gray" not in content
    assert "grey" not in content
    assert "luma" not in content
    assert "thick_stroke" not in content
    assert "regular_stroke + gray" not in content
    assert "if calc.even(y)" not in content
    assert "stroke: (bottom: regular_stroke + black)" in content
    assert "place(bottom + left, line(length: 3mm, stroke: regular_stroke + black))" in content
    assert "align(horizon, [ 8])" in content
    assert "align(horizon, [20])" in content
    assert "align(horizon, [ 7])" not in content
    assert "align(horizon, [21])" not in content


def test_little_calendar_omits_week_letter_and_inverts_this_page_date():
    jan1 = _page("2026-01-01").content()
    assert "[], [M], [T], [W], [T], [F], [S], [S]" in jan1
    assert "[W], [M], [T], [W], [T], [F], [S], [S]" not in jan1
    assert "month_grid(left," in jan1
    assert "if x == 1 {( left: regular_stroke + black )}" not in jan1
    assert "grid.cell(fill: black, text(white, [1]))" in jan1
    assert "grid.cell(fill: black, text(white, [4]))" not in jan1
    jan4 = _page("2026-01-04").content()
    assert "grid.cell(fill: black, text(white, [4]))" in jan4
    assert "grid.cell(fill: black, text(white, [1]))" not in jan4
    assert jan4.count("grid.cell(fill: black") == 1
    assert jan1.count("grid.cell(fill: black") == 1


def test_priorities_label_squares_and_thin_black_rule():
    content = _page("2026-01-01").content()
    assert "[Priorities]" in content
    assert "Top priorities" not in content
    assert content.count("box(height: regular_height, align(horizon + start, task_tick))") == 5
    assert "$square.stroked$" not in content
    assert "task_fill" not in content
    assert "grid.cell(stroke: (bottom: regular_stroke + black), box(height: regular_height, align(horizon, [Priorities])))" in content
    assert "stroke: (_, _) => (bottom: regular_stroke + black)" in content


def test_notes_more_has_no_pipe_when_daily_notes_registered():
    day = make_day("2026-01-01")
    manifest = Manifest()
    manifest.register_source(DatedNote(weekday_start=day.weekday_start, day=day).id)
    content = _page("2026-01-01", manifest=manifest).content()
    assert "| More" not in content
    assert "[| " not in content
    assert "padded_link(<daily-note-2026-01-01-page-1>)[More]" in content
    assert "columns: (1fr, auto)" in content
    assert "grid.cell(colspan: 2, lined_well(dotted_centered))" in content
    assert "[Notes]" in content


def test_notes_alone_when_daily_notes_off():
    content = _page("2026-01-01").content()
    assert "More" not in content
    assert "| " not in content
    assert "columns: (1fr, auto)" not in content
    assert "colspan: 2" not in content
    assert "[Notes]" in content
    assert "lined_well(dotted_centered)" in content
    assert "stroke: (bottom: regular_stroke + black)" in content


def test_notes_pattern_switches():
    mapped = {
        "lined": "lined_fill",
        "review_lined": "review_lined",
        "dotted": "dotted_centered",
        "dotted_centered": "dotted_centered",
    }
    for pattern, well in mapped.items():
        right = [
            {"class": "priorities", "enabled": True, "params": {"number": 5}},
            {
                "class": "notes",
                "enabled": True,
                "params": {"title_height": "4mm", "notes_height": "1fr", "pattern": pattern},
            },
        ]
        content = _page("2026-01-01", right_column=right).content()
        assert f"lined_well({well})" in content
        assert "rect_pattern(" not in content


def test_calendar_appears_nowhere_on_title_or_content():
    title = _page("2026-01-01").title()
    content = _page("2026-01-01").content()
    assert "Calendar" not in title
    assert "Calendar" not in content


def test_generated_contents_mark_alone_and_inverts_january_only():
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), _BULKY)
    typst = _generate(parse_toml(text, source="nomad-daily.toml"))
    pages = _daily_pages(typst)
    jan1 = pages["jan1"]
    assert "padded_link(<annual>, [2026])" not in jan1
    assert "grid.cell(fill: black, text(white)[#padded_link(<annual>, [2026])])" not in jan1
    assert _TRAIL_MARK in jan1
    assert _MARK_FLUSH in jan1
    assert jan1.count(_MARK_RULE) == 1
    assert jan1.index("1 <2026-01-01>") < jan1.index(_TRAIL_MARK)
    heading = jan1[jan1.index(_TRAIL_HEADING) : jan1.index(_TRAIL_MARK)]
    assert "1 <2026-01-01>" in heading
    assert "direction:" not in heading
    assert "spacing:" not in heading
    assert _TRAIL_HEADING in jan1
    assert "column-gutter: 6pt" not in heading
    assert "text(size: h1)[1 <2026-01-01>]" in jan1
    assert "[*Thursday*]" in jan1
    assert "Week 1" in jan1
    assert "2026 /" not in jan1
    assert "text(size: h1)[/]" not in jan1
    assert jan1.count("Calendar") == 0
    assert "Calendar" not in jan1
    assert "[Priorities]" in jan1
    assert "Top priorities" not in jan1
    assert "gray" not in jan1
    assert "regular_stroke + gray" not in jan1
    assert "place(bottom + left, line(length: 3mm, stroke: regular_stroke + black))" in jan1
    assert "[], [M], [T], [W], [T], [F], [S], [S]" in jan1
    assert "[W], [M], [T], [W], [T], [F], [S], [S]" not in jan1
    assert "| More" not in jan1
    assert "padded_link(<daily-note-2026-01-01-page-1>)[More]" in jan1
    bind = typst[typst.index("#let mos_strip = mos_strip.with(months:") :].split("\n", 1)[0]
    assert "(<month-2026-01-01>, [Jan])" in bind
    assert "(<month-2026-12-01>, [Dec])" in bind
    assert "(<quarter-2026-1>, [Q1])" in bind
    assert "(<quarter-2026-4>, [Q4])" in bind
    assert "mos_strip(highlight-months: (<month-2026-01-01>,), highlight-quarters: ())" in jan1
    assert "mos_tabs(" not in jan1
    assert "table.cell(fill: black" not in jan1
    assert "daily_well(" in jan1
    assert "daily_well(left," in jan1
    well = jan1[jan1.index("daily_well(") :]
    assert well.index("left,") < well.index("[Schedule]")
    assert well.index("[Schedule]") < well.index("[Priorities]")


def test_generated_hand_right_contents_mark_alone_left_of_q1():
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), _BULKY)
    typst = _generate(apply_hand(parse_toml(text, source="nomad-hand-right-daily.toml"), "right"))
    pages = _daily_pages(typst)
    jan1 = pages["jan1"]
    assert "padded_link(<annual>, [2026])" not in jan1
    assert _TRAIL_MARK in jan1
    assert jan1.count(_MARK_RULE) == 1
    assert jan1.index("1 <2026-01-01>") < jan1.index(_TRAIL_MARK)
    heading = jan1[jan1.index(_TRAIL_HEADING) : jan1.index(_TRAIL_MARK)]
    assert "1 <2026-01-01>" in heading
    assert "direction:" not in heading
    assert "spacing:" not in heading
    assert _TRAIL_HEADING in jan1
    assert "column-gutter: 6pt" not in heading
    assert "2026 /" not in jan1
    assert "text(size: h1)[/]" not in jan1
    assert jan1.count("Calendar") == 0
    assert "mos_strip(highlight-months: (<month-2026-01-01>,), highlight-quarters: ())" in jan1
    assert "table.cell(fill: black" not in jan1
    assert "daily_well(" in jan1
    assert "daily_well(right," in jan1
    well = jan1[jan1.index("daily_well(") :]
    assert well.index("right,") < well.index("[Schedule]")
    assert well.index("[Schedule]") < well.index("[Priorities]")
    assert "daily_well(left," not in jan1
