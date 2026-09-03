from pathlib import Path

import pytest

from parch.cli import build_parser, generate_cmd, preview_svg_cmd, samples_dest
from parch.config import load
from parch.mos.configurator import Configurator
from parch.mos.preamble import Preamble, copy_house_typ, house_typ_resource
from parch.services.compile import Compile, CompileError
from parch.services.generate import Generate
from parch.services.job_file import DEFAULT_SECTIONS
from parch.services.preview_svg import (
    DEFAULT_SCALE,
    SAMPLE_STEMS,
    crop_svg,
    format_pages,
    parse_pages,
    preview_svg,
    sample_page_numbers,
    sample_stems_for_sections,
    scale_svg,
)
from tests.helpers import base_config, load_default

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
        ["proof", "158x210", "--pages", "1,2"]
    )
    assert args.command == "proof"
    assert args.run is preview_svg_cmd
    assert args.scale == DEFAULT_SCALE
    assert args.crop is False
    assert args.pages == "1,2"


def test_preview_svg_cli_samples():
    parser = build_parser()
    args = parser.parse_args(
        ["proof", "158x210", "--samples"]
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
                "proof",
                "158x210",
                "--pages",
                "1,2",
                "--samples",
            ]
        )


def test_preview_svg_cli_requires_pages_or_samples():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["proof", "158x210"])


def test_samples_dest_uses_workdir_stem():
    assert samples_dest(Path("/tmp/out"), "158x210") == Path("/tmp/out/158x210")
    assert "docs" not in samples_dest(Path("/tmp/out"), "158x210").parts


def test_press_cli_unchanged():
    parser = build_parser()
    args = parser.parse_args(["press", "supernote-nomad"])
    assert args.command == "press"
    assert args.run is generate_cmd
    assert not hasattr(args, "pages")
    assert not hasattr(args, "samples")


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
    from parch.services.preview_svg import sample_page_numbers

    typst = """
cover
#pagebreak()
text(size: h1, weight: "bold")[Contents <index>]
About this notebook
padded_link(<2026W01>, box(width: 100%, height: 100%, align(horizon + left, [Weeks])))
#pagebreak()
text(size: h1)[2026<annual>]
padded_link(<index>)
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
text(size: h1)[Week 1 <2026W01> #h(0.6em) Dec 29 – Jan 4]
#pagebreak()
text(size: h1)[1 <2026-01-01>]
padded_link(<daily-note-2026-01-01-page-1>)
#pagebreak()
text(size: h1)[1 <daily-note-2026-01-01-page-1>]
#pagebreak()
text(size: h1)[Projects <projects>]
#pagebreak()
text(size: h1)[Habits <habits>]
#pagebreak()
text(size: h1)[Review <review>]
#pagebreak()
text(size: h1)[Tasks <tasks>]
#pagebreak()
text(size: h1)[Meetings <meetings>]
#pagebreak()
text(size: h1, weight: "bold")[About this notebook <colophon>]
"""
    pages = sample_page_numbers(
        typst, year=2026, week_id="2026W01", jan1="2026-01-01"
    )
    assert pages == {
        "cover": 1,
        "contents": 2,
        "annual": 3,
        "quarterly-q1": 4,
        "monthly-jan": 6,
        "weekly-w01": 7,
        "daily-jan1": 8,
        "notes-jan1": 9,
        "projects": 10,
        "habits": 11,
        "review": 12,
        "tasks": 13,
        "meetings": 14,
        "colophon": 15,
    }


def test_sample_page_numbers_missing_label():
    with pytest.raises(ValueError, match="contents"):
        sample_page_numbers("cover only", year=2026, week_id="2026W01", jan1="2026-01-01")


def test_sample_stems_include_canonical_extras():
    for stem in ("projects", "habits", "review", "tasks", "meetings"):
        assert stem in SAMPLE_STEMS
    assert SAMPLE_STEMS.index("projects") < SAMPLE_STEMS.index("colophon")


