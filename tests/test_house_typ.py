"""House Typst library: preamble #import, no inlined helper bodies, workdir copy."""

import zipfile
from pathlib import Path

from parch.config import load
from parch.mos.configurator import Configurator
from parch.toml_config import apply_hand
from parch.devices import DEVICES, get_device
from parch.mos.preamble import (
    DEVICE_TYP,
    Preamble,
    copy_house_typ,
    house_typ_resource,
    render_device_typ,
    write_device_typ,
)
from tests.helpers import base_config


def _preamble_set_page(typst: str) -> str:
    start = typst.index("#set page")
    end = typst.index("#set text")
    return typst[start:end]


def test_preamble_imports_house_and_does_not_inline_bodies():
    typst = Preamble(Configurator(load(base_config("158x210")))).generate()
    assert '#import "device.typ": page-width, page-height, toolbar-edge, toolbar-clearance, writing-clearance, mos-width' in typst
    assert "page-margin.with(toolbar-edge: toolbar-edge, toolbar-clearance: toolbar-clearance, writing-clearance: writing-clearance)" in typst
    assert "#include" not in typst
    set_page = _preamble_set_page(typst)
    assert set_page == "#set page(width: page-width, height: page-height, margin: page-margin(left))\n\n"
    assert "158mm" not in set_page
    assert "210mm" not in set_page
    assert "5mm" not in set_page
    assert "0mm" not in set_page
    assert "height: auto" not in typst
    assert '#import "house.typ"' in typst
    imported = typst[typst.index('#import "house.typ"') :].splitlines()[0]
    assert "contents_bars" in imported
    assert "lead_pair" in imported
    assert "trail_heading" in imported
    assert "mos_frame" in imported
    assert "well_frame" in imported
    assert "month_grid" in imported
    assert "month_weeks" in imported
    assert "week_matrix" in imported
    assert "lined_well" in imported
    assert "daily_well" in imported
    assert "quarter_well" in imported
    assert "week_cell" not in imported
    assert "_order_week_rows" not in imported
    assert "#let link_padding =" in typst
    assert "#let rect_pattern = rect_pattern.with(regular_height: regular_height)" in typst
    assert "#let padded_link = padded_link.with(padding: link_padding)" in typst
    assert "#let contents_bars = contents_bars.with(thick_stroke: thick_stroke)" in typst
    assert "trail_heading.with(" not in typst
    assert "spacing: 1fr" not in typst
    assert "#let mos_frame = mos_frame.with(mos-width: mos-width, column-gutter: 2mm)" in typst
    assert "#let well_frame = well_frame.with(heading-height: 10mm, row-gutter: 2mm)" in typst
    assert "#let month_grid = month_grid.with(hline-stroke: regular_stroke + black)" in typst
    assert "week-rows:" not in typst
    assert "#let month_weeks = month_weeks.with(week-col: regular_height, stroke: regular_stroke)" in typst
    assert "month_weeks.with(rows" not in typst
    assert "#let week_matrix = week_matrix.with(header-stroke: regular_stroke + black, regular-height: regular_height)" in typst
    assert "#let lined_well = lined_well.with(regular-height: regular_height)" in typst
    assert "#let daily_well = daily_well.with(column-gutter: regular_column_gutter)" in typst
    assert "#let quarter_well = quarter_well.with(column-gutter: regular_column_gutter)" in typst
    assert "3fr" not in typst
    assert "5fr" not in typst
    assert "2fr" not in typst
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
    # lined_well chrome lives in house.typ, not the preamble.
    assert "#let lined_well(regular-height" not in typst
    assert "rect_pattern(regular_height: regular-height, pattern)" not in typst
    # daily_well chrome (3fr/5fr seating) lives in house.typ.
    assert "#let daily_well(side" not in typst
    assert "grid(columns: (3fr, 5fr)" not in typst
    assert "grid(columns: (5fr, 3fr)" not in typst
    # month_weeks / quarter_well chrome lives in house.typ.
    assert "#let month_weeks(side" not in typst
    assert "#let quarter_well(side" not in typst
    assert "grid(columns: (2fr, 3fr)" not in typst
    assert "grid(columns: (3fr, 2fr)" not in typst
    assert "(1fr,) * 7" not in typst
    assert "(1fr,) * 8" not in typst
    house = house_typ_resource().read_text(encoding="utf-8")
    assert "#set page" not in house
    assert "page-width" not in house
    assert "#let page-margin(side, toolbar-edge: none, toolbar-clearance: none, writing-clearance: none)" in house
    assert "if toolbar-edge == top { toolbar-clearance } else { 0mm }" in house
    assert "#let contents_bars(" in house
    assert "#let lead_pair(" in house
    assert "#let lead_pair(mark, title, spacing: 6pt)" in house
    assert "#let lead_pair(left, right" not in house
    assert "#let trail_heading(" in house
    assert "#let trail_heading(title, mark) = grid(" in house
    assert "Title shrinks in the 1fr (scale + reflow), one line, never grow." in house
    assert "spacing:" not in house[house.index("#let trail_heading(") : house.index("#let mos_frame(")]
    trail_heading = house[house.index("#let trail_heading(") : house.index("#let mos_frame(")]
    assert "columns: (1fr, auto)" in trail_heading
    assert "align: horizon + start" in trail_heading
    assert "layout(size => context {" in trail_heading
    assert "let wanted = measure(title)" in trail_heading
    assert "calc.min(100%, size.width / wanted.width * 100%)" in trail_heading
    assert "scale(factor, origin: start + horizon, reflow: true, title)" in trail_heading
    assert "reflow: true" in trail_heading
    assert "clip:" not in trail_heading
    assert "box(width: 100%, clip: true, title)" not in trail_heading
    assert trail_heading.rstrip().endswith("  mark,\n)")
    assert "stack(" not in trail_heading
    assert "dir: ltr" not in trail_heading
    assert "direction" not in trail_heading
    assert "seated_title" not in trail_heading
    assert "seated_mark" not in trail_heading
    assert "#let mos_frame(" in house
    assert "#let well_frame(" in house
    well_frame = house[house.index("#let well_frame(") : house.index("#let _order_week_rows(")]
    assert "grid.cell(align: horizon, box(width: 100%, height: 100%, clip: true, heading))" in well_frame
    assert "#let month_grid(" in house
    assert "rows: (auto, auto) + (1fr,) * week-rows" in house
    assert "grid.hline(y: 1, stroke: hline-stroke)" in house
    assert "grid.hline(y: 2, stroke: hline-stroke)" in house
    assert "#let _order_week_rows(" in house
    month_grid = house[house.index("#let month_grid(") : house.index("#let month_weeks(")]
    assert month_grid.startswith(
        "#let month_grid(\n  side,\n  name,\n  inset: none,\n  week-rows: 6,\n  hline-stroke: none,\n  ..rows,\n)"
    )
    assert "columns: (1fr,) * 8" in month_grid
    assert "name," in month_grid
    assert "_order_week_rows(side, rows.pos())" in month_grid
    assert "if x == (if side == left { 1 } else { 7 })" in month_grid
    assert "stroke: stroke" not in month_grid
    assert "columns: columns" not in month_grid
    assert "columns: none" not in month_grid
    assert "reverse" not in month_grid
    month_weeks = house[house.index("#let month_weeks(") : house.index("#let week_cell(")]
    assert month_weeks.startswith(
        "#let month_weeks(side, rows: none, week-col: none, stroke: none, ..cells) = block(\n"
        "  width: 100%,\n"
        "  height: 1fr,\n"
        "  grid(\n"
    )
    assert "(week-col,) + (1fr,) * 7" in month_weeks
    assert "(1fr,) * 7 + (week-col,)" in month_weeks
    assert "_order_week_rows(side, cells.pos())" in month_weeks
    assert "reverse" not in month_weeks
    assert "#let week_cell(" in house
    assert "#let week_matrix(" in house
    assert "rows: (auto, 1fr)" in house
    assert "columns: (1fr, 1fr, 1fr)" in house
    assert "rows: (1fr, 1fr, 1fr)" in house
    assert "grid.cell(colspan: 2," in house
    assert 'bottom-edge: "descender"' in house
    week_cell = house[house.index("#let week_cell(") : house.index("#let week_matrix(")]
    assert week_cell.startswith(
        "#let week_cell(header, header-stroke: none, pattern: none, regular-height: none) = {\n"
        "  let gap = if header-stroke == none { 0pt } else { stroke(header-stroke).thickness }\n"
        "  grid(\n"
        "    columns: 1fr,\n"
        "    rows: (auto, 1fr),\n"
        "    grid.cell(\n"
        "      inset: (bottom: gap),\n"
        "      stroke: (bottom: header-stroke),\n"
        '      text(bottom-edge: "descender", header),\n'
        "    ),\n"
        "    box(\n"
        "      width: 100%,\n"
        "      height: 100%,\n"
        "      clip: true,\n"
        "      inset: (top: 0.25em, bottom: 0.25em),\n"
        "      rect_pattern(regular_height: regular-height, pattern),\n"
        "    ),\n"
        "  )\n"
        "}\n"
    )
    assert "inset: (bottom: 0.25em)" not in week_cell
    assert 'text(bottom-edge: "descender"' in week_cell
    assert "inset: (top: 0.25em, bottom: 0.25em)" in week_cell
    assert "1.5 * gap" not in week_cell
    week_matrix_sig = house[house.index("#let week_matrix(") : house.index("..contents,")]
    assert "side" not in week_matrix_sig
    assert "row-gutter" not in week_matrix_sig
    assert "#let lined_well(" in house
    lined_start = house.index("#let lined_well(")
    lined_well = house[lined_start : house.index("\n\n", lined_start)]
    assert "width: 100%" in lined_well
    assert "height: 100%" in lined_well
    assert "rect_pattern(regular_height: regular-height, pattern)" in lined_well
    assert "inset" not in lined_well
    assert "side" not in lined_well
    assert "grid(" not in lined_well
    assert "header" not in lined_well
    assert "#let daily_well(" in house
    daily_well = house[house.index("#let daily_well(") :]
    assert daily_well.startswith(
        "#let daily_well(side, hours, writing, column-gutter: none) = if side == left {\n"
        "  grid(columns: (3fr, 5fr), rows: 1fr, column-gutter: column-gutter, hours, writing)\n"
        "} else {\n"
        "  grid(columns: (5fr, 3fr), rows: 1fr, column-gutter: column-gutter, writing, hours)\n"
        "}"
    )
    assert "column-gutter: 0pt" not in daily_well
    assert "rows: (1fr,)" not in daily_well
    assert "..if" not in daily_well
    assert "height: auto" not in daily_well
    assert "reverse" not in daily_well
    assert "#let quarter_well(" in house
    quarter_well = house[house.index("#let quarter_well(") :]
    assert quarter_well.startswith(
        "#let quarter_well(side, months, pad, column-gutter: none) = if side == left {\n"
        "  grid(columns: (2fr, 3fr), rows: 1fr, column-gutter: column-gutter, months, pad)\n"
        "} else {\n"
        "  grid(columns: (3fr, 2fr), rows: 1fr, column-gutter: column-gutter, pad, months)\n"
        "}"
    )
    assert "reverse" not in quarter_well
    assert "rowspan" not in house
    assert "dir: ltr" in house
    assert "calc.max(measure(title).height, measure(mark).height)" not in house
    assert "measure(seated_title)" not in house


