import pytest

from parch.services.compile import CompileError, typst_asset_name, typst_download_url


CASES = [
    ("darwin", "x86_64", "typst-x86_64-apple-darwin.tar.xz"),
    ("darwin", "amd64", "typst-x86_64-apple-darwin.tar.xz"),
    ("darwin", "arm64", "typst-aarch64-apple-darwin.tar.xz"),
    ("darwin", "aarch64", "typst-aarch64-apple-darwin.tar.xz"),
    ("linux", "x86_64", "typst-x86_64-unknown-linux-musl.tar.xz"),
    ("linux", "amd64", "typst-x86_64-unknown-linux-musl.tar.xz"),
    ("linux", "aarch64", "typst-aarch64-unknown-linux-musl.tar.xz"),
    ("linux", "arm64", "typst-aarch64-unknown-linux-musl.tar.xz"),
    ("linux", "armv7l", "typst-armv7-unknown-linux-musleabi.tar.xz"),
    ("linux", "riscv64", "typst-riscv64gc-unknown-linux-gnu.tar.xz"),
    ("win32", "x86_64", "typst-x86_64-pc-windows-msvc.zip"),
    ("win32", "amd64", "typst-x86_64-pc-windows-msvc.zip"),
    ("win32", "arm64", "typst-aarch64-pc-windows-msvc.zip"),
    ("win32", "aarch64", "typst-aarch64-pc-windows-msvc.zip"),
]


@pytest.mark.parametrize("plat,machine,asset", CASES)
def test_typst_asset_name(plat, machine, asset):
    assert typst_asset_name(plat, machine) == asset


@pytest.mark.parametrize(
    "plat,machine,asset",
    [
        ("Darwin", "X86_64", "typst-x86_64-apple-darwin.tar.xz"),
        ("LINUX", "AMD64", "typst-x86_64-unknown-linux-musl.tar.xz"),
        ("Win32", "AMD64", "typst-x86_64-pc-windows-msvc.zip"),
        ("WIN32", "ARM64", "typst-aarch64-pc-windows-msvc.zip"),
    ],
)
def test_typst_asset_name_is_case_insensitive(plat, machine, asset):
    assert typst_asset_name(plat, machine) == asset


def test_typst_asset_name_unknown_platform_raises():
    with pytest.raises(CompileError, match=r"unsupported platform/arch"):
        typst_asset_name("freebsd", "x86_64")


def test_typst_asset_name_unknown_arch_lists_supported_pairs():
    with pytest.raises(CompileError, match=r"darwin \+ x86_64/amd64") as excinfo:
        typst_asset_name("linux", "ppc64le")
    message = str(excinfo.value)
    assert "linux + aarch64/arm64" in message
    assert "win32 + arm64/aarch64" in message
    assert "'linux' / 'ppc64le'" in message


def test_typst_download_url_uses_pin_and_asset():
    asset = "typst-x86_64-unknown-linux-musl.tar.xz"
    assert typst_download_url(asset) == (
        f"https://github.com/typst/typst/releases/download/v0.15.1/{asset}"
    )


import shutil
import zipfile
from pathlib import Path

import parch.services.compile as compile_mod
from parch.services.compile import (
    _cached_typst_matches_pin,
    _extract_archive,
    _parse_typst_version,
    _zip_member_target,
    ensure_typst,
)


def test_parse_typst_version_from_cli_text():
    assert _parse_typst_version("typst 0.15.1 (9dfd3a08)") == (0, 15, 1)
    assert _parse_typst_version("") is None
    assert _parse_typst_version("not a version") is None


def test_cached_typst_matches_pin(monkeypatch, tmp_path):
    fake = tmp_path / "typst"
    fake.write_text("")
    monkeypatch.setattr(compile_mod, "_typst_version_text", lambda _b: "typst 0.15.1")
    assert _cached_typst_matches_pin(fake) is True
    monkeypatch.setattr(compile_mod, "_typst_version_text", lambda _b: "typst 0.13.1")
    assert _cached_typst_matches_pin(fake) is False
    monkeypatch.setattr(compile_mod, "_typst_version_text", lambda _b: "")
    assert _cached_typst_matches_pin(fake) is False


def test_ensure_typst_reuses_matching_cache(monkeypatch, tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    cached = tools / "typst"
    cached.write_text("pin")
    cached.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _n: None)
    monkeypatch.setattr(compile_mod, "_typst_version_text", lambda _b: "typst 0.15.1 (abc)")
    monkeypatch.setattr(
        compile_mod,
        "_download_typst",
        lambda dest: (_ for _ in ()).throw(AssertionError("should not download")),
    )
    assert ensure_typst(tools_dir=tools) == cached
    assert cached.read_text() == "pin"


def test_ensure_typst_redownloads_stale_cache(monkeypatch, tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    cached = tools / "typst"
    cached.write_text("old")
    cached.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _n: None)
    monkeypatch.setattr(compile_mod, "_typst_version_text", lambda _b: "typst 0.13.1")

    def fake_download(dest):
        dest.write_text("new")

    monkeypatch.setattr(compile_mod, "_download_typst", fake_download)
    assert ensure_typst(tools_dir=tools) == cached
    assert cached.read_text() == "new"


def test_ensure_typst_uses_path_even_when_older(monkeypatch, tmp_path):
    path_bin = tmp_path / "bin" / "typst"
    path_bin.parent.mkdir()
    path_bin.write_text("path")
    path_bin.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _n: str(path_bin))
    monkeypatch.setattr(compile_mod, "_typst_version_text", lambda _b: "typst 0.13.1")
    monkeypatch.setattr(
        compile_mod,
        "_download_typst",
        lambda dest: (_ for _ in ()).throw(AssertionError("should not download")),
    )
    assert ensure_typst(tools_dir=tmp_path / "tools") == path_bin


def _write_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def test_extract_zip_keeps_members_inside_dest(tmp_path):
    archive = tmp_path / "ok.zip"
    dest = tmp_path / "out"
    dest.mkdir()
    _write_zip(archive, {"typst-x86_64-pc-windows-msvc/typst.exe": b"ok"})
    _extract_archive(archive, dest)
    extracted = dest / "typst-x86_64-pc-windows-msvc" / "typst.exe"
    assert extracted.read_bytes() == b"ok"


def test_extract_zip_rejects_path_traversal(tmp_path):
    archive = tmp_path / "bad.zip"
    dest = tmp_path / "out"
    dest.mkdir()
    _write_zip(archive, {"../../evil": b"nope"})
    with pytest.raises(CompileError, match=r"refusing to extract"):
        _extract_archive(archive, dest)
    assert not (tmp_path / "evil").exists()


def test_zip_member_target_rejects_absolute_path(tmp_path):
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(CompileError, match=r"refusing to extract"):
        _zip_member_target(dest, "/tmp/evil")
