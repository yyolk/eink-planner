"""Raster check that the cover year sits in the upper third."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from parch.i18n import I18n
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.test_toml_omit_sections import SECTIONS, compile_pdf
from tests.toml_fixtures import omit_toml_sections
from tests.visual import ink_bbox, raster_page

REPO = Path(__file__).resolve().parents[1]
NOMAD = REPO / "configs/supernote-nomad.toml"
_DPI = 200
_OTHERS = [name for name in SECTIONS if name != "cover"]


def _generate(dto) -> str:
    return Generate(i18n=I18n.load_default(REPO, "en")).generate(dto)


def test_cover_year_sits_in_upper_third(tmp_path):
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), _OTHERS)
    dto = parse_toml(text, source="visual-cover.toml")
    typst = _generate(dto)
    pdf, stderr = compile_pdf(typst, tmp_path / "cover")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr
    png = raster_page(pdf, 1, tmp_path / "cover.png", dpi=_DPI)
    with Image.open(png) as src:
        height = src.size[1]
    box = ink_bbox(png)
    assert box is not None
    _x0, y0, _x1, y1 = box
    center = (y0 + y1) / 2
    assert center < height / 3, (box, height, center)
    assert y1 < height * 0.5, (box, height)
