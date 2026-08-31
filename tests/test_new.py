"""parch new: copy a shipped TOML and overlay year / sections."""

import tomllib

import pytest

from parch import ConfigError
from parch.cli import build_parser, main
from parch.config import load
from parch.services.config_file import overlay_toml
from tests.helpers import base_config

NOMAD = base_config("supernote-nomad")


@pytest.mark.parametrize(
    "stem",
    ["supernote-nomad-lined", "kindle-scribe-lined"],
)
def test_new_from_lined_siblings(tmp_path, stem):
    out = tmp_path / f"{stem}.toml"
    rc = main(["new", "--from", stem, "--yes", "-o", str(out)])
    assert rc == 0
    data = tomllib.loads(out.read_text(encoding="utf-8"))
    assert data["device"]["name"] == stem
    assert data["style"]["scratch_pad"] == "lined"
    assert "pattern" not in data["section"]["daily_notes"]
    load(out)


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
    assert "press" in help_text
    assert "proof" in help_text
    assert "Write a profile from a shipped template." in help_text


def test_new_help_lists_device_names(capsys):
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["new", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Write a profile from a shipped template." in out
    assert "Starting profile or path (default supernote-nomad)." in out
    assert "Year. Also updates a year-only cover title." in out
    assert "Sections to keep, comma-separated." in out
    assert "SuperNote Nomad" in out
    assert "SuperNote Nomad lined" in out
    assert "Kindle Scribe" in out
    assert "Kindle Scribe lined" in out
    assert "158×210 lined" in out
    assert "left-handed" not in out
    assert "MOS-left" not in out
    assert "MOS-right" not in out
    assert "--hand" in out


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


def test_new_hand_overlays_side_menu_only(tmp_path):
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


def test_overlay_hand_rewrites_mos_side_menu():
    text = (
        "[mos] # nav\n"
        'side_menu = "left"\n'
        "reverse_months_quarters = true\n"
    )
    written = overlay_toml(text, hand="right")
    data = tomllib.loads(written)
    assert data["mos"]["side_menu"] == "right"
    assert data["mos"]["reverse_months_quarters"] is True
    assert "side_menu_width" not in data["mos"]


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


def test_overlay_indented_calendar_year_leaves_other_tables():
    text = (
        "    [calendar]\n"
        "    year = 2026\n"
        '    week_starts = "Monday"\n'
        "\n"
        "    [device]\n"
        "    year = 1999\n"
        '    name = "x"\n'
    )
    written = overlay_toml(text, year=2027)
    data = tomllib.loads(written)
    assert data["calendar"]["year"] == 2027
    assert data["device"]["year"] == 1999


def test_overlay_indented_cover_title_year():
    text = (
        "    [section.cover]\n"
        '    title = "2020"\n'
    )
    written = overlay_toml(text, year=2027)
    data = tomllib.loads(written)
    assert data["section"]["cover"]["title"] == "2027"


def test_overlay_indented_sections_replaced_in_place():
    text = (
        '    sections = ["cover", "annual"]\n'
        "\n"
        "    [device]\n"
        '    name = "x"\n'
    )
    written = overlay_toml(
        text, sections=["cover"], source_sections=["cover", "annual"]
    )
    assert written.count("sections =") == 1
    data = tomllib.loads(written)
    assert data["sections"] == ["cover"]


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


def _nomad_text() -> str:
    return NOMAD.read_text(encoding="utf-8")


def test_overlay_paper_inserts_style_and_rewrites_daily_notes_pattern():
    text = _nomad_text()
    written = overlay_toml(text, paper="lined")
    assert "SuperNote Nomad" in written
    assert written.index("[device]") < written.index("[calendar]")
    assert 'title_height = "4mm"' in written
    assert 'daily_cell_height = "16mm"' in written
    data = tomllib.loads(written)
    assert data["style"]["scratch_pad"] == "lined"
    assert data["section"]["daily_notes"]["pattern"] == "lined"
    assert data["section"]["daily"]["right"]["notes"]["pattern"] == "dotted"
    assert data["section"]["daily"]["right"]["notes"]["title_height"] == "4mm"
    assert data["mos"]["reverse_months_quarters"] is True
    assert "week_placement" not in data["section"]["monthly"]


def test_overlay_paper_rewrites_existing_style_scratch_pad():
    text = (
        "[style] # house\n"
        'scratch_pad = "dotted"\n'
        'link_padding = "2pt"\n'
        "\n"
        "[style.stroke]\n"
        'regular = "0.3pt"\n'
        "\n"
        "[section.daily_notes]\n"
        "pages = 2\n"
        'pattern = "dotted"\n'
    )
    written = overlay_toml(text, paper="lined")
    assert "# house" in written
    assert 'link_padding = "2pt"' in written
    assert written.index("# house") < written.index("scratch_pad")
    data = tomllib.loads(written)
    assert data["style"]["scratch_pad"] == "lined"
    assert data["style"]["link_padding"] == "2pt"
    assert data["section"]["daily_notes"]["pattern"] == "lined"


def test_overlay_week_placement_none_vs_omit():
    text = (
        "[section.monthly] # month\n"
        'week_label_rotation = "90deg"\n'
        'daily_cell_height = "16mm"\n'
    )
    none = overlay_toml(text, week_placement="none")
    assert "# month" in none
    assert 'week_label_rotation = "90deg"' in none
    assert 'daily_cell_height = "16mm"' in none
    data = tomllib.loads(none)
    assert data["section"]["monthly"]["week_placement"] == "none"

    omitted = overlay_toml(none, week_placement="omit")
    assert "# month" in omitted
    data = tomllib.loads(omitted)
    assert "week_placement" not in data["section"]["monthly"]
    assert data["section"]["monthly"]["daily_cell_height"] == "16mm"


def test_overlay_paper_rejects_unknown():
    with pytest.raises(ConfigError, match="paper"):
        overlay_toml(_nomad_text(), paper="mesh")


def test_overlay_week_placement_omit_on_nomad_leaves_key_out():
    written = overlay_toml(_nomad_text(), week_placement="omit")
    data = tomllib.loads(written)
    assert "week_placement" not in data["section"]["monthly"]
    assert "SuperNote Nomad" in written


def test_overlay_week_placement_rejects_left_right():
    text = (
        "[section.monthly]\n"
        'week_label_rotation = "90deg"\n'
        'daily_cell_height = "16mm"\n'
    )
    with pytest.raises(ConfigError, match="week_placement"):
        overlay_toml(text, week_placement="left")
    with pytest.raises(ConfigError, match="week_placement"):
        overlay_toml(text, week_placement="right")


def test_overlay_hours_and_counts_keep_neighbors():
    text = _nomad_text()
    written = overlay_toml(
        text,
        hour_from=7,
        hour_to=19,
        priorities_count=3,
        daily_notes_pages=4,
        projects_pages=8,
        projects_card_rows=2,
        habit_columns=6,
        meetings_index_pages=2,
    )
    assert "SuperNote Nomad (A6 X2)" in written
    assert 'time_format = "%k"' in written
    assert "trailing_half_hour = true" in written
    assert 'title_height = "4mm"' in written
    assert 'daily_cell_height = "16mm"' in written
    assert "reverse_months_quarters = true" in written
    data = tomllib.loads(written)
    schedule = data["section"]["daily"]["left"]["schedule"]
    assert schedule["hour_from"] == 7
    assert schedule["hour_to"] == 19
    assert schedule["time_format"] == "%k"
    assert data["section"]["daily"]["right"]["priorities"]["count"] == 3
    assert data["section"]["daily_notes"]["pages"] == 4
    assert data["section"]["projects"]["pages"] == 8
    assert data["section"]["projects"]["card_rows"] == 2
    assert data["section"]["habits"]["habit_columns"] == 6
    assert data["section"]["meetings"]["index_pages"] == 2
    assert data["section"]["monthly"]["daily_cell_height"] == "16mm"
    assert data["section"]["daily"]["right"]["notes"]["title_height"] == "4mm"
    assert "week_placement" not in data["section"]["monthly"]
    assert "model_dump" not in written
    assert written.count("[section.daily.left.schedule]") == 1


def test_overlay_hours_rejects_inverted_range():
    with pytest.raises(ConfigError, match="hour_from"):
        overlay_toml(_nomad_text(), hour_from=20, hour_to=8)


def test_new_yes_does_not_apply_questionary_overlays(tmp_path):
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
    assert "scratch_pad" not in data.get("style", {})
    assert data["section"]["daily"]["left"]["schedule"]["hour_from"] == 8
    assert data["section"]["daily"]["left"]["schedule"]["hour_to"] == 20
    assert data["section"]["daily"]["right"]["priorities"]["count"] == 5
    assert "week_placement" not in data["section"]["monthly"]
    assert data["mos"]["side_menu"] == "left"
    assert data["mos"]["reverse_months_quarters"] is True
    assert 'title_height = "4mm"' in text
    assert 'daily_cell_height = "16mm"' in text


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


def test_interactive_overlays_write_without_regenerating(tmp_path, monkeypatch):
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
