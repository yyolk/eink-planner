"""Quarter pages render all three months in a bounded column grid."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

from parch.compose.page_data import HeadingMark
from parch.i18n import I18n
from parch.toml_config import parse_toml
from parch.mos.manifest import Manifest
from parch.mos.pages.quarterly import Quarterly
from parch.sections.annual import Annual
from parch.sections.quarterly import Quarterly as QuarterlySection
from parch.services.generate import Generate
from tests.helpers import base_config, load_default, make_configurator, make_quarter
from tests.test_toml_omit_sections import compile_pdf
from tests.toml_fixtures import omit_toml_sections

MOS_LEFT = base_config("158x210-mos-left")
MOS_RIGHT = base_config("158x210-mos-right")
NOMAD = base_config("supernote-nomad")
NOMAD_MOS_RIGHT = base_config("supernote-nomad-mos-right")

Q1_MONTHS = ("January", "February", "March")
Q3_MONTHS = ("July", "August", "September")

_BULKY = ("index", "annual", "monthly", "weekly", "daily", "daily_notes", "colophon")


def _i18n() -> I18n:
    return load_default()


def _little_calendar() -> dict:
    return {"week_placement": "left", "inset": "5pt", "show_month_name": True}


def _page(date_str: str, months_column: str = "left") -> Quarterly:
    return Quarterly(
        i18n=_i18n(),
        manifest=Manifest(),
        quarter=make_quarter(date_str),
        months_column=months_column,
        little_calendar=_little_calendar(),
    )


def _section() -> QuarterlySection:
    return QuarterlySection(
        section_name="quarterly",
        i18n=_i18n(),
        configurator=make_configurator(),
        months_column="left",
        little_calendar=_little_calendar(),
    )


def _full_year_quarters(config_path: Path):
    text = omit_toml_sections(config_path.read_text(encoding="utf-8"), _BULKY)
    return parse_toml(text, source=f"{config_path.name}-quarters.toml")


def _generate(dto) -> str:
    return Generate(i18n=_i18n()).generate(dto)


def _quarter_pages(typst_src: str) -> dict[int, str]:
    pages = typst_src.split("#pagebreak()")
    found: dict[int, str] = {}
    for page in pages:
        for number in (1, 2, 3, 4):
            if f"Quarter {number} <quarter-2026-{number}>" in page:
                found[number] = page
    return found


def test_q1_emits_three_equal_month_rows():
    content = _page("2026-01-01").content()
    assert "rows: (1fr, 1fr, 1fr)" in content
    assert "stack(" not in content
    for name in Q1_MONTHS:
        assert f"[{name}]" in content
    assert content.count("colspan:") == 3


def test_q3_emits_july_august_september():
    content = _page("2026-07-01").content()
    assert "rows: (1fr, 1fr, 1fr)" in content
    for name in Q3_MONTHS:
        assert f"[{name}]" in content
    for name in Q1_MONTHS:
        assert f"[{name}]" not in content
    assert content.count("colspan:") == 3


def test_months_column_right_keeps_three_month_grid():
    content = _page("2026-07-01", months_column="right").content()
    assert content.index("rect_pattern(dotted)") < content.index("rows: (1fr, 1fr, 1fr)")
    assert "columns: (3fr,2fr)" in content
    for name in Q3_MONTHS:
        assert f"[{name}]" in content


@pytest.mark.parametrize("path", [MOS_LEFT, MOS_RIGHT, NOMAD, NOMAD_MOS_RIGHT])
def test_full_year_quarter_pages_include_all_three_months(path: Path):
    typst_src = _generate(_full_year_quarters(path))
    pages = _quarter_pages(typst_src)
    assert set(pages) == {1, 2, 3, 4}
    expected = {
        1: Q1_MONTHS,
        2: ("April", "May", "June"),
        3: Q3_MONTHS,
        4: ("October", "November", "December"),
    }
    for number, months in expected.items():
        page = pages[number]
        assert "rows: (1fr, 1fr, 1fr)" in page
        assert "dir: ttb" not in page
        for name in months:
            assert f"[{name}]" in page, f"Q{number} missing {name} in {path.name}"
        assert page.count("colspan:") == 3
        assert "Calendar" not in page
        assert "2026 /" not in page
        assert "text(size: h1)[/]" not in page
        assert f"Quarter {number} <quarter-2026-{number}>" in page
        assert "[], [M], [T], [W], [T], [F], [S], [S]" in page
        assert "[W], [M], [T], [W], [T], [F], [S], [S]" not in page


def test_shipped_profiles_q3_compile_with_three_months(tmp_path):
    """Compile a real 2026 Q1-Q4 set for all shipped MOS profiles so a July-only Q3 cannot slip through."""
    pdfs = []
    for name, config in (("mos-left", MOS_LEFT), ("mos-right", MOS_RIGHT), ("nomad", NOMAD), ("nomad-mos-right", NOMAD_MOS_RIGHT)):
        typst_src = _generate(_full_year_quarters(config))
        q3 = _quarter_pages(typst_src)[3]
        for month in Q3_MONTHS:
            assert f"[{month}]" in q3
        pdf, stderr = compile_pdf(typst_src, tmp_path / name)
        assert pdf.is_file() and pdf.stat().st_size > 0, stderr
        pdfs.append((name, pdf))
    if shutil.which("pdftotext") is None:
        pytest.skip("pdftotext not on PATH")
    for name, pdf in pdfs:
        extracted = subprocess.run(
            ["pdftotext", "-layout", str(pdf), "-"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        q3_pdf = next(page for page in extracted.split("\x0c") if "Quarter 3" in page)
        for month in Q3_MONTHS:
            assert month in q3_pdf, f"{name} Q3 PDF missing {month}"


def test_title_is_quarter_without_year_and_kills_calendar_chip():
    manifest = Manifest()
    manifest.register_source(Annual.ID)
    pages = _section().pages(manifest)
    assert len(pages) == 4
    for number, page in enumerate(pages, start=1):
        assert page.nav_links == []
        assert page.nav_links is not None
        assert page.heading_mark is HeadingMark.LEAD
        assert page.highlight_months == []
        assert len(page.highlight_quarters) == 1
        assert page.highlight_quarters[0].number == number
        assert "padded_link(<annual>)" not in page.title
        assert "2026 /" not in page.title
        assert "text(size: h1)[/]" not in page.title
        assert page.title == f'text(size: h1)[Quarter {number} <quarter-2026-{number}>]'
        assert "Calendar" not in page.title
        assert "Calendar" not in page.content


def test_little_calendars_omit_week_letter():
    content = _page("2026-01-01").content()
    assert "[], [M], [T], [W], [T], [F], [S], [S]" in content
    assert "[W], [M], [T], [W], [T], [F], [S], [S]" not in content


def test_week_letter_stays_off_when_little_calendar_sets_true():
    page = Quarterly(
        i18n=_i18n(),
        manifest=Manifest(),
        quarter=make_quarter("2026-01-01"),
        months_column="left",
        little_calendar={**_little_calendar(), "show_week_letter": True},
    )
    content = page.content()
    assert "[], [M], [T], [W], [T], [F], [S], [S]" in content
    assert "[W], [M], [T], [W], [T], [F], [S], [S]" not in content


def test_generated_title_is_quarter_without_year():
    skip = ("monthly", "weekly", "daily", "daily_notes", "colophon", "projects", "habits", "review", "tasks", "meetings")
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), skip)
    typst = _generate(parse_toml(text, source="nomad-q-annual.toml"))
    pages = _quarter_pages(typst)
    q1 = pages[1]
    assert "padded_link(<annual>)[2026]" not in q1
    assert "2026 /" not in q1
    assert "text(size: h1)[/]" not in q1
    assert "text(size: h1)[Quarter 1 <quarter-2026-1>]" in q1
    assert "Calendar" not in q1
    assert q1.count("Calendar") == 0

