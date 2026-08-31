"""Build-time provenance for the colophon. Not part of the TOML schema."""

import hashlib
import shlex
import subprocess
from pathlib import Path
from typing import Any

from parch import __version__
from parch.config import StrictDict


def config_sha256(path: str | Path) -> str:
    """SHA-256 hex digest of the config file bytes on disk."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def format_command(argv: list[str]) -> str:
    """Shell-join the real argv (``parch press ...``)."""
    parts = [str(part) for part in argv]
    if parts:
        parts[0] = Path(parts[0]).name
    return shlex.join(parts)


def git_head(start: Path) -> str | None:
    """Current HEAD SHA, walking up from *start* and then cwd.

    Reads ``.git`` from disk (directory, or a worktree ``gitdir:`` file).
    Does not compute a dirty-tree hash. Returns ``None`` if git cannot be
    found; callers must not fail generate.
    """
    seen: set[Path] = set()
    for origin in _search_origins(start):
        if origin in seen:
            continue
        seen.add(origin)
        git_dir = _locate_git_dir(origin)
        if git_dir is not None:
            sha = _read_git_head(git_dir)
            if sha:
                return sha
        sha = _git_rev_parse(origin)
        if sha:
            return sha
    return None


def collect_provenance(
    *,
    config_path: str | Path,
    argv: list[str],
    start: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    origin = Path(start) if start is not None else path
    text = ""
    digest = ""
    try:
        raw = path.read_bytes()
    except OSError:
        raw = None
    if raw is not None:
        digest = hashlib.sha256(raw).hexdigest()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
    return {
        "command": format_command(argv),
        "version": __version__,
        "git_sha": git_head(origin),
        "config_path": str(path),
        "config_sha256": digest,
        "config_text": text,
    }


def apply_provenance(dto: StrictDict, provenance: dict[str, Any]) -> StrictDict:
    """Attach runtime provenance onto the loaded DTO (not a config key)."""
    data = dto.to_plain()
    planner = data.setdefault("planner", {})
    if not isinstance(planner, dict):
        planner = {}
        data["planner"] = planner
    params = planner.setdefault("params", {})
    if not isinstance(params, dict):
        params = {}
        planner["params"] = params
    params["provenance"] = dict(provenance)
    return StrictDict(data)


def _search_origins(start: str | Path) -> list[Path]:
    origins: list[Path] = []
    try:
        origins.append(Path(start).resolve())
    except OSError:
        origins.append(Path(start))
    try:
        cwd = Path.cwd().resolve()
    except OSError:
        cwd = Path.cwd()
    if cwd not in origins:
        origins.append(cwd)
    return origins


def _locate_git_dir(start: Path) -> Path | None:
    current = start if start.is_dir() else start.parent
    for directory in [current, *current.parents]:
        marker = directory / ".git"
        if marker.is_dir():
            return marker
        if marker.is_file():
            resolved = _gitdir_from_file(marker)
            if resolved is not None:
                return resolved
    return None


def _gitdir_from_file(marker: Path) -> Path | None:
    try:
        text = marker.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("gitdir:"):
            raw = stripped.split(":", 1)[1].strip()
            path = Path(raw)
            if not path.is_absolute():
                path = (marker.parent / path).resolve()
            if path.is_dir():
                return path
    return None


def _read_git_head(git_dir: Path) -> str | None:
    head_path = git_dir / "HEAD"
    try:
        text = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text:
        return None
    if text.startswith("ref:"):
        ref = text.split(":", 1)[1].strip()
        return _read_ref(git_dir, ref)
    return text


def _read_ref(git_dir: Path, ref: str) -> str | None:
    common = _common_dir(git_dir)
    for root in (git_dir, common):
        ref_file = root / ref
        if ref_file.is_file():
            try:
                sha = ref_file.read_text(encoding="utf-8").strip()
            except OSError:
                sha = ""
            if sha:
                return sha
    packed = common / "packed-refs"
    if packed.is_file():
        try:
            lines = packed.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for line in lines:
            if not line or line.startswith("#") or line.startswith("^"):
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == ref:
                return parts[0]
    return None


def _common_dir(git_dir: Path) -> Path:
    marker = git_dir / "commondir"
    if not marker.is_file():
        return git_dir
    try:
        raw = marker.read_text(encoding="utf-8").strip()
    except OSError:
        return git_dir
    if not raw:
        return git_dir
    path = Path(raw)
    if not path.is_absolute():
        path = (git_dir / path).resolve()
    return path if path.is_dir() else git_dir


def _git_rev_parse(start: Path) -> str | None:
    cwd = start if start.is_dir() else start.parent
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    sha = (result.stdout or "").strip()
    if result.returncode == 0 and sha:
        return sha
    return None
