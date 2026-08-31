"""House Typst library: preamble #import, no inlined helper bodies, workdir copy."""

import zipfile
from pathlib import Path

from parch.config import load
from parch.mos.configurator import Configurator
from parch.mos.preamble import Preamble, copy_house_typ, house_typ_resource
from tests.helpers import base_config


def test_preamble_imports_house_and_does_not_inline_bodies():
    typst = Preamble(Configurator(load(base_config("158x210-mos-left")))).generate()
    assert '#import "house.typ"' in typst
    imported = typst[typst.index('#import "house.typ"') :].splitlines()[0]
    assert "contents_bars" in imported
    assert "lead_pair" in imported
    assert "trail_heading" in imported
    assert "mos_frame" in imported
    assert "well_frame" in imported
    assert "month_grid" in imported
    assert "week_matrix" in imported
    assert "week_cell" not in imported
    assert "#let link_padding =" in typst
    assert "#let rect_pattern = rect_pattern.with(regular_height: regular_height)" in typst
    assert "#let padded_link = padded_link.with(padding: link_padding)" in typst
    assert "#let contents_bars = contents_bars.with(thick_stroke: thick_stroke)" in typst
    assert "#let mos_frame = mos_frame.with(mos-width: 10mm, column-gutter: 2mm)" in typst
    assert "#let well_frame = well_frame.with(heading-height: 10mm, row-gutter: 2mm)" in typst
    assert "#let month_grid = month_grid.with(week-rows: 6, hline-stroke: regular_stroke + black)" in typst
    assert "#let week_matrix = week_matrix.with(regular-height: regular_height)" in typst
    assert "#let dotted = dotted(regular_height: regular_height)" in typst
    assert "#let lined = lined(regular_height: regular_height, regular_stroke: regular_stroke)" in typst
    assert "#let scratch_pad = rect_pattern(dotted)" in typst
    assert "here().position()" not in typst
    assert "link(target)[#box(inset: padding, content)]" not in typst
    assert "#let rect_pattern(pattern) = rect(" not in typst
    assert "#let padded_link(padding:" not in typst
    assert "0.7em.to-absolute()" not in typst
    assert "line(length: 0.844em, stroke: thick_stroke + black)" not in typst
    assert "let seated_title =" not in typst
    assert "measure(seated_title)" not in typst
    assert "columns: (auto, auto)" not in typst
    assert "column-gutter: 6pt" not in typst
    assert "columns: (10mm, 1fr)" not in typst
    assert "rows: (10mm, 1fr)" not in typst
    assert "rowspan" not in typst
    assert "align: center + horizon" not in typst
    assert "(auto, auto) + (1fr,)" not in typst
    assert "grid.hline(y: 1" not in typst
    assert "grid.hline(y: 2" not in typst
    # Little-calendar chrome lives in house.typ, not inlined as `rows: 1fr`.
    assert "rows: 1fr," not in typst
    assert "rows: 1fr\n" not in typst
    # Weekly 3×3 / week_cell chrome lives in house.typ, not the preamble.
    assert "columns: (1fr, 1fr, 1fr)" not in typst
    assert "rows: (1fr, 1fr, 1fr)" not in typst
    assert "grid.cell(colspan" not in typst
    assert "rows: (auto, 1fr)" not in typst
    assert 'bottom-edge: "descender"' not in typst
    assert "inset: (bottom: 0.25em)" not in typst
    house = house_typ_resource().read_text(encoding="utf-8")
    assert "#set page" not in house
    assert "#let contents_bars(" in house
    assert "#let lead_pair(" in house
    assert "#let lead_pair(mark, title, spacing: 6pt)" in house
    assert "#let lead_pair(left, right" not in house
    assert "#let trail_heading(" in house
    assert "#let mos_frame(" in house
    assert "#let well_frame(" in house
    assert "#let month_grid(" in house
    assert "rows: (auto, auto) + (1fr,) * week-rows" in house
    assert "grid.hline(y: 1, stroke: hline-stroke)" in house
    assert "grid.hline(y: 2, stroke: hline-stroke)" in house
    month_grid_sig = house[house.index("#let month_grid(") : house.index("..cells,")]
    assert "side" not in month_grid_sig
    assert "#let week_cell(" in house
    assert "#let week_matrix(" in house
    assert "rows: (auto, 1fr)" in house
    assert "columns: (1fr, 1fr, 1fr)" in house
    assert "rows: (1fr, 1fr, 1fr)" in house
    assert "grid.cell(colspan: 2," in house
    assert 'bottom-edge: "descender"' in house
    week_matrix_sig = house[house.index("#let week_matrix(") : house.index("..contents,")]
    assert "side" not in week_matrix_sig
    assert "row-gutter" not in week_matrix_sig
    assert "rowspan" not in house
    assert "dir: ltr" in house
    assert "calc.max(measure(seated_title).height, measure(seated_mark).height)" in house


def test_copy_house_typ_writes_workdir(tmp_path):
    dest = copy_house_typ(tmp_path)
    assert dest == tmp_path / "house.typ"
    assert dest.is_file()
    text = dest.read_text(encoding="utf-8")
    packaged = house_typ_resource().read_text(encoding="utf-8")
    assert text == packaged
    assert "#let rect_pattern(" in text
    assert "#let padded_link(" in text
    assert "#let contents_bars(" in text
    assert "#let lead_pair(" in text
    assert "#let trail_heading(" in text
    assert "#let mos_frame(" in text
    assert "#let well_frame(" in text
    assert "#let month_grid(" in text
    assert "#let week_matrix(" in text
    assert "#let week_cell(" in text


def test_press_copies_house_typ_next_to_index(tmp_path, monkeypatch):
    from parch.cli import generate_cmd
    from tests.toml_fixtures import _minimal

    path = tmp_path / "press.toml"
    path.write_text(_minimal(enable=["colophon"], sections=""), encoding="utf-8")

    class _DummyCompile:
        def compile(self, workdir, file="index.typst", **_kwargs):
            pdf = Path(workdir) / "index.pdf"
            pdf.write_bytes(b"%PDF-dummy")
            return pdf

    monkeypatch.setattr("parch.cli.Compile", lambda: _DummyCompile())
    ns = type(
        "Args",
        (),
        {
            "config": str(path),
            "workdir": str(tmp_path / "out"),
            "locale": "en",
            "with_ghostscript": False,
            "debug": False,
            "year": None,
        },
    )()
    assert generate_cmd(ns, argv=["parch", "press", str(path)]) == 0
    workdir = tmp_path / "out"
    assert (workdir / "house.typ").is_file()
    index = (workdir / "index.typst").read_text(encoding="utf-8")
    assert '#import "house.typ"' in index
    assert (workdir / "house.typ").read_text(encoding="utf-8") == house_typ_resource().read_text(
        encoding="utf-8"
    )


def test_wheel_includes_house_typ(tmp_path):
    import subprocess

    result = subprocess.run(
        ["uv", "build", "--wheel", "-o", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    wheels = list(tmp_path.glob("*.whl"))
    assert wheels, result.stdout
    with zipfile.ZipFile(wheels[0]) as zf:
        names = zf.namelist()
    assert "parch/data/typst/house.typ" in names
    assert names.count("parch/data/typst/house.typ") == 1
