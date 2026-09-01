import re
import shutil
import subprocess
from pathlib import Path

import pytest

import parch.services.compile as compile_mod
from parch.mos.preamble import copy_house_typ
from parch.services.compile import (
    Compile,
    CompileError,
    requested_typst_backend,
    resolve_typst_backend,
    typst_py_available,
)

REPO = Path(__file__).resolve().parents[1]

_TINY = "#set page(width: 80pt, height: 100pt)\n= A\n#pagebreak()\n= B\n"


def test_requested_backend_defaults_to_cli(monkeypatch):
    monkeypatch.delenv("PARCH_TYPST", raising=False)
    assert requested_typst_backend() == "cli"


@pytest.mark.parametrize("value,expected", [("cli", "cli"), ("PY", "py")])
def test_requested_backend_normalizes(monkeypatch, value, expected):
    monkeypatch.setenv("PARCH_TYPST", value)
    assert requested_typst_backend() == expected


def test_requested_backend_unknown(monkeypatch):
    monkeypatch.setenv("PARCH_TYPST", "wasm")
    with pytest.raises(CompileError, match="unknown PARCH_TYPST"):
        requested_typst_backend()


def test_requested_backend_rejects_auto(monkeypatch):
    monkeypatch.setenv("PARCH_TYPST", "auto")
    with pytest.raises(CompileError, match="unknown PARCH_TYPST"):
        requested_typst_backend()


def test_default_stays_cli_when_binding_present(monkeypatch):
    monkeypatch.delenv("PARCH_TYPST", raising=False)
    monkeypatch.setattr(compile_mod, "typst_py_available", lambda: True)
    assert resolve_typst_backend() == "cli"


def test_resolve_cli_ignores_binding(monkeypatch):
    monkeypatch.setenv("PARCH_TYPST", "cli")
    monkeypatch.setattr(compile_mod, "typst_py_available", lambda: True)
    assert resolve_typst_backend() == "cli"


def test_resolve_py_requires_binding(monkeypatch):
    monkeypatch.setenv("PARCH_TYPST", "py")
    monkeypatch.setattr(compile_mod, "typst_py_available", lambda: False)
    with pytest.raises(CompileError, match="typst-native"):
        resolve_typst_backend()


def test_cli_backend_uses_ensure_typst(monkeypatch, tmp_path):
    monkeypatch.setenv("PARCH_TYPST", "cli")
    called = {}

    def fake_ensure(**_kwargs):
        called["yes"] = True
        return Path("/bin/false")

    monkeypatch.setattr(compile_mod, "ensure_typst", fake_ensure)
    (tmp_path / "index.typst").write_text("= A\n", encoding="utf-8")
    with pytest.raises(CompileError):
        Compile().compile(tmp_path)
    assert called.get("yes") is True


@pytest.mark.skipif(not typst_py_available(), reason="typst extra not installed")
def test_py_backend_skips_ensure_typst(monkeypatch, tmp_path):
    monkeypatch.setenv("PARCH_TYPST", "py")
    monkeypatch.setattr(
        compile_mod,
        "ensure_typst",
        lambda **_k: (_ for _ in ()).throw(AssertionError("ensure_typst")),
    )
    (tmp_path / "index.typst").write_text(
        "#set page(width: 80pt, height: 100pt)\n= A\n", encoding="utf-8"
    )
    pdf = Compile().compile(tmp_path)
    assert pdf.is_file() and pdf.stat().st_size > 0


@pytest.mark.skipif(not typst_py_available(), reason="typst extra not installed")
def test_typst_py_compile_has_no_pages_arg():
    import inspect

    import typst

    params = inspect.signature(typst.Compiler.compile).parameters
    assert "pages" not in params
    assert "page" not in params
    assert compile_mod._py_pages_param(typst.Compiler.compile) is None


def _svg_geom(text: str) -> tuple[str, str, str]:
    vb = re.search(r'\bviewBox="([^"]*)"', text)
    width = re.search(r'\bwidth="([^"]*)"', text)
    height = re.search(r'\bheight="([^"]*)"', text)
    return (
        vb.group(1) if vb else "",
        width.group(1) if width else "",
        height.group(1) if height else "",
    )