def test_preamble_mos_right_uses_page_margin_right():
    dto = apply_hand(load(base_config("158x210")), "right")
    typst = Preamble(Configurator(dto)).generate()
    assert '#import "device.typ": page-width, page-height, toolbar-edge, toolbar-clearance, writing-clearance, mos-width' in typst
    assert "page-margin(right)" in _preamble_set_page(typst)
    assert "page-margin(left)" not in _preamble_set_page(typst)


def test_preamble_devices_import_parameterized_device_typ():
    nomad = Preamble(Configurator(load(base_config("supernote-nomad")))).generate()
    scribe = Preamble(Configurator(load(base_config("kindle-scribe")))).generate()
    lined = Preamble(Configurator(load(base_config("supernote-nomad", paper="lined")))).generate()
    right = Preamble(Configurator(apply_hand(load(base_config("kindle-scribe")), "right"))).generate()
    import_line = '#import "device.typ": page-width, page-height, toolbar-edge, toolbar-clearance, writing-clearance, mos-width'
    assert import_line in nomad
    assert import_line in scribe
    assert import_line in lined
    assert import_line in right
    assert "page-margin(left)" in _preamble_set_page(nomad)
    assert "page-margin(right)" in _preamble_set_page(right)
    assert "118.87" not in _preamble_set_page(nomad)
    assert "157.48" not in _preamble_set_page(scribe)
    assert "height: auto" not in nomad
    assert "height: auto" not in scribe


