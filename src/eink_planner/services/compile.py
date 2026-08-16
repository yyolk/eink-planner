"""Compile generated Typst to PDF, installing the typst CLI if needed."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

TYPST_VERSION = "v0.13.1"
TYPST_ASSET = "typst-x86_64-unknown-linux-musl.tar.xz"
TYPST_URL = f"https://github.com/typst/typst/releases/download/{TYPST_VERSION}/{TYPST_ASSET}"
OUTPUT_FILE = "index.pdf"
TEMP_FILE = "temp.pdf"


class CompileError(RuntimeError):
    pass


class Compile:
    def compile(
        self,
        workdir: str | Path,
        file: str = "index.typst",
        enable_ghostscript: bool = False,
        tools_dir: str | Path | None = None,
    ) -> Path:
        workdir = Path(workdir)
        typst = ensure_typst(tools_dir=tools_dir)
        self._compile_typst(typst, workdir, file)
        if enable_ghostscript:
            self._run_ghostscript(workdir)
        return workdir / OUTPUT_FILE

    def _compile_typst(self, typst: Path, workdir: Path, file: str) -> None:
        src = workdir / file
        dest = workdir / OUTPUT_FILE
        print("Compiling with typst...")
        started = time.perf_counter()
        result = subprocess.run(
            [str(typst), "compile", str(src), str(dest)],
            capture_output=True,
            text=True,
        )
        elapsed = time.perf_counter() - started
        print(f"Typst compilation time: {elapsed:.2f}s")
        if result.returncode != 0:
            raise CompileError(
                f"typst compile failed ({result.returncode}):\n{result.stdout}\n{result.stderr}"
            )

    def _run_ghostscript(self, workdir: Path) -> None:
        gs = shutil.which("gs")
        if not gs:
            print("Ghostscript requested but `gs` is not on PATH; skipping.")
            return
        print("Running Ghostscript...")
        started = time.perf_counter()
        cmd = [
            gs,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.5",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dAutoRotatePages=/None",
            f"-sOutputFile={workdir / TEMP_FILE}",
            str(workdir / OUTPUT_FILE),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"Ghostscript time: {time.perf_counter() - started:.2f}s")
        if result.returncode != 0:
            raise CompileError(f"ghostscript failed: {result.stderr}")
        (workdir / TEMP_FILE).replace(workdir / OUTPUT_FILE)


def ensure_typst(tools_dir: str | Path | None = None) -> Path:
    """Return a typst binary, downloading the official Linux x64 build if needed."""
    found = shutil.which("typst")
    if found:
        return Path(found)

    if tools_dir is None:
        # repo root: src/eink_planner/services/compile.py → parents[3]
        tools_dir = Path(__file__).resolve().parents[3] / ".tools"
    tools_dir = Path(tools_dir)
    dest = tools_dir / "typst"
    if dest.exists() and os.access(dest, os.X_OK):
        return dest

    print(f"typst not found; downloading {TYPST_VERSION} to {dest} ...")
    tools_dir.mkdir(parents=True, exist_ok=True)
    _download_typst(dest)
    return dest


def _download_typst(dest: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / TYPST_ASSET
        try:
            urllib.request.urlretrieve(TYPST_URL, archive)
        except Exception as exc:
            raise CompileError(
                f"failed to download typst from {TYPST_URL}: {exc}"
            ) from exc
        with tarfile.open(archive, "r:xz") as tar:
            tar.extractall(tmp, filter="data")
        binary = None
        for root, _dirs, files in os.walk(tmp):
            if "typst" in files:
                binary = Path(root) / "typst"
                break
        if binary is None:
            raise CompileError("downloaded archive did not contain a typst binary")
        shutil.copy2(binary, dest)
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"Installed typst at {dest}", file=sys.stderr)