def test_sample_page_numbers_finds_extras_in_generated_book():
    typst = Generate(i18n=load_default()).generate(load(base_config("158x210", extras=True)))
    pages = sample_page_numbers(
        typst, year=2026, week_id="2026W01", jan1="2026-01-01", stems=SAMPLE_STEMS
    )
    for stem in SAMPLE_STEMS:
        assert stem in pages
        assert pages[stem] >= 1
    assert pages["projects"] < pages["habits"] < pages["review"]
    assert pages["review"] < pages["tasks"] < pages["meetings"] < pages["colophon"]


def test_sample_stems_for_default_sections_omit_extras():
    stems = sample_stems_for_sections(DEFAULT_SECTIONS)
    for extra in ("projects", "habits", "review", "tasks", "meetings"):
        assert extra not in stems
    assert stems[0] == "cover"
    assert stems[-1] == "colophon"
    assert "contents" in stems
    assert "notes-jan1" in stems


def test_sample_page_numbers_compact_job_does_not_request_extras():
    typst = Generate(i18n=load_default()).generate(load(base_config("158x210")))
    stems = sample_stems_for_sections(DEFAULT_SECTIONS)
    pages = sample_page_numbers(
        typst, year=2026, week_id="2026W01", jan1="2026-01-01", stems=stems
    )
    for extra in ("projects", "habits", "review", "tasks", "meetings"):
        assert extra not in pages
    assert "cover" in pages
    assert "colophon" in pages
    assert "contents" in pages


def test_sample_page_numbers_canonical_raises_if_extra_missing():
    typst = Generate(i18n=load_default()).generate(load(base_config("158x210")))
    with pytest.raises(ValueError, match="projects"):
        sample_page_numbers(
            typst, year=2026, week_id="2026W01", jan1="2026-01-01", stems=SAMPLE_STEMS
        )


def _house_paper() -> str:
    text = house_typ_resource().read_text(encoding="utf-8")
    start = text.index("#let dotted_centered(")
    end = text.index("#let padded_link(")
    return text[start:end]


def test_house_paper_is_tiling_fill():
    house = house_typ_resource().read_text(encoding="utf-8")
    paper = _house_paper()
    typst = Preamble(Configurator(load(base_config("158x210")))).generate()
    assert "tiling(" in paper
    assert "#let dotted_centered(" in paper
    assert "#let lined_fill(" in paper
    assert "#let task_fill(" in paper
    assert "#let dotted(" not in house
    assert "#let lined(" not in house
    assert "#let rect_pattern(" not in house
    assert "#let rect_pattern_centered(" not in house
    assert "here().position()" not in house
    assert "rect_pattern" not in typst
    assert "#let trail_heading = trail_heading.with(shrink: page-width < 100mm)" in typst
    assert "lined_well(dotted_centered)" in typst
    assert "PageData" not in typst
    assert "heading_mark" not in typst
    assert "let seated_title" not in typst


def test_lined_well_svg_uses_tiling_fill(tmp_path):
    src = tmp_path / "index.typst"
    src.write_text(
        Preamble(Configurator(load(base_config("158x210")))).generate()
        + "\n#lined_well(dotted_centered)\n",
        encoding="utf-8",
    )
    copy_house_typ(tmp_path, device="158x210")
    paths = Compile().compile_svg(
        tmp_path,
        pages=[1],
        dest_pattern="preview-{p}.svg",
        tools_dir=REPO / ".tools",
    )
    raw = paths[0].read_text(encoding="utf-8")
    out = preview_svg(raw, scale=DEFAULT_SCALE, crop=False)
    assert "<pattern" in raw
    assert 'fill="url(#' in raw
    assert "<pattern" in out
    assert 'fill="url(#' in out
    assert 'viewBox="0 0 447.874015748 595.275590551"' in raw


def test_compile_svg_tiny_two_pages_py(tmp_path, monkeypatch):
    typst = pytest.importorskip("typst")
    assert typst is not None
    monkeypatch.setenv("PARCH_TYPST", "py")
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
