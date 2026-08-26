"""Monthly pages: year / month crumb, MOS invert, unboxed days, leftover notes."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from parch.i18n import I18n
from parch.mos.manifest import Manifest
from parch.mos.pages.monthly import Monthly
from parch.mos.sections.annual import Annual
from parch.mos.sections.monthly import Monthly as MonthlySection
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.helpers import make_configurator, make_month
from tests.test_toml_omit_sections import compile_pdf
from tests.toml_fixtures import omit_toml_sections

REPO = Path(__file__).resolve().parents[2]
NOMAD = REPO / "configs/supernote-nomad.toml"

_MONTH_PARAMS = {
    "week_placement": "left",
    "week_label_rotation": "90deg",
    "daily_cell_height": "16mm",
}

_BULKY = (
    "daily",
    "daily_notes",
    "colophon",
    "projects",
    "habits",
    "review",
    "meetings",
)
_MONTHLY_ONLY = _BULKY + ("cover", "annual", "quarterly", "weekly")

INNER_DAY_BOX = "box(stroke: regular_stroke, inset: 3pt)"


def _i18n() -> I18n:
    return I18n.load_default(REPO, "en")


def _page(yyyy_mm: str, week_placement: str = "left") -> Monthly:
    params = {**_MONTH_PARAMS, "week_placement": week_placement}
    return Monthly(
        i18n=_i18n(),
        manifest=Manifest(),
        month=make_month(yyyy_mm),
        month_params=params,
    )


def _section() -> MonthlySection:
    return MonthlySection(
        section_name="monthly",
        i18n=_i18n(),
        configurator=make_configurator(),
        month_params=_MONTH_PARAMS,
    )


def _generate(dto) -> str:
    return Generate(i18n=_i18n()).generate(dto)


def _month_pages(typst_src: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for page in typst_src.split("#pagebreak()"):
        if "January<month-2026-01-01>" in page:
            found["january"] = page
        if "August<month-2026-08-01>" in page:
            found["august"] = page
    return found


def test_january_keeps_full_weekdays_and_five_body_rows():
    content = _page("2026-01").content()
    assert "rows: (auto, auto, 1fr)" in content
    assert "rows: (regular_height, 16mm, 16mm, 16mm, 16mm, 16mm)" in content
    for name in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"):
        assert f"align(center + horizon)[{name}]" in content
    assert "align(center + horizon)[Mon]" not in content


def test_august_2026_is_six_rows_on_one_page():
    page = _page("2026-08")
    content = page.content()
    weeks = page._month_in_weeks()
    assert len(weeks) == 6
    assert "rows: (auto, auto, 1fr)" in content
    assert "rows: (regular_height, 16mm, 16mm, 16mm, 16mm, 16mm, 16mm)" in content
    assert content.count("rotate(90deg") == 6


def test_week_rail_is_number_only():
    content = _page("2026-01").content()
    assert "Week 1" not in content
    assert "Week 5" not in content
    assert "[Week " not in content
    assert "rotate(90deg, reflow: true)[#[1]]" in content
    assert "rotate(90deg, reflow: true)[#[5]]" in content


def test_day_numbers_sit_unboxed_in_the_corner():
    content = _page("2026-01").content()
    assert INNER_DAY_BOX not in content
    assert "grid.cell(align: top + left, inset: 3pt, [#[1]])" in content
    assert "grid.cell(align: top + left, inset: 3pt, [#[31]])" in content
    assert "grid.cell(fill: black" not in content


def test_notes_are_thin_rule_plus_pattern_without_label():
    content = _page("2026-01").content()
    assert "monthly_notes" not in content
    assert "Notes" not in content
    assert "thick_stroke" not in content
    assert "grid.hline(stroke: regular_stroke + black)" in content
    assert "rect_pattern(dotted)" in content


def test_title_is_year_slash_month_crumb_and_kills_calendar_chip():
    manifest = Manifest()
    manifest.register_source(Annual.ID)
    pages = _section().pages(manifest)
    assert len(pages) == 12
    year_cell = manifest.link_or_content(Annual.ID, "2026")
    names = (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )
    for index, page in enumerate(pages):
        month_id = f"month-2026-{index + 1:02d}-01"
        assert page.nav_links == []
        assert page.show_quarters is True
        assert len(page.highlight_months) == 1
        assert page.highlight_months[0].id == month_id
        assert page.highlight_quarters == []
        assert f"text(size: h1, {year_cell})" in page.title
        assert "text(size: h1)[/]" in page.title
        assert f"{names[index]}<{month_id}>" in page.title
        assert "Calendar" not in page.title
        assert "Calendar" not in page.content
        assert "monthly_notes" not in page.content
        assert "Notes" not in page.content
        assert INNER_DAY_BOX not in page.content
        assert "Week " not in page.content


def test_generated_year_crumb_links_to_annual_and_inverts_only_the_month():
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), _BULKY)
    typst = _generate(parse_toml(text, source="nomad-monthly.toml"))
    pages = _month_pages(typst)
    jan = pages["january"]
    aug = pages["august"]
    assert "padded_link(<annual>)[2026]" in jan
    assert "text(size: h1)[/]" in jan
    assert "January<month-2026-01-01>" in jan
    assert jan.count("Calendar") == 0
    assert "Calendar" not in jan
    assert "monthly_notes" not in jan
    assert "Notes" not in jan
    assert INNER_DAY_BOX not in jan
    assert "Week 1" not in jan
    assert "rotate(90deg, reflow: true)[#padded_link(<2026W01>)[1]]" in jan
    assert "table.cell(fill: black, text(white)[#padded_link(<month-2026-01-01>)[Jan]])" in jan
    assert "table.cell(fill: black, text(white)[#padded_link(<quarter-2026-1>)[Q1]])" not in jan
    assert "table.cell([#padded_link(<quarter-2026-1>)[Q1]])" in jan
    assert "Q1" in jan and "Q4" in jan
    assert "August<month-2026-08-01>" in aug
    assert aug.count("rotate(90deg") == 6
    assert "rows: (auto, auto, 1fr)" in aug
    month_slices = [page for page in typst.split("#pagebreak()") if "August<month-2026-08-01>" in page]
    assert len(month_slices) == 1


def test_six_row_august_compiles_as_one_pdf_page(tmp_path):
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), _MONTHLY_ONLY)
    typst = _generate(parse_toml(text, source="nomad-monthly-only.toml"))
    crumbs = [
        page
        for page in typst.split("#pagebreak()")
        if "text(size: h1)[/" in page and "<month-2026-" in page
    ]
    assert len(crumbs) == 12
    august = next(page for page in crumbs if "August<month-2026-08-01>" in page)
    assert "rows: (regular_height, 16mm, 16mm, 16mm, 16mm, 16mm, 16mm)" in august
    pdf, stderr = compile_pdf(typst, tmp_path / "monthly-year")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr
    if shutil.which("pdfinfo") is None:
        return
    info = subprocess.run(
        ["pdfinfo", str(pdf)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    pages_line = next(line for line in info.splitlines() if line.startswith("Pages:"))
    assert int(pages_line.split(":")[1]) == 12
