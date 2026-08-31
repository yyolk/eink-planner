"""Short-leash Meetings raster checks; drop with tests/visual.py if design moves."""

from pathlib import Path

from PIL import Image

from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.test_toml_omit_sections import _LABEL_DEF, compile_pdf
from tests.toml_fixtures import _minimal
from tests.visual import full_width_bands, ink_bbox, raster_page
from tests.helpers import load_default

_DPI = 200

_NOMAD = """[device]
name = "supernote-nomad"
width = "118.87mm"
height = "158.5mm"
ppi = 300"""


def _generate(dto) -> str:
    return Generate(i18n=load_default()).generate(dto)


def _meetings_pdf(tmp_path: Path) -> tuple[Path, str]:
    dto = parse_toml(
        _minimal(enable=["meetings"], sections="", device=_NOMAD),
        source="visual-meetings.toml",
    )
    typst = _generate(dto)
    pdf, stderr = compile_pdf(typst, tmp_path / "meetings")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr
    return pdf, typst


def _page_index(typst: str, label: str) -> int:
    return next(
        i
        for i, chunk in enumerate(typst.split("#pagebreak()"), start=1)
        if label in _LABEL_DEF.findall(chunk)
    )


def test_nomad_index_numbers_left_no_arrows(tmp_path):
    pdf, typst = _meetings_pdf(tmp_path)
    page = _page_index(typst, "meetings")
    png = raster_page(pdf, page, tmp_path / "index.png", dpi=_DPI)
    with Image.open(png) as src:
        width, height = src.size
        gray = src.convert("L")
        pixels = gray.load()
    box = ink_bbox(png)
    assert box is not None
    x0, y0, x1, y1 = box
    # Numbers sit toward the left; write-in paper is empty. No year chip.
    assert x0 < width * 0.22, box
    assert y0 < height * 0.20, box
    # 16x1fr bands eat leftover height; last rule sits near the page bottom.
    assert y1 > height * 0.82, box
    # Numbers occupy a left column: ink in the first ~18% but not a full-band arrow.
    left_ink = 0
    mid_ink = 0
    right_ink = 0
    left_x1 = int(width * 0.18)
    mid_x0, mid_x1 = int(width * 0.35), int(width * 0.70)
    right_x0 = int(width * 0.82)
    for y in range(int(height * 0.18), int(height * 0.92)):
        if any(pixels[x, y] <= 64 for x in range(8, left_x1)):
            left_ink += 1
        if any(pixels[x, y] <= 64 for x in range(mid_x0, mid_x1)):
            mid_ink += 1
        if any(pixels[x, y] <= 64 for x in range(right_x0, width - 4)):
            right_ink += 1
    assert left_ink > 20, left_ink
    # Write-in is paper; row rules may tick mid, but no full-width arrow heads on the right.
    assert right_ink < left_ink * 0.6, (right_ink, left_ink)
    bands = full_width_bands(png, x0_frac=0.08, coverage=0.70)
    thick = [b for b in bands if b[2] >= 4]
    assert not thick, thick


def test_nomad_meeting_notes_dotted_topics_have_ticks(tmp_path):
    pdf, typst = _meetings_pdf(tmp_path)
    page = _page_index(typst, "meeting-1")
    png = raster_page(pdf, page, tmp_path / "meeting.png", dpi=_DPI)
    bands = full_width_bands(png, x0_frac=0.10, coverage=0.70)
    thick = [b for b in bands if b[2] >= 4]
    # House-dot notes and tick baselines: no boxed table frame.
    assert not thick, thick
    with Image.open(png) as src:
        width, height = src.size
        gray = src.convert("L")
        pixels = gray.load()
    # Topics/actions: left tick gutter — a column of ink that is not full-width.
    gutter_x = int(width * 0.08)
    mid_x = int(width * 0.50)
    gutter_hits = 0
    mid_hits = 0
    for y in range(int(height * 0.18), int(height * 0.42)):
        if pixels[gutter_x, y] <= 64:
            gutter_hits += 1
        if pixels[mid_x, y] <= 64:
            mid_hits += 1
    assert gutter_hits > 0
    # Mid-page topic write-ins are ruled but not a solid fill.
    assert mid_hits < (height * 0.24)
