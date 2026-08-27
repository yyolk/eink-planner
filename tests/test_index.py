"""Optional Contents page (section key ``index``) and back-link mark."""

from __future__ import annotations

from pathlib import Path

from parch.config import load
from parch.i18n import I18n
from parch.services.config_file import CANONICAL_SECTIONS
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.test_toml_omit_sections import compile_pdf
from tests.toml_fixtures import _minimal, omit_toml_sections, short_january

REPO = Path(__file__).resolve().parents[1]
NOMAD = REPO / "configs/supernote-nomad.toml"
NOMAD_MOS_RIGHT = REPO / "configs/supernote-nomad-mos-right.toml"

_TOC_TITLE = 'weight: "bold")[Contents <index>]'
_MARK_RULE = "line(length: 1.2em, stroke: thick_stroke + black)"
_MARK_LINK = "padded_link(<index>"


def _generate(dto) -> str:
    return Generate(i18n=I18n.load_default(REPO, "en")).generate(dto)


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
    for name in ("Quarters", "Months", "Weeks", "Days", "Projects", "Habits", "Review", "Meetings"):
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
    assert _MARK_LINK not in cover
    assert _MARK_RULE not in cover
    assert "<index>" not in cover


def test_contents_page_has_no_back_link_mark():
    typst = _generate(load(NOMAD))
    page = _contents_page(typst)
    assert _TOC_TITLE in page
    assert _MARK_LINK not in page
    assert _MARK_RULE not in page


def test_annual_keeps_calendar_chip_and_links_to_index():
    typst = _generate(load(NOMAD))
    page = _annual_page(typst)
    assert "padded_link(<annual>" in page
    assert "Calendar" in page
    assert "fill: black" in page
    assert _MARK_LINK in page
    assert _MARK_RULE in page
    assert page.count(_MARK_RULE) == 4


def test_colophon_has_mark_and_unchanged_facts():
    typst = _generate(load(NOMAD))
    page = _colophon_page(typst)
    assert _MARK_LINK in page
    assert _MARK_RULE in page
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
    mark_at = page.index(_MARK_LINK)
    chip_at = page.index("[Calendar]")
    assert title_at < mark_at < chip_at
    for label in ("Q1", "Q2", "Q3", "Q4"):
        assert label in page
    assert page.count(_MARK_RULE) == 4


def test_daily_year_chip_sits_beside_lead_title():
    typst = _generate(load(NOMAD))
    page = next(p for p in _pages(typst) if "1 <2026-01-01>" in p)
    title_at = page.index("1 <2026-01-01>")
    mark_at = page.index(_MARK_LINK)
    chip_at = page.index("[2026]")
    assert title_at < mark_at < chip_at



def test_mos_right_habits_mark_sits_next_to_strip():
    typst = _generate(load(NOMAD_MOS_RIGHT))
    page = next(p for p in _pages(typst) if "January<habits-january>" in p)
    title_at = page.index("January<habits-january>")
    mark_at = page.index(_MARK_LINK)
    strip_at = page.index("rowspan: 2")
    assert title_at < mark_at < strip_at
    assert page[mark_at:strip_at].count("padded_link") == 1
