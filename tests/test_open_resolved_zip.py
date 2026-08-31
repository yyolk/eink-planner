"""Zip-backed open_resolved keeps the extracted profile alive through load."""

import importlib
import sys
import tomllib
from importlib.resources import as_file, files
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from parch.services.config_file import open_resolved


def test_open_resolved_reads_zip_backed_toml(tmp_path, monkeypatch):
    archive = tmp_path / "probe.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as package:
        package.writestr("probe_pkg/__init__.py", "")
        package.writestr("probe_pkg/configs/zip-probe.toml", "[calendar]\nyear = 2026\n")

    sys.path.insert(0, str(archive))
    importlib.invalidate_caches()
    try:
        resource = files("probe_pkg") / "configs" / "zip-probe.toml"
        with as_file(resource) as path:
            escaped = Path(path)
            assert escaped.read_text(encoding="utf-8") == "[calendar]\nyear = 2026\n"
        assert not escaped.exists()

        monkeypatch.setattr(
            "parch.services.config_file.files",
            lambda _name: files("probe_pkg"),
        )
        with open_resolved("zip-probe") as path:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            assert data["calendar"]["year"] == 2026
    finally:
        sys.path.remove(str(archive))
        sys.modules.pop("probe_pkg", None)
        importlib.invalidate_caches()
