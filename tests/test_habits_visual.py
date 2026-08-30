"""Raster check that habit day rules are even and thin."""

from __future__ import annotations

from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.test_toml_omit_sections import compile_pdf
from tests.toml_fixtures import _minimal
from tests.visual import full_width_bands, raster_page
from tests.helpers import load_default

_INDEX_PAGE = 1
_DEC_PAGE = 13  # habits-only: index, Jan…Dec
_DPI = 200
_THICK_PX = 3


def _generate(dto) -> str:
    return Generate(i18n=load_default()).generate(dto)


def test_december_day_rules_are_even_and_thin(tmp_path):
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="visual-habits.toml")
    typst = _generate(dto)
    pdf, stderr = compile_pdf(typst, tmp_path / "habits-year")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr
    png = raster_page(pdf, _DEC_PAGE, tmp_path / "december.png", dpi=_DPI)
    bands = full_width_bands(png)
    thick = [b for b in bands if b[2] >= _THICK_PX]
    assert not thick, f"expected no Friday bars, got {thick}"
    thin = [b for b in bands if b[2] <= 2]
    assert len(thin) >= 20, f"expected many thin day rules, got {thin}"


def test_index_has_no_full_width_rules(tmp_path):
    dto = parse_toml(_minimal(enable=["habits"], sections=""), source="visual-habits-index.toml")
    typst = _generate(dto)
    pdf, stderr = compile_pdf(typst, tmp_path / "habits-index")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr
    png = raster_page(pdf, _INDEX_PAGE, tmp_path / "index.png", dpi=_DPI)
    bands = full_width_bands(png)
    assert not bands, f"expected label bands without rules, got {bands}"
