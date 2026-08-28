"""Thin alias-dispatch smoke: press/generate and proof/preview-svg."""

from __future__ import annotations

import pytest

from parch.cli import build_parser, generate_cmd, main, new_cmd, preview_svg_cmd


def test_top_help_lists_canonical_verbs():
    help_text = build_parser().format_help()
    assert "press" in help_text
    assert "proof" in help_text
    assert "new" in help_text
    assert "Press a profile to PDF" in help_text
    assert "Pull SVG proofs of selected pages" in help_text
    assert "Write a profile from a shipped template." in help_text


def test_press_and_generate_dispatch_same_handler():
    parser = build_parser()
    press = parser.parse_args(["press", "supernote-nomad"])
    generate = parser.parse_args(["generate", "supernote-nomad"])
    assert press.run is generate_cmd
    assert generate.run is generate_cmd
    assert press.command in ("press", "generate")
    assert generate.command in ("press", "generate")


def test_proof_and_preview_svg_dispatch_same_handler():
    parser = build_parser()
    proof = parser.parse_args(["proof", "158x210-mos-left", "--samples"])
    preview = parser.parse_args(["preview-svg", "158x210-mos-left", "--samples"])
    assert proof.run is preview_svg_cmd
    assert preview.run is preview_svg_cmd
    assert proof.command in ("proof", "preview-svg")
    assert preview.command in ("proof", "preview-svg")


def test_new_dispatch_handler():
    parser = build_parser()
    args = parser.parse_args(["new", "--yes", "-o", "mine.toml"])
    assert args.run is new_cmd
    assert args.command == "new"


def test_verb_help_smokes(capsys):
    for verb in ("press", "generate", "proof", "preview-svg", "new"):
        with pytest.raises(SystemExit) as exc:
            main([verb, "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "usage:" in out


def test_press_generate_help_same_command(capsys):
    with pytest.raises(SystemExit) as press_exc:
        main(["press", "--help"])
    assert press_exc.value.code == 0
    press_help = capsys.readouterr().out
    with pytest.raises(SystemExit) as gen_exc:
        main(["generate", "--help"])
    assert gen_exc.value.code == 0
    generate_help = capsys.readouterr().out
    assert "--workdir" in press_help
    assert "--workdir" in generate_help
    assert "--pages" not in press_help
    assert press_help == generate_help


def test_proof_preview_svg_help_same_command(capsys):
    with pytest.raises(SystemExit) as proof_exc:
        main(["proof", "--help"])
    assert proof_exc.value.code == 0
    proof_help = capsys.readouterr().out
    with pytest.raises(SystemExit) as prev_exc:
        main(["preview-svg", "--help"])
    assert prev_exc.value.code == 0
    preview_help = capsys.readouterr().out
    assert "--pages" in proof_help
    assert "--samples" in proof_help
    assert proof_help == preview_help
