"""parch new writes a complete job from a device; parch edit reopens it."""

import tomllib

import pytest

from parch import ConfigError
from parch.cli import build_parser, main
from parch.config import load
from parch.devices import DEVICES, get_device, known_device_ids
from parch.services.job_file import (
    CANONICAL_SECTIONS,
    COMPACT_STYLE,
    DEFAULT_SECTIONS,
    emit_job,
    spec_from_data,
    spec_from_device,
)


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
    assert data["device"]["name"] == "supernote-nomad"
    assert data["style"]["scratch_pad"] == "dotted"
    assert data["sections"] == list(DEFAULT_SECTIONS)
    assert "projects" not in data["sections"]
    load(out)
    assert "SuperNote Nomad" in text


def test_new_from_is_device_id_not_path(tmp_path, capsys):
    src = tmp_path / "last.toml"
    src.write_text(emit_job(spec_from_device("supernote-nomad")), encoding="utf-8")
    out = tmp_path / "out.toml"
    rc = main(["new", "--from", str(src), "--year", "2027", "--yes", str(out)])
    assert rc == 1
    assert "device id" in capsys.readouterr().err
    assert not out.exists()


def test_new_from_lined_stem_is_unknown(tmp_path, capsys):
    out = tmp_path / "lined.toml"
    rc = main(["new", "--from", "supernote-nomad-lined", "--yes", "-o", str(out)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "unknown device" in err
    assert not out.exists()


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
    assert "section" in data
    assert "cover" in data["section"]
    assert "annual" in data["section"]
    assert "daily" not in data["section"]
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
    assert "edit" in help_text
    assert "press" in help_text
    assert "proof" in help_text
    assert "Write a job file from a device and defaults." in help_text


def test_new_help_lists_device_names(capsys):
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["new", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Write a complete job file from a device record plus defaults." in out
    assert "Device id (default supernote-nomad)." in out
    assert "Year. Also updates a year-only cover title." in out
    assert "Sections to keep, comma-separated." in out
    for device in DEVICES:
        assert device.name in out
    assert "lined" not in out.lower()
    assert "left-handed" not in out
    assert "MOS-left" not in out
    assert "MOS-right" not in out
    assert "--hand" in out
    assert "--paper" not in out


def test_no_config_or_mos_flags():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["config", "new"])
    with pytest.raises(SystemExit):
        parser.parse_args(["new", "--mos", "right", "--yes", "-o", "x.toml"])
    args = parser.parse_args(["new", "--hand", "right", "--yes", "-o", "x.toml"])
    assert args.hand == "right"
    with pytest.raises(SystemExit):
        parser.parse_args(["new", "--paper", "lined", "--yes", "-o", "x.toml"])
    edit = parser.parse_args(["edit", "x.toml"])
    assert edit.command == "edit"


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


def test_new_hand_writes_side_menu_only(tmp_path):
    out = tmp_path / "mine.toml"
    rc = main(
        [
            "new",
            "--from",
            "supernote-nomad",
            "--hand",
            "right",
            "--yes",
            "-o",
            str(out),
        ]
    )
    assert rc == 0
    data = tomllib.loads(out.read_text(encoding="utf-8"))
    assert data["mos"]["side_menu"] == "right"
    assert data["device"]["name"] == "supernote-nomad"
    assert "months_column" not in data["section"]["quarterly"]
    assert "week_placement" not in data["section"]["monthly"]
    assert "columns" not in data["section"]["daily"]
    assert "side_menu_width" not in data["mos"]
    assert data["mos"]["reverse_months_quarters"] is True
    assert "left" in data["section"]["daily"]
    assert "right" in data["section"]["daily"]
    assert "schedule" in data["section"]["daily"]["left"]
    assert "priorities" in data["section"]["daily"]["right"]
    load(out)


def test_new_dest_parent_is_file(tmp_path, capsys):
    parent = tmp_path / "existing_file"
    parent.write_text("keep\n", encoding="utf-8")
    out = parent / "child.toml"
    rc = main(
        [
            "new",
            "--from",
            "supernote-nomad",
            "--yes",
            "-o",
            str(out),
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "error:" in err
    assert str(out) in err
    assert "Traceback" not in err
    assert parent.read_text(encoding="utf-8") == "keep\n"
    assert parent.is_file()


def test_emit_job_is_complete_resume_state():
    text = emit_job(spec_from_device("supernote-nomad", paper="lined", week_placement="none"))
    data = tomllib.loads(text)
    assert data["style"]["scratch_pad"] == "lined"
    assert data["section"]["monthly"]["week_placement"] == "none"
    assert data["section"]["daily"]["right"]["notes"]["pattern"] == "dotted"
    assert data["section"]["daily_notes"]["pattern"] == "lined"
    assert data["section"]["daily"]["right"]["notes"]["title_height"] == "4mm"
    assert data["section"]["monthly"]["daily_cell_height"] == "16mm"
    spec = spec_from_data(data)
    assert spec.paper == "lined"
    assert spec.week_placement == "none"


def test_new_yes_writes_device_defaults(tmp_path):
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
    text = out.read_text(encoding="utf-8")
    data = tomllib.loads(text)
    assert data["calendar"]["year"] == 2027
    assert data["style"]["scratch_pad"] == "dotted"
    assert data["section"]["daily"]["left"]["schedule"]["hour_from"] == 8
    assert data["section"]["daily"]["left"]["schedule"]["hour_to"] == 20
    assert data["section"]["daily"]["right"]["priorities"]["count"] == 5
    assert "week_placement" not in data["section"]["monthly"]
    assert data["mos"]["side_menu"] == "left"
    assert data["mos"]["reverse_months_quarters"] is True
    assert 'title_height = "4mm"' in text
    assert 'daily_cell_height = "16mm"' in text
    load(out)


def test_defaults_omit_extras_on_every_device(tmp_path):
    extras = ("projects", "habits", "review", "tasks", "meetings")
    for device in known_device_ids():
        out = tmp_path / f"{device}.toml"
        rc = main(["new", "--from", device, "--yes", "-o", str(out)])
        assert rc == 0
        data = tomllib.loads(out.read_text(encoding="utf-8"))
        assert data["device"]["name"] == device
        assert data["sections"] == list(DEFAULT_SECTIONS)
        for extra in extras:
            assert extra not in data["sections"]
            assert extra not in data.get("section", {})
        assert data["device"]["ppi"] == get_device(device).ppi
        load(out)
    for extra in extras:
        assert extra in CANONICAL_SECTIONS


def test_new_from_manta_alias_writes_compact_style(tmp_path):
    out = tmp_path / "manta.toml"
    rc = main(["new", "--yes", "--from", "manta", "-o", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    data = tomllib.loads(text)
    assert data["device"]["name"] == "supernote-manta"
    assert data["sections"] == list(DEFAULT_SECTIONS)
    assert "projects" not in data["sections"]
    style = COMPACT_STYLE
    assert data["style"]["stroke"]["regular"] == style.stroke_regular
    assert data["style"]["type"]["body"] == style.type_body
    assert data["style"]["type"]["h1"] == style.type_h1
    assert data["section"]["cover"]["font_size"] == style.cover_font_size
    assert data["section"]["monthly"]["daily_cell_height"] == style.monthly_daily_cell_height
    assert data["section"]["daily"]["right"]["notes"]["title_height"] == style.notes_title_height
    assert data["section"]["daily"]["item_spacing"] == style.daily_item_spacing
    assert "SuperNote Manta" in text
    assert "Toolbar top 8mm." in text
    assert get_device("manta").id == "supernote-manta"
    load(out)


def test_sections_checkbox_offers_extras_unchecked(tmp_path, monkeypatch):
    out = tmp_path / "mine.toml"
    extras = ("projects", "habits", "review", "tasks", "meetings")

    class Capture(_FakeQuestionary):
        def checkbox(self, message, choices=None, validate=None):
            self.asked.append(message)
            self.captured = list(choices or [])
            picked = [choice.value for choice in self.captured if choice.checked]
            return _Ask(picked)

    fake = Capture(
        {
            "MOS side": "left",
            "Paper": "dotted",
            "Week rail": "omit",
            "Hour from": 8,
            "Hour to": 20,
            "Priority rows": 5,
            "Daily notes pages": 2,
        }
    )
    monkeypatch.setattr("parch.services.config_file._questionary", lambda: fake)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    rc = main(["new", "--from", "supernote-nomad", "--year", "2026", "-o", str(out)])
    assert rc == 0
    assert "Sections" in fake.asked
    checked = {choice.value: choice.checked for choice in fake.captured}
    assert list(checked) == list(CANONICAL_SECTIONS)
    for name in DEFAULT_SECTIONS:
        assert checked[name] is True
    for name in extras:
        assert checked[name] is False
    assert "Project pages" not in fake.asked
    data = tomllib.loads(out.read_text(encoding="utf-8"))
    assert data["sections"] == list(DEFAULT_SECTIONS)
    load(out)


class _Ask:
    def __init__(self, value):
        self.value = value

    def ask(self):
        return self.value


class _FakeQuestionary:
    def __init__(self, answers: dict[str, object]):
        self.answers = answers
        self.asked: list[str] = []

    class Choice:
        def __init__(self, title, value=None, checked=False):
            self.title = title
            self.value = title if value is None else value
            self.checked = checked

    def select(self, message, choices=None, default=None):
        self.asked.append(message)
        return _Ask(self.answers[message])

    def text(self, message, default=None, validate=None):
        self.asked.append(message)
        value = self.answers[message]
        if validate is not None:
            ok = validate(str(value))
            if ok is not True:
                raise AssertionError(ok)
        return _Ask(str(value))

    def checkbox(self, message, choices=None, validate=None):
        self.asked.append(message)
        return _Ask(self.answers[message])

    def path(self, message):
        self.asked.append(message)
        return _Ask(self.answers[message])


def test_interactive_new_writes_complete_job(tmp_path, monkeypatch):
    out = tmp_path / "mine.toml"
    fake = _FakeQuestionary(
        {
            "MOS side": "right",
            "Paper": "lined",
            "Week rail": "none",
            "Hour from": 7,
            "Hour to": 18,
            "Priority rows": 3,
            "Daily notes pages": 4,
            "Project pages": 8,
            "Project card rows": 2,
            "Habit columns": 6,
            "Meeting index pages": 2,
        }
    )
    monkeypatch.setattr("parch.services.config_file._questionary", lambda: fake)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    rc = main(
        [
            "new",
            "--from",
            "supernote-nomad",
            "--year",
            "2027",
            "--sections",
            "cover,monthly,daily,daily_notes,projects,habits,meetings,colophon",
            "-o",
            str(out),
        ]
    )
    assert rc == 0
    assert "title_height" not in fake.asked
    assert "daily_cell_height" not in fake.asked
    assert "MOS side" in fake.asked
    assert "Paper" in fake.asked
    text = out.read_text(encoding="utf-8")
    assert "SuperNote Nomad" in text
    assert text.index("[device]") < text.index("[calendar]")
    assert 'title_height = "4mm"' in text
    assert 'daily_cell_height = "16mm"' in text
    assert "reverse_months_quarters = true" in text
    data = tomllib.loads(text)
    assert data["calendar"]["year"] == 2027
    assert data["mos"]["side_menu"] == "right"
    assert data["mos"]["reverse_months_quarters"] is True
    assert data["style"]["scratch_pad"] == "lined"
    assert data["section"]["monthly"]["week_placement"] == "none"
    assert data["section"]["daily"]["left"]["schedule"]["hour_from"] == 7
    assert data["section"]["daily"]["left"]["schedule"]["hour_to"] == 18
    assert data["section"]["daily"]["right"]["priorities"]["count"] == 3
    assert data["section"]["daily_notes"]["pages"] == 4
    assert data["section"]["projects"]["pages"] == 8
    assert data["section"]["projects"]["card_rows"] == 2
    assert data["section"]["habits"]["habit_columns"] == 6
    assert data["section"]["meetings"]["index_pages"] == 2
    assert data["section"]["daily"]["right"]["notes"]["title_height"] == "4mm"
    load(out)


def test_interactive_hand_flag_skips_side_prompt(tmp_path, monkeypatch):
    out = tmp_path / "mine.toml"
    fake = _FakeQuestionary(
        {
            "Paper": "dotted",
            "Week rail": "omit",
            "Hour from": 8,
            "Hour to": 20,
            "Priority rows": 5,
            "Daily notes pages": 2,
        }
    )
    monkeypatch.setattr("parch.services.config_file._questionary", lambda: fake)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    rc = main(
        [
            "new",
            "--from",
            "supernote-nomad",
            "--year",
            "2027",
            "--hand",
            "right",
            "--sections",
            "cover,monthly,daily,daily_notes,colophon",
            "-o",
            str(out),
        ]
    )
    assert rc == 0
    assert "MOS side" not in fake.asked
    data = tomllib.loads(out.read_text(encoding="utf-8"))
    assert data["mos"]["side_menu"] == "right"
    assert "week_placement" not in data["section"]["monthly"]
    assert "projects" not in data["sections"]
    load(out)


def test_edit_reopens_same_file(tmp_path, monkeypatch):
    dest = tmp_path / "job.toml"
    dest.write_text(emit_job(spec_from_device("kindle-scribe", year=2026)), encoding="utf-8")
    fake = _FakeQuestionary(
        {
            "Year": 2028,
            "Sections": ["cover", "monthly", "daily", "colophon"],
            "MOS side": "right",
            "Paper": "lined",
            "Week rail": "none",
            "Hour from": 9,
            "Hour to": 17,
            "Priority rows": 4,
        }
    )
    monkeypatch.setattr("parch.services.config_file._questionary", lambda: fake)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    rc = main(["edit", str(dest)])
    assert rc == 0
    data = tomllib.loads(dest.read_text(encoding="utf-8"))
    assert data["device"]["name"] == "kindle-scribe"
    assert data["calendar"]["year"] == 2028
    assert data["style"]["scratch_pad"] == "lined"
    assert data["mos"]["side_menu"] == "right"
    assert data["section"]["monthly"]["week_placement"] == "none"
    assert data["section"]["daily"]["left"]["schedule"]["hour_from"] == 9
    assert data["sections"] == ["cover", "monthly", "daily", "colophon"]
    load(dest)


def test_edit_without_tty_errors(tmp_path, capsys, monkeypatch):
    dest = tmp_path / "job.toml"
    dest.write_text(emit_job(spec_from_device("supernote-nomad")), encoding="utf-8")
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    rc = main(["edit", str(dest)])
    assert rc == 1
    assert "TTY" in capsys.readouterr().err


def test_hand_edit_still_loads(tmp_path):
    dest = tmp_path / "hand.toml"
    dest.write_text(emit_job(spec_from_device("158x210", year=2026)), encoding="utf-8")
    text = dest.read_text(encoding="utf-8")
    text = text.replace('scratch_pad = "dotted"', 'scratch_pad = "lined"')
    dest.write_text(text, encoding="utf-8")
    dto = load(dest)
    assert dto["planner"]["params"]["scratch_pad"] == "lined"
    assert dto["device"] == "158x210"
