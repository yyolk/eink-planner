"""parch new: copy a shipped TOML and overlay year / sections."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from parch.cli import build_parser, main
from parch.config import load
from parch.services.config_file import overlay_toml

REPO = Path(__file__).resolve().parents[1]
NOMAD = REPO / "configs" / "supernote-nomad.toml"


def test_new_yes_year(tmp_path, capsys):
    out = tmp_path / "mine.toml"
    rc = main(
        [
            "new",
            "--from",
            "supernote-nomad",
            "--year",
            "2027",
            "--yes",
            "-o",
            str(out),
        ]
    )
    assert rc == 0
    assert f"Wrote {out}" in capsys.readouterr().out
    text = out.read_text(encoding="utf-8")
    data = tomllib.loads(text)
    assert data["calendar"]["year"] == 2027
    assert data["section"]["cover"]["title"] == "2027"
    assert "cover" in data["sections"]
    assert "colophon" in data["sections"]
    load(out)
    assert "SuperNote Nomad" in text


def test_new_sections(tmp_path):
    out = tmp_path / "mine.toml"
    rc = main(
        [
            "new",
            "--from",
            "supernote-nomad",
            "--sections",
            "cover,annual,colophon",
            "--yes",
            "-o",
            str(out),
        ]
    )
    assert rc == 0
    data = tomllib.loads(out.read_text(encoding="utf-8"))
    assert data["sections"] == ["cover", "annual", "colophon"]
    load(out)


def test_new_refuses_overwrite_without_force(tmp_path, capsys):
    out = tmp_path / "mine.toml"
    out.write_text("keep\n", encoding="utf-8")
    rc = main(
        [
            "new",
            "--from",
            "supernote-nomad",
            "--year",
            "2027",
            "--yes",
            "-o",
            str(out),
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "already exists" in err
    assert out.read_text(encoding="utf-8") == "keep\n"

    rc = main(
        [
            "new",
            "--from",
            "supernote-nomad",
            "--year",
            "2027",
            "--yes",
            "--force",
            "-o",
            str(out),
        ]
    )
    assert rc == 0
    data = tomllib.loads(out.read_text(encoding="utf-8"))
    assert data["calendar"]["year"] == 2027


def test_new_yes_without_outfile_errors(capsys):
    rc = main(["new", "--from", "supernote-nomad", "--year", "2027", "--yes"])
    assert rc == 1
    assert "outfile is required" in capsys.readouterr().err


def test_new_from_existing_path_year_rollover(tmp_path):
    src = tmp_path / "last.toml"
    src.write_text(NOMAD.read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "out.toml"
    rc = main(
        [
            "new",
            "--from",
            str(src),
            "--year",
            "2027",
            "--yes",
            str(out),
        ]
    )
    assert rc == 0
    data = tomllib.loads(out.read_text(encoding="utf-8"))
    assert data["calendar"]["year"] == 2027
    assert data["section"]["cover"]["title"] == "2027"


def test_parser_new_and_top_help():
    parser = build_parser()
    args = parser.parse_args(
        ["new", "--from", "supernote-nomad", "--year", "2027", "--yes", "-o", "mine.toml"]
    )
    assert args.command == "new"
    assert args.year == 2027
    assert args.yes is True
    help_text = parser.format_help()
    assert "new" in help_text
    assert "generate" in help_text
    assert "Write a planner from a shipped profile." in help_text


def test_new_help_lists_device_names(capsys):
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["new", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Write a planner from a shipped profile." in out
    assert "Starting profile or path (default supernote-nomad)." in out
    assert "Year. Also updates a year-only cover title." in out
    assert "Sections to keep, comma-separated." in out
    assert "SuperNote Nomad" in out
    assert "SuperNote Nomad (left-handed)" in out
    assert "Kindle Scribe" in out
    assert "158×210 lined" in out
    assert "158×210 (left-handed)" in out
    assert "MOS-left" not in out
    assert "MOS-right" not in out


def test_no_config_or_mos_flags():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["config", "new"])
    with pytest.raises(SystemExit):
        parser.parse_args(["new", "--mos", "right", "--yes", "-o", "x.toml"])
    with pytest.raises(SystemExit):
        parser.parse_args(["edit", "x.toml"])


def test_new_year_zero_rejected(tmp_path, capsys):
    out = tmp_path / "mine.toml"
    rc = main(
        [
            "new",
            "--from",
            "supernote-nomad",
            "--year",
            "0",
            "--yes",
            "-o",
            str(out),
        ]
    )
    assert rc == 1
    assert "year must be between 1 and 9999" in capsys.readouterr().err
    assert not out.exists()
    assert not (tmp_path / "mine.toml.tmp.toml").exists()


def test_overlay_table_headers_allow_space_and_comment():
    text = (
        "[device]\n"
        "year = 1999\n"
        "name = \"x\"\n"
        "\n"
        "[ calendar ] # hi\n"
        "year = 2026\n"
        "week_starts = \"Monday\"\n"
        "\n"
        "[section.cover] # x\n"
        'title = "2026"\n'
    )
    written = overlay_toml(text, year=2027)
    data = tomllib.loads(written)
    assert data["calendar"]["year"] == 2027
    assert data["device"]["year"] == 1999
    assert data["section"]["cover"]["title"] == "2027"


def test_new_force_keeps_dest_when_source_invalid(tmp_path, capsys):
    dest = tmp_path / "mine.toml"
    dest.write_text(NOMAD.read_text(encoding="utf-8"), encoding="utf-8")
    before = dest.read_bytes()
    src = tmp_path / "bad.toml"
    src.write_text("[device]\nname = \"x\"\n", encoding="utf-8")
    rc = main(
        [
            "new",
            "--from",
            str(src),
            "--yes",
            "--force",
            "-o",
            str(dest),
        ]
    )
    assert rc == 1
    assert dest.read_bytes() == before
    assert not (tmp_path / "mine.toml.tmp.toml").exists()
    err = capsys.readouterr().err
    assert err
