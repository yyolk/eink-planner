"""Compile generated Typst to PDF, installing the typst CLI if needed."""

import inspect
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

ENV_TYPST = "PARCH_TYPST"
_BACKENDS = frozenset({"cli", "py"})
_PY_PAGE_PARAMS = ("pages", "page", "page_ranges")


class CompileError(RuntimeError):
    pass


def requested_typst_backend() -> str:
    """Return the raw PARCH_TYPST choice (default cli)."""
    raw = os.environ.get(ENV_TYPST, "cli").strip().lower() or "cli"
    if raw not in _BACKENDS:
        raise CompileError(
            f"unknown {ENV_TYPST}={raw!r}; expected cli or py"
        )
    return raw


def typst_py_available() -> bool:
    """True when the PyPI typst binding is importable."""
    try:
        import typst  # noqa: F401
    except ImportError:
        return False
    return True


def resolve_typst_backend() -> str:
    """Resolve PARCH_TYPST to cli or py."""
    requested = requested_typst_backend()
    if requested == "cli":
        return "cli"
    if not typst_py_available():
        raise CompileError(
            "PARCH_TYPST=py but the typst binding is not installed; "
            "run `uv sync --extra typst-native` or unset PARCH_TYPST"
        )
    return "py"


def _import_typst_py():
    try:
        import typst as typst_py
    except ImportError as exc:
        raise CompileError(
            "PARCH_TYPST=py but the typst binding is not installed; "
            "run `uv sync --extra typst-native` or set PARCH_TYPST=cli"
        ) from exc
    return typst_py


def _typst_py_error(exc: BaseException, what: str) -> CompileError:
    if isinstance(exc, CompileError):
        return exc
    message = getattr(exc, "message", None) or str(exc)
    diagnostic = getattr(exc, "diagnostic", None)
    if diagnostic and str(diagnostic).strip() and str(diagnostic) != str(message):
        detail = f"{message}\n{diagnostic}"
    else:
        detail = str(diagnostic or message)
    return CompileError(f"typst (py) {what} failed: {detail}")


def _package_cache_path() -> Path:
    path = Path.home() / ".cache" / "parch" / "packages"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _py_pages_param(compile_fn) -> str | None:
    try:
        params = inspect.signature(compile_fn).parameters
    except (TypeError, ValueError):
        return None
    for name in _PY_PAGE_PARAMS:
        if name in params:
            return name
    return None


def _svg_page_buffers(result) -> list[bytes]:
    if result is None:
        raise CompileError(
            "typst (py) cannot select pages: compile(format='svg') returned no page bytes"
        )
    if isinstance(result, (bytes, bytearray)):
        return [bytes(result)]
    try:
        buffers = [bytes(item) for item in result]
    except TypeError as exc:
        raise CompileError(
            "typst (py) cannot select pages: compile(format='svg') did not return page bytes"
        ) from exc
    if not buffers:
        raise CompileError(
            "typst (py) cannot select pages: compile(format='svg') returned no page bytes"
        )
    return buffers