def test_device_typ_is_parameterized_from_python_record():
    nomad = render_device_typ(get_device("supernote-nomad"))
    scribe = render_device_typ(get_device("kindle-scribe"))
    assert nomad == (
        "#let page-width = 118.87mm\n"
        "#let page-height = 158.5mm\n"
        "#let toolbar-edge = top\n"
        "#let toolbar-clearance = 8mm\n"
        "#let writing-clearance = 4mm\n"
        "#let mos-width = 8mm\n"
    )
    assert scribe == (
        "#let page-width = 157.48mm\n"
        "#let page-height = 209.97mm\n"
        "#let toolbar-edge = none\n"
        "#let toolbar-clearance = 0mm\n"
        "#let writing-clearance = 5mm\n"
        "#let mos-width = 10mm\n"
    )
    for device in DEVICES:
        text = render_device_typ(device)
        assert text == (
            f"#let page-width = {device.page_width}\n"
            f"#let page-height = {device.page_height}\n"
            f"#let toolbar-edge = {device.toolbar_edge}\n"
            f"#let toolbar-clearance = {device.toolbar_clearance}\n"
            f"#let writing-clearance = {device.writing_clearance}\n"
            f"#let mos-width = {device.mos_width}\n"
        )
        assert "page-margin" not in text
        assert "#let mos-width = toolbar-clearance" not in text
        assert "ppi" not in text
        assert "lined" not in text
        assert "dotted" not in text


