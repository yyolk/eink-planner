"""parch press dest lock: cwd product PDF, temp compile unless -w."""

from pathlib import Path

from parch.cli import build_parser, generate_cmd, main, press_dest, press_outfile
from parch.services.compile import OUTPUT_FILE
from tests.toml_fixtures import _minimal


def _job(tmp_path: Path, name: str = "mine.toml") -> Path:
    path = tmp_path / name
    path.write_text(_minimal(enable=["colophon"], sections=""), encoding="utf-8")
    return path


def _dummy(monkeypatch, *, fail: bool = False, seen: dict | None = None):
    captured = {} if seen is None else seen

    class _DummyCompile:
        def compile(self, workdir, file="index.typst", enable_ghostscript=False, **_kwargs):
            workdir = Path(workdir)
            captured["workdir"] = workdir
            captured["ghostscript"] = enable_ghostscript
            if fail:
                raise CompileError("typst compile failed")
            pdf = workdir / OUTPUT_FILE
            pdf.write_bytes(b"%PDF-gs" if enable_ghostscript else b"%PDF-ok")
            return pdf

    monkeypatch.setattr("parch.cli.Compile", lambda: _DummyCompile())
    return captured


def test_press_dest_toml_stem(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    job = tmp_path / "jobs" / "mine.toml"
    assert press_dest(job) == Path.cwd() / "mine.pdf"
    assert press_dest("mine.toml") == Path.cwd() / "mine.pdf"
    args = build_parser().parse_args(["press", str(job)])
    assert press_dest(args.config, workdir=args.workdir, outfile=press_outfile(args)) == (
        Path.cwd() / "mine.pdf"
    )


def test_press_dest_device_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    args = build_parser().parse_args(["press", "supernote-nomad"])
    assert press_dest(args.config, workdir=args.workdir, outfile=press_outfile(args)) == (
        Path.cwd() / "supernote-nomad.pdf"
    )


def test_press_dest_dash_o_and_positional():
    flagged = build_parser().parse_args(["press", "mine.toml", "-o", "custom.pdf"])
    assert press_dest(flagged.config, workdir=flagged.workdir, outfile=press_outfile(flagged)) == (
        Path("custom.pdf")
    )
    positional = build_parser().parse_args(["press", "mine.toml", "custom.pdf"])
    assert press_dest(
        positional.config, workdir=positional.workdir, outfile=press_outfile(positional)
    ) == Path("custom.pdf")


def test_press_dest_workdir_only_is_index_pdf():
    args = build_parser().parse_args(["press", "mine.toml", "-w", "out"])
    assert press_dest(args.config, workdir=args.workdir, outfile=press_outfile(args)) == (
        Path("out") / OUTPUT_FILE
    )


def test_press_dest_workdir_and_output():
    args = build_parser().parse_args(["press", "mine.toml", "-w", "out", "-o", "custom.pdf"])
    assert press_dest(args.config, workdir=args.workdir, outfile=press_outfile(args)) == Path(
        "custom.pdf"
    )


def test_press_output_mutex(capsys):
    rc = main(["press", "mine.toml", "a.pdf", "-o", "b.pdf"])
    assert rc == 1
    assert "give outfile as a positional or -o, not both" in capsys.readouterr().err


def test_press_output_mutex_agrees(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = _job(tmp_path)
    _dummy(monkeypatch)
    args = build_parser().parse_args(["press", str(path), "same.pdf", "-o", "same.pdf"])
    assert press_outfile(args) == "same.pdf"
    assert generate_cmd(args, argv=["parch", "press", str(path), "same.pdf", "-o", "same.pdf"]) == 0
    assert (tmp_path / "same.pdf").read_bytes() == b"%PDF-ok"


def test_press_default_temp_dir_gone_after_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    jobs = tmp_path / "jobs"
    jobs.mkdir()
    path = _job(jobs)
    seen = _dummy(monkeypatch)
    assert main(["press", str(path)]) == 0
    dest = tmp_path / "mine.pdf"
    assert dest.read_bytes() == b"%PDF-ok"
    assert "Wrote" in capsys.readouterr().out
    assert seen["workdir"] is not None
    assert not seen["workdir"].exists()
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "jobs" / "mine.pdf").exists()


def test_press_failed_compile_leaves_existing_dest(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = _job(tmp_path)
    dest = tmp_path / "mine.pdf"
    dest.write_bytes(b"keep")
    seen = _dummy(monkeypatch, fail=True)
    assert main(["press", str(path)]) == 1
    assert dest.read_bytes() == b"keep"
    assert "typst compile failed" in capsys.readouterr().err
    assert seen["workdir"] is not None
    assert not seen["workdir"].exists()


def test_press_workdir_writes_index_typst(tmp_path, monkeypatch):
    path = _job(tmp_path)
    workdir = tmp_path / "work"
    _dummy(monkeypatch)
    assert main(["press", str(path), "-w", str(workdir)]) == 0
    assert (workdir / "index.typst").is_file()
    assert (workdir / OUTPUT_FILE).read_bytes() == b"%PDF-ok"
    assert (workdir / "house.typ").is_file()


def test_press_workdir_and_output_keeps_index_pdf(tmp_path, monkeypatch):
    path = _job(tmp_path)
    workdir = tmp_path / "work"
    dest = tmp_path / "custom.pdf"
    _dummy(monkeypatch)
    assert main(["press", str(path), "-w", str(workdir), "-o", str(dest)]) == 0
    assert dest.read_bytes() == b"%PDF-ok"
    assert (workdir / OUTPUT_FILE).read_bytes() == b"%PDF-ok"
    assert (workdir / "index.typst").is_file()


def test_press_ghostscript_dest_is_gs_pdf(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = _job(tmp_path)
    seen = _dummy(monkeypatch)
    assert main(["press", str(path), "-g"]) == 0
    assert seen["ghostscript"] is True
    assert (tmp_path / "mine.pdf").read_bytes() == b"%PDF-gs"
    assert not seen["workdir"].exists()


def test_press_overwrites_existing_dest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = _job(tmp_path)
    dest = tmp_path / "mine.pdf"
    dest.write_bytes(b"old")
    _dummy(monkeypatch)
    assert main(["press", str(path)]) == 0
    assert dest.read_bytes() == b"%PDF-ok"


def test_proof_and_specimen_keep_out_default():
    parser = build_parser()
    assert parser.parse_args(["proof", "158x210", "--samples"]).workdir == "./out"
    assert parser.parse_args(["specimen", "supernote-nomad"]).workdir == "./out"
    assert parser.parse_args(["press", "supernote-nomad"]).workdir is None
