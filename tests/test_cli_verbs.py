"""Thin dispatch smoke: press, proof, and new."""

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


def test_press_dispatch_handler():
    parser = build_parser()
    press = parser.parse_args(["press", "supernote-nomad"])
    assert press.run is generate_cmd
    assert press.command == "press"


def test_proof_dispatch_handler():
    parser = build_parser()
    proof = parser.parse_args(["proof", "158x210-mos-left", "--samples"])
    assert proof.run is preview_svg_cmd
    assert proof.command == "proof"


def test_new_dispatch_handler():
    parser = build_parser()
    args = parser.parse_args(["new", "--yes", "-o", "mine.toml"])
    assert args.run is new_cmd
    assert args.command == "new"


def test_verb_help_smokes(capsys):
    for verb in ("press", "proof", "new"):
        with pytest.raises(SystemExit) as exc:
            main([verb, "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "usage:" in out


def test_press_help(capsys):
    with pytest.raises(SystemExit) as press_exc:
        main(["press", "--help"])
    assert press_exc.value.code == 0
    press_help = capsys.readouterr().out
    assert "--workdir" in press_help
    assert "--pages" not in press_help


def test_proof_help(capsys):
    with pytest.raises(SystemExit) as proof_exc:
        main(["proof", "--help"])
    assert proof_exc.value.code == 0
    proof_help = capsys.readouterr().out
    assert "--pages" in proof_help
    assert "--samples" in proof_help


def test_dropped_aliases_are_unknown(capsys):
    for verb in ("generate", "preview-svg"):
        with pytest.raises(SystemExit) as exc:
            main([verb, "--help"])
        assert exc.value.code != 0
        err = capsys.readouterr().err
        assert "invalid choice" in err
