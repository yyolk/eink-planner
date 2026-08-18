import pytest

from eink_planner.services.compile import CompileError, typst_asset_name, typst_download_url


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
