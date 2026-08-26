"""Short-leash Projects card-baseline raster checks; drop with tests/visual.py if design moves."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from eink_planner.i18n import I18n
from eink_planner.services.generate import Generate
from eink_planner.toml_config import parse_toml
from tests.test_toml_omit_sections import _LABEL_DEF, compile_pdf
from tests.toml_fixtures import _minimal
from tests.visual import card_interior_lines, raster_page

REPO = Path(__file__).resolve().parents[1]
_DPI = 200
_GAP_PX = 3
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
    return Generate(i18n=I18n.load_default(REPO, "en")).generate(dto)


def _board_png(tmp_path: Path, device: str, stem: str) -> Path:
    dto = parse_toml(
        _minimal(enable=["projects"], sections="", device=device),
        source=f"{stem}.toml",
    )
    typst = _generate(dto)
    pdf, stderr = compile_pdf(typst, tmp_path / stem)
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr
    page = next(
        i
        for i, chunk in enumerate(typst.split("#pagebreak()"), start=1)
        if "project-1" in _LABEL_DEF.findall(chunk)
    )
    return raster_page(pdf, page, tmp_path / f"{stem}-board.png", dpi=_DPI)


def _assert_card_baselines(png: Path) -> None:
    with Image.open(png) as src:
        width = src.size[0]
        gray = src.convert("L")
        pixels = gray.load()
    for frac in _COL_FRACS:
        x = int(width * frac)
        cards = card_interior_lines(png, x)
        assert len(cards) == 5, (frac, cards)
        for card in cards:
            top, *interiors, bottom = card
            assert len(interiors) == 3, card
            thicknesses = [band[2] for band in interiors]
            assert all(1 <= t <= 2 for t in thicknesses), thicknesses
            assert max(thicknesses) - min(thicknesses) <= 1, thicknesses
            gap = bottom[0] - interiors[-1][1]
            assert gap >= _GAP_PX, f"last interior stacked on frame: gap={gap} card={card}"
            assert interiors[-1][1] + 1 < bottom[0]
            for y0, y1, _thick in interiors:
                vals = [pixels[x, y] for y in range(y0, y1 + 1)]
                assert vals and max(vals) <= 64, (frac, y0, vals)
            assert top[2] <= 2 and bottom[2] <= 2, card


def test_nomad_card_baselines_do_not_stack(tmp_path):
    png = _board_png(tmp_path, _NOMAD, "nomad")
    _assert_card_baselines(png)


def test_scribe_card_baselines_do_not_stack(tmp_path):
    png = _board_png(tmp_path, _SCRIBE, "scribe")
    _assert_card_baselines(png)