def test_copy_house_typ_writes_workdir(tmp_path):
    dest = copy_house_typ(tmp_path)
    assert dest == tmp_path / "house.typ"
    assert dest.is_file()
    assert not (tmp_path / DEVICE_TYP).exists()
    assert not (tmp_path / "158x210.typ").exists()
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
    assert "#let month_weeks(" in text
    assert "#let week_matrix(" in text
    assert "#let quarter_well(" in text
    assert "#let week_cell(" in text
    assert "#let lined_well(" in text
    assert "#let daily_well(" in text


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
            "hand": None,
        },
    )()
    assert generate_cmd(ns, argv=["parch", "press", str(path)]) == 0
    workdir = tmp_path / "out"
    assert (workdir / "house.typ").is_file()
    assert (workdir / DEVICE_TYP).is_file()
    index = (workdir / "index.typst").read_text(encoding="utf-8")
    assert '#import "house.typ"' in index
    assert '#import "device.typ": page-width, page-height, toolbar-edge, toolbar-clearance, writing-clearance, mos-width' in index
    assert (workdir / "house.typ").read_text(encoding="utf-8") == house_typ_resource().read_text(
        encoding="utf-8"
    )
    assert (workdir / DEVICE_TYP).read_text(encoding="utf-8") == render_device_typ(
        get_device("158x210")
    )
    assert not (workdir / "158x210.typ").exists()
    assert not (workdir / "lined.typ").exists()
    assert not (workdir / "158x210-mos-left.typ").exists()


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
    for device in ("supernote-nomad.typ", "kindle-scribe.typ", "158x210.typ"):
        assert f"parch/data/typst/{device}" not in names
    assert not any(name.endswith("-lined.typ") for name in names)
    assert not any("mos-left.typ" in name or "mos-right.typ" in name for name in names)
    assert not any(name.startswith("parch/data/configs/") and name.endswith(".toml") for name in names)


def test_write_device_typ_fills_workdir(tmp_path):
    dest = write_device_typ(tmp_path, "kindle-scribe")
    assert dest == tmp_path / DEVICE_TYP
    assert dest.read_text(encoding="utf-8") == render_device_typ(get_device("kindle-scribe"))
    copy_house_typ(tmp_path, device="supernote-nomad")
    assert (tmp_path / DEVICE_TYP).read_text(encoding="utf-8") == render_device_typ(
        get_device("supernote-nomad")
    )


def test_no_shipped_job_tomls():
    from importlib.resources import files

    configs_dir = files("parch.data") / "configs"
    if not configs_dir.is_dir():
        return
    configs = [p.name for p in configs_dir.iterdir() if str(p).endswith(".toml")]
    assert configs == []
