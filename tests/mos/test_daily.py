"""Daily pages: date block, Contents mark alone, paper MOS, no year chip."""


from parch.calendar.dated_note import DatedNote
from parch.i18n import I18n
from parch.mos.manifest import Manifest
from parch.mos.pages.daily import Daily
from parch.compose.page_data import HeadingMark
from parch.sections.daily import Daily as DailySection
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.helpers import base_config, load_default, make_configurator, make_day
from tests.toml_fixtures import omit_toml_sections

NOMAD = base_config("supernote-nomad")
NOMAD_MOS_RIGHT = base_config("supernote-nomad-mos-right")

_MARK_RULE = "line(length: 0.844em, stroke: thick_stroke + black)"
_MARK_FLUSH = "padded_link(padding: 0pt, <index>"
_TRAIL_MARK = "pad(right: 3mm, padded_link(padding: 0pt, <index>"
_SEATED_TRAIL = "box(height: band, align(horizon + left, seated_"
_SEATED_TITLE = "let seated_title ="
_SEATED_MARK = "let seated_mark ="
_SEAT_RTL = "dir: rtl,\n    spacing: 1fr,"
_SEAT_LTR = "dir: ltr,\n    spacing: 1fr,"

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
        "columns_width": "(3fr, 5fr)",
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
        columns_width="(3fr, 5fr)",
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
    assert "if x == 1 {( left: regular_stroke + black )}" in jan1
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
    assert content.count("$square.stroked$") == 5
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
    assert "grid.cell(colspan: 2, rect_pattern(dotted))" in content
    assert "[Notes]" in content


def test_notes_alone_when_daily_notes_off():
    content = _page("2026-01-01").content()
    assert "More" not in content
    assert "| " not in content
    assert "columns: (1fr, auto)" not in content
    assert "colspan: 2" not in content
    assert "[Notes]" in content
    assert "rect_pattern(dotted)" in content
    assert "stroke: (bottom: regular_stroke + black)" in content


def test_notes_pattern_switches():
    for pattern in ("lined", "review_lined", "dotted", "dotted_centered"):
        right = [
            {"class": "priorities", "enabled": True, "params": {"number": 5}},
            {
                "class": "notes",
                "enabled": True,
                "params": {"title_height": "4mm", "notes_height": "1fr", "pattern": pattern},
            },
        ]
        content = _page("2026-01-01", right_column=right).content()
        assert f"rect_pattern({pattern})" in content


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
    assert jan1.count(_MARK_RULE) == 5
    assert jan1.index("1 <2026-01-01>") < jan1.index(_TRAIL_MARK)
    heading = jan1[jan1.index(_SEATED_TITLE) : jan1.index(_SEATED_MARK)]
    assert "1 <2026-01-01>" in heading
    assert _SEAT_RTL in jan1
    assert _SEATED_TRAIL in jan1
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
    assert "table.cell(fill: black, text(white)[#padded_link(<month-2026-01-01>)[Jan]])" in jan1
    assert "table.cell([#padded_link(<quarter-2026-1>)[Q1]])" in jan1
    assert "table.cell(fill: black, text(white)[#padded_link(<quarter-" not in jan1
    assert "Q1" in jan1 and "Q4" in jan1
    assert "Jan" in jan1 and "Dec" in jan1
    assert jan1.count("table.cell(fill: black") == 1


def test_generated_mos_right_contents_mark_alone_left_of_q1():
    text = omit_toml_sections(NOMAD_MOS_RIGHT.read_text(encoding="utf-8"), _BULKY)
    typst = _generate(parse_toml(text, source="nomad-mos-right-daily.toml"))
    pages = _daily_pages(typst)
    jan1 = pages["jan1"]
    assert "padded_link(<annual>, [2026])" not in jan1
    assert _TRAIL_MARK in jan1
    assert jan1.count(_MARK_RULE) == 5
    assert jan1.index("1 <2026-01-01>") < jan1.index(_TRAIL_MARK)
    heading = jan1[jan1.index(_SEATED_TITLE) : jan1.index(_SEATED_MARK)]
    assert "1 <2026-01-01>" in heading
    assert _SEAT_LTR in jan1
    assert _SEATED_TRAIL in jan1
    assert "column-gutter: 6pt" not in heading
    assert "2026 /" not in jan1
    assert "text(size: h1)[/]" not in jan1
    assert jan1.count("Calendar") == 0
    assert "table.cell(fill: black, text(white)[#padded_link(<month-2026-01-01>)[Jan]])" in jan1
    assert "table.cell([#padded_link(<quarter-2026-1>)[Q1]])" in jan1
    assert jan1.count("table.cell(fill: black") == 1
