"""House Typst library: preamble #import, no inlined helper bodies, workdir copy."""

from pathlib import Path

from parch.config import load
from parch.mos.configurator import Configurator
from parch.mos.preamble import Preamble, copy_house_typ, house_typ_resource
from tests.helpers import base_config


def test_preamble_imports_house_and_does_not_inline_bodies():
    typst = Preamble(Configurator(load(base_config("158x210-mos-left")))).generate()
    assert '#import "house.typ"' in typst
    assert "#let link_padding =" in typst
    assert "#let rect_pattern = rect_pattern.with(regular_height: regular_height)" in typst
    assert "#let padded_link = padded_link.with(padding: link_padding)" in typst
    assert "#let dotted = dotted(regular_height: regular_height)" in typst
    assert "#let lined = lined(regular_height: regular_height, regular_stroke: regular_stroke)" in typst
    assert "#let scratch_pad = rect_pattern(dotted)" in typst
    assert "here().position()" not in typst
    assert "link(target)[#box(inset: padding, content)]" not in typst
    assert "#let rect_pattern(pattern) = rect(" not in typst
    assert "#let padded_link(padding:" not in typst
    assert "#set page" not in house_typ_resource().read_text(encoding="utf-8")


def test_copy_house_typ_writes_workdir(tmp_path):
    dest = copy_house_typ(tmp_path)
    assert dest == tmp_path / "house.typ"
    assert dest.is_file()
    text = dest.read_text(encoding="utf-8")
    packaged = house_typ_resource().read_text(encoding="utf-8")
    assert text == packaged
    assert "#let rect_pattern(" in text
    assert "#let padded_link(" in text


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