def _pdf_page_count(path: Path) -> int:
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(path)).pages)
    except ImportError:
        pass
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        raise RuntimeError("need pypdf or pdfinfo to count PDF pages")
    result = subprocess.run(
        [pdfinfo, str(path)], capture_output=True, text=True, check=False
    )
    for line in result.stdout.splitlines():
        if line.lower().startswith("pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError(f"pdfinfo did not report pages:\n{result.stdout}")


def _compile_backend(monkeypatch, backend: str, workdir: Path, *, pages=None):
    monkeypatch.setenv("PARCH_TYPST", backend)
    compiler = Compile()
    tools = REPO / ".tools"
    if pages is None:
        return compiler.compile(workdir, tools_dir=tools)
    return compiler.compile_svg(
        workdir, pages=pages, dest_pattern="preview-{p}.svg", tools_dir=tools
    )


@pytest.mark.skipif(not typst_py_available(), reason="typst extra not installed")
def test_py_cli_tiny_pdf_svg_match(monkeypatch, tmp_path):
    cli_dir = tmp_path / "cli"
    py_dir = tmp_path / "py"
    for dest in (cli_dir, py_dir):
        dest.mkdir()
        (dest / "index.typst").write_text(_TINY, encoding="utf-8")

    cli_pdf = _compile_backend(monkeypatch, "cli", cli_dir)
    cli_svgs = _compile_backend(monkeypatch, "cli", cli_dir, pages=[1, 2])
    py_pdf = _compile_backend(monkeypatch, "py", py_dir)
    py_svgs = _compile_backend(monkeypatch, "py", py_dir, pages=[1, 2])

    assert cli_pdf.is_file() and py_pdf.is_file()
    assert _pdf_page_count(cli_pdf) == _pdf_page_count(py_pdf) == 2

    assert [p.name for p in cli_svgs] == [p.name for p in py_svgs] == [
        "preview-1.svg",
        "preview-2.svg",
    ]
    for cli_svg, py_svg in zip(cli_svgs, py_svgs):
        cli_text = cli_svg.read_text(encoding="utf-8")
        py_text = py_svg.read_text(encoding="utf-8")
        assert _svg_geom(cli_text) == _svg_geom(py_text)

    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        from tests.visual import ink_bbox, raster_page

        cli_png = raster_page(cli_pdf, 1, tmp_path / "cli-1.png")
        py_png = raster_page(py_pdf, 1, tmp_path / "py-1.png")
        cli_box = ink_bbox(cli_png)
        py_box = ink_bbox(py_png)
        assert cli_box is not None and py_box is not None
        assert all(abs(a - b) <= 3 for a, b in zip(cli_box, py_box))


def _write_planner(workdir: Path, stem: str) -> Path:
    from parch.config import load
    from parch.i18n import I18n
    from parch.services.generate import Generate
    from tests.helpers import base_config

    workdir.mkdir(parents=True, exist_ok=True)
    text = Generate(i18n=I18n.load_default("en")).generate(load(base_config(stem)))
    src = workdir / "index.typst"
    src.write_text(text, encoding="utf-8")
    copy_house_typ(workdir, device=stem)
    return src


@pytest.mark.slow
@pytest.mark.skipif(not typst_py_available(), reason="typst extra not installed")
def test_py_cli_nomad_press_and_proof_page1(monkeypatch, tmp_path):
    nomad_src = _write_planner(tmp_path / "nomad-src", "supernote-nomad")
    text = nomad_src.read_text(encoding="utf-8")
    cli_nomad = tmp_path / "nomad-cli"
    py_nomad = tmp_path / "nomad-py"
    for dest in (cli_nomad, py_nomad):
        dest.mkdir()
        (dest / "index.typst").write_text(text, encoding="utf-8")
        copy_house_typ(dest, device="supernote-nomad")

    cli_pdf = _compile_backend(monkeypatch, "cli", cli_nomad)
    py_pdf = _compile_backend(monkeypatch, "py", py_nomad)
    assert cli_pdf.is_file() and py_pdf.is_file()
    assert _pdf_page_count(cli_pdf) == _pdf_page_count(py_pdf)
    assert cli_pdf.stat().st_size > 0 and py_pdf.stat().st_size > 0

    proof_src = _write_planner(tmp_path / "proof-src", "158x210")
    proof_text = proof_src.read_text(encoding="utf-8")
    cli_proof = tmp_path / "proof-cli"
    py_proof = tmp_path / "proof-py"
    for dest in (cli_proof, py_proof):
        dest.mkdir()
        (dest / "index.typst").write_text(proof_text, encoding="utf-8")
        copy_house_typ(dest, device="158x210")

    cli_svgs = _compile_backend(monkeypatch, "cli", cli_proof, pages=[1])
    py_svgs = _compile_backend(monkeypatch, "py", py_proof, pages=[1])
    cli_text = cli_svgs[0].read_text(encoding="utf-8")
    py_text = py_svgs[0].read_text(encoding="utf-8")
    assert _svg_geom(cli_text) == _svg_geom(py_text)
