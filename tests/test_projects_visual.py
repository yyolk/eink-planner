"""Short-leash Projects raster checks; drop with tests/visual.py if design moves."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.test_toml_omit_sections import _LABEL_DEF, compile_pdf
from tests.toml_fixtures import _minimal
from tests.visual import card_interior_lines, full_width_bands, ink_bbox, raster_page
from tests.helpers import load_default

_DPI = 200
_COL_FRACS = (0.20, 0.50, 0.80)

_NOMAD = """[device]
name = "supernote-nomad"
width = "118.87mm"
height = "158.5mm"
ppi = 300"""

_SCRIBE = """[device]
name = "kindle-scribe"
width = "157.48mm"
height = "209.97mm"
ppi = 300"""


def _generate(dto) -> str:
    return Generate(i18n=load_default()).generate(dto)


def _projects_pdf(tmp_path: Path, device: str, stem: str) -> tuple[Path, str]:
    dto = parse_toml(
        _minimal(enable=["projects"], sections="", device=device),
        source=f"{stem}.toml",
    )
    typst = _generate(dto)
    pdf, stderr = compile_pdf(typst, tmp_path / stem)
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr
    return pdf, typst


def _page_index(typst: str, label: str) -> int:
    return next(
        i
        for i, chunk in enumerate(typst.split("#pagebreak()"), start=1)
        if label in _LABEL_DEF.findall(chunk)
    )


def _assert_three_dotted_columns(png: Path) -> None:
    with Image.open(png) as src:
        width, height = src.size
        gray = src.convert("L")
        pixels = gray.load()
    y0 = int(height * 0.28)
    y1 = int(height * 0.92)
    col_ink = []
    for frac in _COL_FRACS:
        x = int(width * frac)
        hits = sum(1 for y in range(y0, y1) if pixels[x, y] <= 64)
        col_ink.append(hits)
        assert hits > 8, (frac, hits)
        assert hits < (y1 - y0) * 0.35, (frac, hits)
    # Columns are peers — house dots, not one fat done-column of ticks.
    assert max(col_ink) - min(col_ink) < max(12, int(max(col_ink) * 0.55)), col_ink
    for frac in _COL_FRACS:
        try:
            cards = card_interior_lines(png, int(width * frac))
        except AssertionError:
            continue
        raise AssertionError(f"framed cards still present at {frac}: {cards}")
    thick = [b for b in full_width_bands(png, x0_frac=0.10, coverage=0.70) if b[2] >= 4]
    assert not thick, thick


def test_nomad_index_numbers_left_no_year(tmp_path):
    pdf, typst = _projects_pdf(tmp_path, _NOMAD, "nomad-index")
    page = _page_index(typst, "projects")
    png = raster_page(pdf, page, tmp_path / "index.png", dpi=_DPI)
    with Image.open(png) as src:
        width, height = src.size
        gray = src.convert("L")
        pixels = gray.load()
    box = ink_bbox(png)
    assert box is not None
    x0, y0, x1, y1 = box
    assert x0 < width * 0.22, box
    assert y0 < height * 0.20, box
    left_ink = 0
    right_ink = 0
    left_x1 = int(width * 0.18)
    right_x0 = int(width * 0.82)
    for y in range(int(height * 0.18), int(height * 0.92)):
        if any(pixels[x, y] <= 64 for x in range(8, left_x1)):
            left_ink += 1
        if any(pixels[x, y] <= 64 for x in range(right_x0, width - 4)):
            right_ink += 1
    assert left_ink > 20, left_ink
    assert right_ink < left_ink * 0.6, (right_ink, left_ink)
    thick = [b for b in full_width_bands(png, x0_frac=0.08, coverage=0.70) if b[2] >= 4]
    assert not thick, thick


def test_nomad_board_is_three_dotted_columns(tmp_path):
    pdf, typst = _projects_pdf(tmp_path, _NOMAD, "nomad")
    chunk = next(
        c
        for c in typst.split("#pagebreak()")
        if "project-1" in _LABEL_DEF.findall(c)
    )
    assert "1/16" not in chunk
    assert "text(size: 0.85em)[1]" in chunk
    assert chunk.count("rect_pattern(dotted)") == 3
    page = _page_index(typst, "project-1")
    png = raster_page(pdf, page, tmp_path / "nomad-board.png", dpi=_DPI)
    _assert_three_dotted_columns(png)


def test_scribe_board_is_three_dotted_columns(tmp_path):
    pdf, typst = _projects_pdf(tmp_path, _SCRIBE, "scribe")
    page = _page_index(typst, "project-1")
    png = raster_page(pdf, page, tmp_path / "scribe-board.png", dpi=_DPI)
    _assert_three_dotted_columns(png)