class Compile:
    def __init__(self) -> None:
        self._py_compilers: dict[tuple[str, str], object] = {}

    def _py_compiler(self, src: Path, workdir: Path):
        key = (str(src.resolve()), str(workdir.resolve()))
        cached = self._py_compilers.get(key)
        if cached is not None:
            return cached
        typst_py = _import_typst_py()
        try:
            compiler = typst_py.Compiler(
                str(src),
                root=str(workdir),
                package_cache_path=str(_package_cache_path()),
            )
        except Exception as exc:
            raise _typst_py_error(exc, "compiler init") from exc
        self._py_compilers[key] = compiler
        return compiler

    def compile(
        self,
        workdir: str | Path,
        file: str = "index.typst",
        enable_ghostscript: bool = False,
        tools_dir: str | Path | None = None,
    ) -> Path:
        workdir = Path(workdir)
        backend = resolve_typst_backend()
        if backend == "cli":
            typst = ensure_typst(tools_dir=tools_dir)
            self._compile_typst(typst, workdir, file)
        else:
            self._compile_typst_py(workdir, file)
        if enable_ghostscript:
            self._run_ghostscript(workdir)
        return workdir / OUTPUT_FILE

    def _compile_typst(self, typst: Path, workdir: Path, file: str) -> None:
        src = workdir / file
        dest = workdir / OUTPUT_FILE
        print("Compiling with typst (cli)...")
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

    def _compile_typst_py(self, workdir: Path, file: str) -> None:
        src = workdir / file
        dest = workdir / OUTPUT_FILE
        print("Compiling with typst (py)...")
        started = time.perf_counter()
        try:
            compiler = self._py_compiler(src, workdir)
            compiler.compile(output=str(dest), format="pdf")
        except Exception as exc:
            if isinstance(exc, CompileError):
                raise
            raise _typst_py_error(exc, "compile") from exc
        print(f"Typst compilation time: {time.perf_counter() - started:.2f}s")
        if not dest.is_file() or dest.stat().st_size == 0:
            raise CompileError(f"typst (py) did not write {dest}")

    def compile_svg(
        self,
        workdir: str | Path,
        file: str = "index.typst",
        pages: list[int] | None = None,
        dest_pattern: str = "preview-{p}.svg",
        tools_dir: str | Path | None = None,
    ) -> list[Path]:
        """Compile selected pages to SVG. Refuses a full-book dump."""
        from parch.services.preview_svg import format_pages

        workdir = Path(workdir)
        if not pages:
            raise CompileError("SVG preview needs an explicit page list")
        if "{p}" not in dest_pattern:
            raise CompileError("SVG dest pattern must include {p}")
        backend = resolve_typst_backend()
        if backend == "cli":
            return self._compile_svg_cli(
                workdir, file, pages, dest_pattern, tools_dir, format_pages
            )
        return self._compile_svg_py(workdir, file, pages, dest_pattern)

    def _compile_svg_cli(
        self,
        workdir: Path,
        file: str,
        pages: list[int],
        dest_pattern: str,
        tools_dir: str | Path | None,
        format_pages,
    ) -> list[Path]:
        typst = ensure_typst(tools_dir=tools_dir)
        src = workdir / file
        dest = workdir / dest_pattern
        print("Compiling SVG pages with typst (cli)...")
        started = time.perf_counter()
        result = subprocess.run(
            [
                str(typst),
                "compile",
                "--format",
                "svg",
                "--pages",
                format_pages(pages),
                str(src),
                str(dest),
            ],
            capture_output=True,
            text=True,
        )
        print(f"Typst SVG compilation time: {time.perf_counter() - started:.2f}s")
        if result.returncode != 0:
            raise CompileError(
                f"typst svg compile failed ({result.returncode}):\n{result.stdout}\n{result.stderr}"
            )
        return self._svg_dest_paths(workdir, dest_pattern, pages)

    def _compile_svg_py(
        self,
        workdir: Path,
        file: str,
        pages: list[int],
        dest_pattern: str,
    ) -> list[Path]:
        src = workdir / file
        dest = workdir / dest_pattern
        compiler = self._py_compiler(src, workdir)
        print("Compiling SVG pages with typst (py)...")
        started = time.perf_counter()
        page_arg = _py_pages_param(compiler.compile)
        if page_arg is not None:
            try:
                compiler.compile(output=str(dest), format="svg", **{page_arg: pages})
            except Exception as exc:
                if isinstance(exc, CompileError):
                    raise
                raise _typst_py_error(exc, "svg compile") from exc
            print(f"Typst SVG compilation time: {time.perf_counter() - started:.2f}s")
            return self._svg_dest_paths(workdir, dest_pattern, pages)
        # typst-py 0.15.0 has no pages= arg. output="preview-{p}.svg" would
        # write every page to disk; compile(format="svg") returns list[bytes].
        try:
            result = compiler.compile(format="svg")
        except Exception as exc:
            if isinstance(exc, CompileError):
                raise
            raise _typst_py_error(exc, "svg compile") from exc
        print(f"Typst SVG compilation time: {time.perf_counter() - started:.2f}s")
        buffers = _svg_page_buffers(result)
        written: list[Path] = []
        total = len(buffers)
        for n in pages:
            if n < 1 or n > total:
                raise CompileError(
                    f"typst (py) page {n} out of range (document has {total} pages)"
                )
            path = workdir / dest_pattern.replace("{p}", str(n))
            path.write_bytes(buffers[n - 1])
            if not path.is_file() or path.stat().st_size == 0:
                raise CompileError(f"typst (py) did not write {path}")
            written.append(path)
        return written

    def _svg_dest_paths(
        self, workdir: Path, dest_pattern: str, pages: list[int]
    ) -> list[Path]:
        written: list[Path] = []
        for n in pages:
            path = workdir / dest_pattern.replace("{p}", str(n))
            if not path.is_file() or path.stat().st_size == 0:
                raise CompileError(f"typst did not write {path}")
            written.append(path)
        return written

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
        # repo root: src/parch/services/compile.py → parents[3]
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


def _zip_member_target(dest_dir: Path, name: str) -> Path:
    """Return the extract path if ``name`` stays inside ``dest_dir``.

    Raises CompileError on Zip Slip (``../``, absolute paths).
    """
    dest = dest_dir.resolve()
    if Path(name).is_absolute():
        raise CompileError(f"refusing to extract {name!r} outside {dest}")
    target = (dest / name).resolve()
    try:
        target.relative_to(dest)
    except ValueError as exc:
        raise CompileError(f"refusing to extract {name!r} outside {dest}") from exc
    return target


def _extract_zip(archive: Path, dest_dir: Path) -> None:
    dest = dest_dir.resolve()
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            _zip_member_target(dest, info.filename)
        zf.extractall(dest)


def _extract_archive(archive: Path, dest_dir: Path) -> None:
    if archive.suffix == ".zip" or archive.name.endswith(".zip"):
        _extract_zip(archive, dest_dir)
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
