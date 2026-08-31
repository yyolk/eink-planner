"""Provenance helpers: command line, version, git HEAD, config hash."""

import hashlib
import re
from pathlib import Path

import pytest

from parch import __version__
from parch.config import StrictDict
from parch.provenance import (
    apply_provenance,
    collect_provenance,
    config_sha256,
    format_command,
    git_head,
)

REPO = Path(__file__).resolve().parents[1]


def test_config_sha256_matches_hashlib(tmp_path):
    path = tmp_path / "cfg.toml"
    data = b'section colophon { }\n#true `ticks` "quotes"\n'
    path.write_bytes(data)
    assert config_sha256(path) == hashlib.sha256(data).hexdigest()


def test_format_command_joins_argv():
    assert format_command(["parch", "generate", "foo.toml"]) == "parch generate foo.toml"
    joined = format_command(["parch", "generate", "file with space.toml"])
    assert "parch generate" in joined
    assert "file with space.toml" in joined


def test_format_command_uses_basename_when_argv0_is_a_path():
    uv = "/home/box/.cache/uv/archive-v0/abc123/bin/parch"
    assert format_command([uv, "press", "-w", "out", "nomad.toml"]) == "parch press -w out nomad.toml"
    assert format_command(["/usr/bin/parch", "press", "nomad.toml"]) == "parch press nomad.toml"
    assert format_command(["parch", "press", "nomad.toml"]) == "parch press nomad.toml"


def test_git_head_this_repo():
    sha = git_head(REPO)
    if sha is None:
        pytest.skip("sdist/wheel / no .git")
    assert re.fullmatch(r"[0-9a-f]{40}", sha.lower()), sha


def test_git_head_from_file_inside_repo():
    assert git_head(REPO / "pyproject.toml") == git_head(REPO)


def test_git_head_missing_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert git_head(tmp_path) is None


def test_git_head_reads_ref_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/topic\n", encoding="utf-8")
    (git / "refs" / "heads" / "topic").write_text("a" * 40 + "\n", encoding="utf-8")
    assert git_head(tmp_path) == "a" * 40


def test_git_head_detached(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_text("b" * 40 + "\n", encoding="utf-8")
    assert git_head(tmp_path) == "b" * 40


def test_git_head_packed_refs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_text("ref: refs/heads/packed\n", encoding="utf-8")
    (git / "packed-refs").write_text(
        "# pack-refs with: peeled\n" + "c" * 40 + " refs/heads/packed\n",
        encoding="utf-8",
    )
    assert git_head(tmp_path) == "c" * 40


def test_git_head_worktree_gitdir_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main = tmp_path / "main"
    work = tmp_path / "work"
    (main / ".git" / "refs" / "heads").mkdir(parents=True)
    (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
    (main / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (main / ".git" / "refs" / "heads" / "main").write_text("d" * 40 + "\n", encoding="utf-8")
    (main / ".git" / "refs" / "heads" / "topic").write_text("e" * 40 + "\n", encoding="utf-8")
    wt = main / ".git" / "worktrees" / "wt"
    (wt / "HEAD").write_text("ref: refs/heads/topic\n", encoding="utf-8")
    (wt / "commondir").write_text("../..\n", encoding="utf-8")
    work.mkdir()
    (work / ".git").write_text(f"gitdir: {wt}\n", encoding="utf-8")
    assert git_head(work) == "e" * 40


def test_collect_provenance_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "x.toml"
    path.write_text("year 2026\n", encoding="utf-8")
    prov = collect_provenance(
        config_path=path,
        argv=["parch", "generate", str(path)],
        start=tmp_path,
    )
    assert set(prov) == {
        "command",
        "version",
        "git_sha",
        "config_path",
        "config_sha256",
        "config_text",
    }
    assert prov["version"] == __version__
    assert prov["config_text"] == "year 2026\n"
    assert prov["config_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert prov["git_sha"] is None
    assert "parch generate" in prov["command"]
    assert str(path) in prov["config_path"]


def test_apply_provenance_attaches_to_planner_params():
    dto = StrictDict({"planner": {"params": {}, "sections": []}})
    out = apply_provenance(dto, {"command": "parch generate x.toml", "git_sha": None})
    assert out["planner"]["params"]["provenance"]["command"] == "parch generate x.toml"
    assert "provenance" not in dto["planner"]["params"]
