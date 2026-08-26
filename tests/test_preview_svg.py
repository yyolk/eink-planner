from pathlib import Path

import pytest

from eink_planner.cli import build_parser, samples_dest
from eink_planner.services.compile import Compile, CompileError
from eink_planner.services.preview_svg import (
    DEFAULT_SCALE,
    crop_svg,
    format_pages,
    parse_pages,
    preview_svg,
    scale_svg,
)

REPO = __import__("pathlib").Path(__file__).resolve().parents[1]

_TINY = """<svg viewBox="0 0 400 600" width="400pt" height="600pt" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><g transform="matrix(1 0 0 -1 100 80)"><use xlink:href="#g" x="0" y="0"/><use xlink:href="#g" x="20" y="0"/></g><defs><symbol id="g" overflow="visible"><path d="M 0 0"/></symbol></defs></svg>"""


def test_parse_pages_list_and_range():
    assert parse_pages("1,3-5,8") == [1, 3, 4, 5, 8]
    assert format_pages([1, 2, 7]) == "1,2,7"


def test_parse_pages_rejects_empty_and_zero():
    with pytest.raises(ValueError, match="at least one"):
        parse_pages(" , ")
    with pytest.raises(ValueError, match="1-based"):
        parse_pages("0")
    with pytest.raises(ValueError, match="bad page range"):
        parse_pages("5-2")


def test_scale_svg_keeps_viewbox():
    out = scale_svg(_TINY, 0.25)
    assert 'viewBox="0 0 400 600"' in out
    assert 'width="100.0pt"' in out
    assert 'height="150.0pt"' in out


def test_crop_svg_follows_typst_y_flip():
    out = crop_svg(_TINY, pad=10)
    assert 'viewBox="90.0 70.0 40.0 20.0"' in out
    assert 'width="40.0pt"' in out
    assert 'height="20.0pt"' in out


def test_preview_svg_crop_then_scale():
    out = preview_svg(_TINY, scale=0.5, crop=True)
    assert 'viewBox="68.0 48.0 84.0 64.0"' in out
    assert 'width="42.0pt"' in out
    assert 'height="32.0pt"' in out


def test_preview_svg_cli_defaults():
    parser = build_parser()
    args = parser.parse_args(
        ["preview-svg", "configs/158x210-mos-left.toml", "--pages", "1,2"]
    )
    assert args.command == "preview-svg"
    assert args.scale == DEFAULT_SCALE
    assert args.crop is False
    assert args.pages == "1,2"


def test_preview_svg_cli_samples():
    parser = build_parser()
    args = parser.parse_args(
        ["preview-svg", "configs/158x210-mos-left.toml", "--samples"]
    )
    assert args.samples is True
    assert args.pages is None
    assert args.scale == DEFAULT_SCALE
    assert args.crop is False


def test_preview_svg_cli_pages_and_samples_conflict():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "preview-svg",
                "configs/158x210-mos-left.toml",
                "--pages",
                "1,2",
                "--samples",
            ]
        )


def test_preview_svg_cli_requires_pages_or_samples():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["preview-svg", "configs/158x210-mos-left.toml"])


def test_samples_dest_uses_config_stem():
    assert samples_dest(Path("/repo"), "configs/158x210-mos-left.toml") == Path(
        "/repo/docs/samples/158x210-mos-left"
    )


def test_generate_cli_unchanged():
    parser = build_parser()
    args = parser.parse_args(["generate", "configs/supernote-nomad.toml"])
    assert args.command == "generate"
    assert not hasattr(args, "pages") or args.command == "generate"


def test_compile_svg_refuses_missing_pages(tmp_path):
    with pytest.raises(CompileError, match="explicit page list"):
        Compile().compile_svg(tmp_path, pages=[])


def test_compile_svg_tiny_two_pages(tmp_path):
    src = tmp_path / "index.typst"
    src.write_text("#set page(width: 80pt, height: 100pt)\n= A\n#pagebreak()\n= B\n")
    paths = Compile().compile_svg(
        tmp_path,
        pages=[1, 2],
        dest_pattern="preview-{p}.svg",
        tools_dir=REPO / ".tools",
    )
    assert [p.name for p in paths] == ["preview-1.svg", "preview-2.svg"]
    for path in paths:
        text = path.read_text()
        assert "<svg" in text
        assert "viewBox=" in text
        assert path.stat().st_size > 0


def test_sample_page_numbers_from_labels():
    from eink_planner.services.preview_svg import sample_page_numbers

    typst = """
cover
#pagebreak()
text(size: h1)[2026<annual>]
padded_link(<quarter-2026-1>)
padded_link(<month-2026-01-01>)
padded_link(<2026W01>)
padded_link(<quarter-2026-1>, [Q1])
#pagebreak()
text(size: h1)[Quarter 1 <quarter-2026-1>]
#pagebreak()
padding
#pagebreak()
text(size: h1)[January<month-2026-01-01>]
#pagebreak()
text(size: h1)[Week 1 <2026W01>]
#pagebreak()
text(size: h1)[1 <2026-01-01>]
padded_link(<daily-note-2026-01-01-page-1>)
#pagebreak()
text(size: h1)[1 <daily-note-2026-01-01-page-1>]
#pagebreak()
About this notebook
"""
    pages = sample_page_numbers(
        typst, year=2026, week_id="2026W01", jan1="2026-01-01"
    )
    assert pages == {
        "cover": 1,
        "annual": 2,
        "quarterly-q1": 3,
        "monthly-jan": 5,
        "weekly-w01": 6,
        "daily-jan1": 7,
        "notes-jan1": 8,
        "colophon": 9,
    }


def test_sample_page_numbers_missing_label():
    from eink_planner.services.preview_svg import sample_page_numbers

    with pytest.raises(ValueError, match="annual"):
        sample_page_numbers("cover only", year=2026, week_id="2026W01", jan1="2026-01-01")
