"""Raster check that December Friday week rules are thicker than the grid."""

from __future__ import annotations

from pathlib import Path
from statistics import median

from eink_planner.i18n import I18n
from eink_planner.services.generate import Generate
from eink_planner.toml_config import parse_toml
from tests.test_toml_omit_sections import compile_pdf
from tests.toml_fixtures import _minimal
from tests.visual import full_width_bands, raster_page

REPO = Path(__file__).resolve().parents[1]
_DEC_PAGE = 13  # habits-only: index, Jan…Dec
_DPI = 200  # 0.4mm ≈ 3.1px; regular 0.3pt ≈ 0.8px
_THICK_PX = 3


def _generate(dto) -> str:
    return Generate(i18n=I18n.load_default(REPO, "en")).generate(dto)


def test_december_friday_rules_are_thicker_than_grid(tmp_path):
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="visual-habits.toml")
    typst = _generate(dto)
    pdf, stderr = compile_pdf(typst, tmp_path / "habits-year")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr
    png = raster_page(pdf, _DEC_PAGE, tmp_path / "december.png", dpi=_DPI)
    bands = full_width_bands(png)
    thick = [b for b in bands if b[2] >= _THICK_PX]
    thicknesses = [b[2] for b in thick]
    assert len(thick) == 4, f"expected 4 Friday rules (4/11/18/25), got {thick}"
    assert max(thicknesses) - min(thicknesses) <= 1, thicknesses
    ones = [b[2] for b in bands if b[2] == 1]
    if ones:
        assert min(thicknesses) > median(ones)
