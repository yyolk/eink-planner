"""Monthly pages: January title, MOS invert, unboxed days, leftover notes."""

import shutil
import subprocess

from parch.compose.page_data import HeadingMark
from parch.i18n import I18n
from parch.mos.manifest import Manifest
from parch.mos.pages.monthly import Monthly
from parch.sections.annual import Annual
from parch.sections.monthly import Monthly as MonthlySection
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.helpers import base_config, load_default, make_configurator, make_month
from tests.test_toml_omit_sections import compile_pdf
from tests.toml_fixtures import omit_toml_sections

NOMAD = base_config("supernote-nomad")

_MONTH_PARAMS = {
    "week_placement": "left",
    "week_label_rotation": "90deg",
    "daily_cell_height": "16mm",
}

_BULKY = (
    "index",
    "daily",
    "daily_notes",
    "colophon",
    "projects",
    "habits",
    "review",
    "tasks",
    "meetings",
)
_MONTHLY_ONLY = _BULKY + ("cover", "annual", "quarterly", "weekly")

INNER_DAY_BOX = "box(stroke: regular_stroke, inset: 3pt)"


def _i18n() -> I18n:
    return load_default()


def _page(yyyy_mm: str, week_placement: str = "left", side: str = "left") -> Monthly:
    params = {**_MONTH_PARAMS, "week_placement": week_placement}
    return Monthly(
        i18n=_i18n(),
        manifest=Manifest(),
        month=make_month(yyyy_mm),
        month_params=params,
        side=side,
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
    assert "month_weeks(left," in content
    well = content[content.index("month_weeks(") :]
    assert "rows: (regular_height,) + (1fr,) * 5" in well
    assert "16mm" not in well
    assert "(1fr,) * 6" not in well
    assert "columns: (regular_height" not in well
    assert "stroke:" not in well
    assert "block(" not in well
    assert "layout(" not in content
    assert "grid.hline(y: 1, stroke: regular_stroke + black)" in content
    assert "rows: (1fr, 1fr)" in content
    assert "rows: (1fr, auto, 1fr)" not in content
    assert "rows: (auto, auto, 1fr)" not in content
    assert (
        "[], align(center + horizon)[M], align(center + horizon)[T], "
        "align(center + horizon)[W], align(center + horizon)[T], "
        "align(center + horizon)[F], align(center + horizon)[S], "
        "align(center + horizon)[S]"
    ) in content
    assert "align(center + horizon)[Monday]" not in content
    assert "align(center + horizon)[Mon]" not in content
    assert not hasattr(_page("2026-01"), "_with_week_column")


def test_hand_right_still_emits_week_first():
    content = _page("2026-01", side="right").content()
    assert "month_weeks(right," in content
    assert "rows: (regular_height,) + (1fr,) * 5" in content
    assert "[], align(center + horizon)[M]" in content
    assert "align(center + horizon)[S], []" not in content
    assert "month_weeks(left," not in content
    assert "columns: (regular_height" not in content


def test_week_placement_none_is_seven_col_without_side():
    content = _page("2026-01", week_placement="none").content()
    assert "month_weeks(" not in content
    assert "block(\n    width: 100%,\n    height: 1fr,\n    grid(" in content
    assert "columns: (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr)" in content
    assert "rows: (regular_height,) + (1fr,) * 5" in content
    assert "16mm" not in content
    assert "align(center + horizon)[M]" in content
    assert "align(center + horizon)[Monday]" not in content
    assert "rotate(90deg" not in content
    notes = content[content.index("lined_well") :]
    assert "block(" not in notes
    assert "lined_well(dotted_centered)" in notes
    assert "layout(" not in content
    assert "grid.hline(y: 1, stroke: regular_stroke + black)" in content
    assert "rows: (1fr, 1fr)" in content


def test_august_2026_is_six_rows_on_one_page():
    page = _page("2026-08")
    content = page.content()
    weeks = page._month_in_weeks()
    assert len(weeks) == 6
    assert "layout(" not in content
    assert "rows: (1fr, 1fr)" in content
    assert "grid.hline(y: 1, stroke: regular_stroke + black)" in content
    assert "rows: (regular_height,) + (1fr,) * 6" in content
    assert "rows: (1fr, auto, 1fr)" not in content
    assert "rows: (auto, auto, 1fr)" not in content
    assert content.count("rotate(90deg") == 6


def test_week_rail_is_number_only():
    content = _page("2026-01").content()
    assert "Week 1" not in content
    assert "Week 5" not in content
    assert "[Week " not in content
    assert "rotate(90deg)[#[1]]" in content
    assert "rotate(90deg)[#[5]]" in content


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
    assert "grid.hline(y: 1, stroke: regular_stroke + black)" in content
    assert "lined_well(dotted_centered)" in content
    notes = content[content.index("lined_well") :]
    assert "block(" not in notes
    assert "layout(" not in content


def test_title_is_month_without_year_and_kills_calendar_chip():
    manifest = Manifest()
    manifest.register_source(Annual.ID)
    pages = _section().pages(manifest)
    assert len(pages) == 12
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
        assert page.nav_links is not None
        assert page.heading_mark is HeadingMark.LEAD
        assert page.show_quarters is True
        assert len(page.highlight_months) == 1
        assert page.highlight_months[0].id == month_id
        assert page.highlight_quarters == []
        assert "padded_link(<annual>)" not in page.title
        assert "2026 /" not in page.title
        assert "text(size: h1)[/]" not in page.title
        assert page.title == f"text(size: h1)[{names[index]}<{month_id}>]"
        assert "Calendar" not in page.title
        assert "Calendar" not in page.content
        assert "monthly_notes" not in page.content
        assert "Notes" not in page.content
        assert INNER_DAY_BOX not in page.content
        assert "Week " not in page.content


def test_generated_title_is_january_without_year_and_inverts_only_the_month():
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), _BULKY)
    typst = _generate(parse_toml(text, source="nomad-monthly.toml"))
    pages = _month_pages(typst)
    jan = pages["january"]
    aug = pages["august"]
    assert "padded_link(<annual>)[2026]" not in jan
    assert "2026 /" not in jan
    assert "text(size: h1)[/]" not in jan
    assert "text(size: h1)[January<month-2026-01-01>]" in jan
    assert "January<month-2026-01-01>" in jan
    assert jan.count("Calendar") == 0
    assert "Calendar" not in jan
    assert "monthly_notes" not in jan
    assert "Notes" not in jan
    assert INNER_DAY_BOX not in jan
    assert "Week 1" not in jan
    assert "rotate(90deg)[#padded_link(<2026W01>)[1]]" in jan
    assert "table.cell(fill: black, text(white)[#padded_link(<month-2026-01-01>)[Jan]])" in jan
    assert "table.cell(fill: black, text(white)[#padded_link(<quarter-2026-1>)[Q1]])" not in jan
    assert "table.cell([#padded_link(<quarter-2026-1>)[Q1]])" in jan
    assert "Q1" in jan and "Q4" in jan
    assert "August<month-2026-08-01>" in aug
    assert aug.count("rotate(90deg") == 6
    assert "rows: (1fr, 1fr)" in aug
    assert "grid.hline(y: 1, stroke: regular_stroke + black)" in aug
    assert "layout(" not in aug
    assert "rows: (regular_height,) + (1fr,) * 6" in aug
    month_slices = [page for page in typst.split("#pagebreak()") if "August<month-2026-08-01>" in page]
    assert len(month_slices) == 1


def test_six_row_august_compiles_as_one_pdf_page(tmp_path):
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), _MONTHLY_ONLY)
    typst = _generate(parse_toml(text, source="nomad-monthly-only.toml"))
    crumbs = [
        page
        for page in typst.split("#pagebreak()")
        if "text(size: h1)[" in page and "<month-2026-" in page
    ]
    assert len(crumbs) == 12
    august = next(page for page in crumbs if "August<month-2026-08-01>" in page)
    assert "rows: (regular_height,) + (1fr,) * 6" in august
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
