"""Quarter pages render all three months in a bounded column grid."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from eink_planner.i18n import I18n
from eink_planner.kdl_config import parse_kdl
from eink_planner.mos.manifest import Manifest
from eink_planner.mos.pages.quarterly import Quarterly
from eink_planner.services.generate import Generate
from tests.helpers import make_quarter
from tests.test_kdl_omit_sections import compile_pdf, omit_kdl_sections

REPO = Path(__file__).resolve().parents[2]
CONFIGS = REPO / "configs"
MOS_LEFT = CONFIGS / "158x210-mos-left.kdl"
MOS_RIGHT = CONFIGS / "158x210-mos-right.kdl"
NOMAD = CONFIGS / "supernote-nomad.kdl"
NOMAD_MOS_RIGHT = CONFIGS / "supernote-nomad-mos-right.kdl"

Q1_MONTHS = ("January", "February", "March")
Q3_MONTHS = ("July", "August", "September")

_BULKY = ("annual", "monthly", "weekly", "daily", "daily-notes", "colophon")


def _i18n() -> I18n:
    return I18n.load_default(REPO, "en")


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


def _full_year_quarters(config_path: Path):
    text = omit_kdl_sections(config_path.read_text(encoding="utf-8"), _BULKY)
    return parse_kdl(text, source=f"{config_path.name}-quarters.kdl")


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
    assert content.index("scratch_pad") < content.index("rows: (1fr, 1fr, 1fr)")
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


def test_mos_left_and_mos_right_q3_compile_with_three_months(tmp_path):
    """Compile a real 2026 Q1-Q4 set so a July-only Q3 cannot slip through."""
    for name, config in (("mos-left", MOS_LEFT), ("mos-right", MOS_RIGHT), ("nomad-mos-right", NOMAD_MOS_RIGHT)):
        typst_src = _generate(_full_year_quarters(config))
        q3 = _quarter_pages(typst_src)[3]
        for month in Q3_MONTHS:
            assert f"[{month}]" in q3
        pdf, stderr = compile_pdf(typst_src, tmp_path / name)
        assert pdf.is_file() and pdf.stat().st_size > 0, stderr
        extracted = subprocess.run(
            ["pdftotext", "-layout", str(pdf), "-"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        q3_pdf = next(page for page in extracted.split("\x0c") if "Quarter 3" in page)
        for month in Q3_MONTHS:
            assert month in q3_pdf, f"{name} Q3 PDF missing {month}"
