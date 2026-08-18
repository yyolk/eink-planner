"""Compile generated Typst to PDF, installing the typst CLI if needed."""

from __future__ import annotations

import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

TYPST_VERSION = "v0.15.1"
_PINNED_VERSION = TYPST_VERSION.lstrip("v")

_ARCH_ALIASES = {
    "amd64": "x86_64",
    "x86_64": "x86_64",
    "arm64": "aarch64",
    "aarch64": "aarch64",
    "armv7l": "armv7l",
    "riscv64": "riscv64",
}

_ASSET_BY_PLATFORM_ARCH = {
    ("darwin", "x86_64"): "typst-x86_64-apple-darwin.tar.xz",
    ("darwin", "aarch64"): "typst-aarch64-apple-darwin.tar.xz",
    ("linux", "x86_64"): "typst-x86_64-unknown-linux-musl.tar.xz",
    ("linux", "aarch64"): "typst-aarch64-unknown-linux-musl.tar.xz",
    ("linux", "armv7l"): "typst-armv7-unknown-linux-musleabi.tar.xz",
    ("linux", "riscv64"): "typst-riscv64gc-unknown-linux-gnu.tar.xz",
    ("win32", "x86_64"): "typst-x86_64-pc-windows-msvc.zip",
    ("win32", "aarch64"): "typst-aarch64-pc-windows-msvc.zip",
}

_SUPPORTED_PAIRS = (
    "darwin + x86_64/amd64",
    "darwin + arm64/aarch64",
    "linux + x86_64/amd64",
    "linux + aarch64/arm64",
    "linux + armv7l",
    "linux + riscv64",
    "win32 + x86_64/amd64",
    "win32 + arm64/aarch64",
)

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


def typst_asset_name(
    sys_platform: str | None = None,
    machine: str | None = None,
) -> str:
    """Map ``(sys.platform, platform.machine())`` to an official Typst asset."""
    plat = (sys.platform if sys_platform is None else sys_platform).lower()
    arch_raw = (platform.machine() if machine is None else machine).lower()
    arch = _ARCH_ALIASES.get(arch_raw)
    asset = _ASSET_BY_PLATFORM_ARCH.get((plat, arch)) if arch else None
    if asset is None:
        raise CompileError(
            f"unsupported platform/arch for typst {TYPST_VERSION}: "
            f"{plat!r} / {arch_raw!r}. Supported pairs: {', '.join(_SUPPORTED_PAIRS)}"
        )
    return asset


def typst_download_url(asset: str | None = None) -> str:
    name = asset if asset is not None else typst_asset_name()
    return f"https://github.com/typst/typst/releases/download/{TYPST_VERSION}/{name}"


def cached_typst_name(sys_platform: str | None = None) -> str:
    plat = sys.platform if sys_platform is None else sys_platform
    return "typst.exe" if plat.lower() == "win32" else "typst"


def ensure_typst(tools_dir: str | Path | None = None) -> Path:
    """Return a typst binary, downloading the official pinned build if needed."""
    found = shutil.which("typst")
    if found:
        path = Path(found)
        _warn_if_path_typst_older(path)
        return path

    if tools_dir is None:
        # repo root: src/eink_planner/services/compile.py → parents[3]
        tools_dir = Path(__file__).resolve().parents[3] / ".tools"
    tools_dir = Path(tools_dir)
    dest = tools_dir / cached_typst_name()
    if dest.exists() and os.access(dest, os.X_OK) and _cached_typst_matches_pin(dest):
        return dest

    print(f"typst not found or not {TYPST_VERSION}; downloading {TYPST_VERSION} to {dest} ...")
    tools_dir.mkdir(parents=True, exist_ok=True)
    _download_typst(dest)
    return dest


def _typst_version_text(binary: Path) -> str:
    for args in ([str(binary), "--version"], [str(binary), "version"]):
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        text = f"{result.stdout or ''}{result.stderr or ''}"
        if result.returncode == 0 and text.strip():
            return text
    return ""


def _parse_typst_version(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _cached_typst_matches_pin(binary: Path) -> bool:
    parsed = _parse_typst_version(_typst_version_text(binary))
    pin = _parse_typst_version(_PINNED_VERSION)
    return parsed is not None and parsed == pin


def _warn_if_path_typst_older(binary: Path) -> None:
    parsed = _parse_typst_version(_typst_version_text(binary))
    pin = _parse_typst_version(_PINNED_VERSION)
    if parsed is None or pin is None or parsed >= pin:
        return
    print(
        f"warning: PATH typst {'.'.join(map(str, parsed))} is older than "
        f"the official pin {TYPST_VERSION}; using PATH anyway",
        file=sys.stderr,
    )


def _find_typst_binary(root: Path) -> Path | None:
    names = {"typst", "typst.exe"}
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name in names:
                return Path(dirpath) / name
    return None


def _extract_archive(archive: Path, dest_dir: Path) -> None:
    if archive.suffix == ".zip" or archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest_dir)
        return
    with tarfile.open(archive, "r:xz") as tar:
        tar.extractall(dest_dir, filter="data")


def _download_typst(dest: Path) -> None:
    asset = typst_asset_name()
    url = typst_download_url(asset)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        archive = tmp_path / asset
        try:
            urllib.request.urlretrieve(url, archive)
        except Exception as exc:
            raise CompileError(f"failed to download typst from {url}: {exc}") from exc
        _extract_archive(archive, tmp_path)
        binary = _find_typst_binary(tmp_path)
        if binary is None:
            raise CompileError("downloaded archive did not contain a typst binary")
        shutil.copy2(binary, dest)
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"Installed typst at {dest}", file=sys.stderr)
