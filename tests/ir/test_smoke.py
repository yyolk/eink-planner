import re
import zlib

from parch.config import load
from parch.i18n import I18n
from parch.ir.fpdf import render_fpdf
from parch.ir.mos import build_planner
from parch.ir.typst import render_typst
from tests.helpers import base_config
from tests.toml_fixtures import short_january


def _page_count(data: bytes) -> int:
    counts = [int(m) for m in re.findall(rb"/Count\s+(\d+)", data)]
    if counts:
        return max(counts)
    return len(re.findall(rb"/Type\s*/Page(?!s)", data))


def test_build_planner_and_render_typst_short_january():
    dto = short_january(load(base_config("supernote-nomad")))
    doc = build_planner(dto, I18n.load_default())
    src = render_typst(doc)
    assert src.count("#pagebreak()") == len(doc.pages) - 1
    assert "padded_link" in src
    assert "<annual>" in src
    assert "scratch_pad" in src
    assert "#set page" in src
    ids = [p.id for p in doc.pages]
    assert ids[0] is None
    assert "annual" in ids
    assert "month-2026-01-01" in ids
    assert "2026-01-01" in ids


def test_ir_fpdf2_short_pdf(tmp_path):
    dto = short_january(load(base_config("supernote-nomad")))
    doc = build_planner(dto, I18n.load_default())
    dest = render_fpdf(doc, tmp_path / "index.pdf")
    data = dest.read_bytes()
    assert data.startswith(b"%PDF")
    box = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", data)
    assert box is not None
    assert abs(float(box.group(3)) - 336.96) < 0.2
    assert abs(float(box.group(4)) - 449.28) < 0.2
    assert _page_count(data) == len(doc.pages)
    assert b"/Annot" in data or b"/Dest" in data


def test_ir_fpdf2_menu_stays_7pt_after_cover(tmp_path):
    """Cover is 36pt. rotation() restores that size; menu labels must stay 7pt."""
    dto = short_january(load(base_config("supernote-nomad")))
    doc = build_planner(dto, I18n.load_default())
    dest = render_fpdf(doc, tmp_path / "index.pdf")
    data = dest.read_bytes()
    streams = re.findall(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S)
    assert len(streams) >= 2
    annual = zlib.decompress(streams[1]).decode("latin1")
    assert "/F1 7.00 Tf" in annual
    assert "/F1 36.00 Tf" not in annual
    assert "(Q1)" in annual
    assert "(Jan)" in annual
