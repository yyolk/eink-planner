"""open_resolved yields a path for a job file or a device id."""

import tomllib

from parch.services.config_file import open_resolved
from parch.services.job_file import emit_job, spec_from_device


def test_open_resolved_device_id_writes_complete_job():
    with open_resolved("supernote-nomad") as path:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        assert data["device"]["name"] == "supernote-nomad"
        assert data["calendar"]["year"] == 2026
        assert "sections" in data


def test_open_resolved_existing_path(tmp_path):
    dest = tmp_path / "job.toml"
    dest.write_text(emit_job(spec_from_device("158x210")), encoding="utf-8")
    with open_resolved(str(dest)) as path:
        assert path == dest
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        assert data["device"]["name"] == "158x210"
