from pathlib import Path

import pytest

from parch import ConfigError
from parch.cli import build_parser
from parch.config import load
from parch.devices import DEVICES, TOOLBAR_NONE
from parch.models.device import DEVICE_SCALE, device_page_margin, device_scale
from parch.mos.configurator import Configurator
from parch.services.job_file import DEFAULT_SECTIONS
from parch.toml_config import apply_debug, apply_hand, apply_year, load_toml, parse_toml
from tests.toml_fixtures import _minimal, omit_toml_sections
from tests.helpers import base_config, load_default

NOMAD = base_config("supernote-nomad")
NOMAD_LINED = base_config("supernote-nomad", paper="lined")
PAPER_158 = base_config("158x210")
PAPER_158_LINED = base_config("158x210", paper="lined")
SCRIBE_LINED = base_config("kindle-scribe", paper="lined")

_DEVICES = [base_config(device.id) for device in DEVICES]
_NOMAD = {NOMAD, NOMAD_LINED}
_DEFAULT_SECTIONS = list(DEFAULT_SECTIONS)
_EXTRAS = ("projects", "habits", "review", "tasks", "meetings")
_LINED = {
    PAPER_158_LINED,
    NOMAD_LINED,
    SCRIBE_LINED,
}


@pytest.mark.parametrize("path", _DEVICES)
def test_parse_device_job_defaults(path: Path):
    dto = load(path)
    assert dto["chase"] == "mos"
    assert "debug" not in dto
    cfg = Configurator(dto)
    names = [section["name"] for section in cfg.enabled_sections()]
    assert names == _DEFAULT_SECTIONS
    mos = dto["planner"]["params"]["mos_layout"]
    assert mos["reverse_months_quarters"] is True
    assert "side_menu_width" not in mos
    assert mos["side_menu_position"] in {"left", "right"}
    scale = device_scale(dto["device"])
    assert dto["document"]["layout"]["dimensions"]["width"] == scale["width"]
    assert dto["document"]["layout"]["dimensions"]["height"] == scale["height"]
    assert dto["document"]["layout"]["margin"].to_plain() == device_page_margin(scale)
    text = path.read_text(encoding="utf-8")
    assert "reverse_months_quarters = true" in text
    assert "side_menu =" in text
    assert "side_menu_width" not in text
    assert "[style.margin]" not in text
    assert "months_column" not in text
    assert "week_placement" not in text
    assert "columns = [" not in text
    assert "\nwidth = " not in text
    assert "\nheight = " not in text
    assert DEVICE_SCALE["kindle-scribe"]["mos_width"] == "10mm"
    assert DEVICE_SCALE["kindle-scribe"]["toolbar_edge"] == "none"
    assert DEVICE_SCALE["kindle-scribe"]["toolbar_clearance"] == "0mm"
    assert DEVICE_SCALE["supernote-nomad"]["mos_width"] == "8mm"
    assert DEVICE_SCALE["supernote-nomad"]["toolbar_edge"] == "top"
    assert DEVICE_SCALE["supernote-manta"]["mos_width"] == "8mm"
    assert DEVICE_SCALE["supernote-manta"]["toolbar_edge"] == "top"
    assert DEVICE_SCALE["supernote-manta"]["toolbar_clearance"] == "8mm"
    assert DEVICE_SCALE["supernote-manta"]["writing_clearance"] == "4mm"
    for device in DEVICES:
        scale = DEVICE_SCALE[device.id]
        assert scale == device.scale()
        if device.toolbar_edge == TOOLBAR_NONE:
            assert scale["toolbar_clearance"] == "0mm"
            assert scale["writing_clearance"] == "5mm"
            assert scale["mos_width"] == "10mm"


def test_load_rejects_yaml_and_kdl_device_profiles():
    with pytest.raises(ConfigError, match="TOML"):
        load("foo.yaml")
    with pytest.raises(ConfigError, match="TOML"):
        load("foo.yml")
    with pytest.raises(ConfigError, match="TOML"):
        load("foo.kdl")
    with pytest.raises(ConfigError, match="TOML"):
        load("supernote-nomad.kdl")
    with pytest.raises(ConfigError, match="TOML"):
        load("supernote-nomad.yaml")


def test_load_toml_invalid_utf8_is_config_error(tmp_path):
    path = tmp_path / "bad.toml"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(ConfigError) as exc:
        load_toml(path)
    assert str(path) in str(exc.value)


def test_commented_section_is_disabled():
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), ["cover"])
    dto = parse_toml(text, source="commented.toml")
    cfg = Configurator(dto)
    names = [section["name"] for section in cfg.enabled_sections()]
    assert "cover" not in names
    assert "annual" in names


def test_year_and_week_starts_mapping():
    dto = load(NOMAD)
    params = dto["planner"]["params"]
    assert params["start_date"] == "2026-01-01"
    assert params["end_date"] == "2026-12-31"
    assert params["weekday_start"] == "Monday"
    cfg = Configurator(dto)
    assert cfg.weekday_start() == "monday"
    assert cfg.start_date().day.isoformat() == "2026-01-01"
    assert cfg.end_date().day.isoformat() == "2026-12-31"


def test_mos_left_daily_columns():
    dto = load(PAPER_158)
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")
    params = daily["params"]
    assert "columns_width" not in params
    assert [c["class"] for c in params["left_column"]] == ["schedule", "little_calendar"]
    assert [c["class"] for c in params["right_column"]] == ["priorities", "notes"]
    schedule = params["left_column"][0]["params"]
    assert schedule["from"] == 8
    assert schedule["to"] == 20
    assert schedule["time_format"] == "%k"
    assert schedule["trailing_30_minutes"] is True
    notes = params["right_column"][1]["params"]
    assert notes["title_height"] == "5mm"
    assert notes["notes_height"] == "1fr"


def test_apply_hand_right_does_not_flip_daily_tracks():
    dto = apply_hand(load(PAPER_158), "right")
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")
    params = daily["params"]
    assert dto["planner"]["params"]["mos_layout"]["side_menu_position"] == "right"
    assert "columns_width" not in params
    assert [c["class"] for c in params["left_column"]] == ["schedule", "little_calendar"]
    assert [c["class"] for c in params["right_column"]] == ["priorities", "notes"]
    schedule = params["left_column"][0]["params"]
    assert schedule["from"] == 8
    assert schedule["to"] == 20


@pytest.mark.parametrize("path", sorted(_NOMAD, key=lambda p: p.name))
def test_nomad_defaults_omit_extras(path: Path):
    dto = load(path)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names == _DEFAULT_SECTIONS
    for extra in _EXTRAS:
        assert extra not in names
        assert f"[section.{extra}]" not in path.read_text(encoding="utf-8")


def test_nomad_projects_pages_and_card_rows_when_selected():
    path = base_config("supernote-nomad", extras=True)
    dto = load(path)
    projects = next(s for s in dto["planner"]["sections"] if s["name"] == "projects")
    assert projects["params"]["pages"] == 16
    assert projects["params"]["card_rows"] == 5
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names.index("projects") == names.index("daily_notes") + 1
    assert names.index("habits") == names.index("projects") + 1
    for extra in _EXTRAS:
        assert extra in names
        assert f"[section.{extra}]" in path.read_text(encoding="utf-8")


def _daily_notes_params(dto):
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")
    for col in ("left_column", "right_column"):
        for comp in daily["params"].get(col) or []:
            if comp["class"] == "notes":
                return comp["params"]
    raise AssertionError("daily notes component missing")


@pytest.mark.parametrize("path", sorted(_LINED, key=lambda p: p.name))
def test_lined_scratch_pad(path: Path):
    dto = load(path)
    assert dto["planner"]["params"]["scratch_pad"] == "lined"
    assert _daily_notes_params(dto)["pattern"] == "dotted"
    extra = next(s for s in dto["planner"]["sections"] if s["name"] == "daily_notes")
    assert extra["params"]["pattern"] == "lined"


def test_unknown_key_raises():
    with pytest.raises(ConfigError, match="unknown key"):
        parse_toml("foo = 1\n" + _minimal())


def test_leftover_layout_table_is_unknown_key():
    leftover = """[layout]
name = "mos"
side_menu = "left"
reverse_months_quarters = true
menu_rotate = "270deg"
column_gutter = "1.5mm"
row_gutter = "1.5mm"
"""
    with pytest.raises(ConfigError, match="unknown key: layout"):
        parse_toml(_minimal() + leftover)
    with pytest.raises(ConfigError, match="unknown key: layout"):
        parse_toml(_minimal(mos=leftover))


def test_style_gutter_row_is_optional_and_ignored():
    style = """[style.stroke]
regular = "0.3pt"
thick = "0.6pt"

[style.type]
body = "8pt"
h1 = "8mm"


[style.gutter]
column = "8pt"
row = "9mm"
"""
    dto = parse_toml(_minimal(style=style))
    assert dto["planner"]["params"]["regular_column_gutter"] == "8pt"
    # style.gutter.row is accepted on the model and ignored by the adapter
    assert dto["planner"]["params"]["mos_layout"]["row_gutter"] == "1.5mm"


def test_unknown_section_raises():
    with pytest.raises(ConfigError, match="unknown section"):
        parse_toml(_minimal(enable=["mystery"], sections=""))


@pytest.mark.parametrize("kind", ["quarterly", "monthly", "weekly"])
def test_listed_calendar_section_without_table_raises(kind):
    with pytest.raises(ConfigError, match=f"{kind} is listed in sections but"):
        parse_toml(_minimal(enable=[kind], sections=""))


def test_unknown_section_table_key_raises():
    with pytest.raises(ConfigError, match="unknown key: section.proejcts"):
        parse_toml(
            _minimal(
                enable=["cover", "projects"],
                sections="""[section.cover]
title = "Hi"
font_size = "12pt"

[section.proejcts]
pages = 20
""",
            )
        )


def test_dangling_known_section_table_is_ok():
    dto = parse_toml(
        _minimal(
            enable=["cover"],
            sections="""[section.cover]
title = "Hi"
font_size = "12pt"

[section.projects]
pages = 20
""",
        )
    )
    names = [s["name"] for s in dto["planner"]["sections"]]
    assert names == ["cover"]


def test_colophon_array_entry_must_be_table():
    with pytest.raises(ConfigError, match=r"section.colophon: expected a table"):
        parse_toml(
            _minimal(
                enable=["colophon"],
                sections="""[section]
colophon = ["not-a-table"]
""",
            )
        )


def test_missing_required_keys_raise():
    with pytest.raises(ConfigError, match="missing key: calendar"):
        parse_toml(_minimal(calendar=""))
    with pytest.raises(ConfigError, match="missing key: device"):
        parse_toml(_minimal(device=""))
    with pytest.raises(ConfigError, match="missing key: style"):
        parse_toml(_minimal(style=""))
    with pytest.raises(ConfigError, match="missing key: mos"):
        parse_toml(_minimal(mos=""))


def test_debug_not_required_and_rejected_in_toml():
    dto = parse_toml(_minimal())
    assert "debug" not in dto
    assert Configurator(dto).debug() is False
    with pytest.raises(ConfigError, match="debug does not belong"):
        parse_toml("debug = true\n" + _minimal())


def test_debug_cli_flag():
    parser = build_parser()
    args = parser.parse_args(["press", str(NOMAD), "--debug"])
    assert args.debug is True
    off = parser.parse_args(["press", str(NOMAD)])
    assert off.debug is False
    dto = apply_debug(load(NOMAD), debug=True)
    assert dto["debug"] is True
    assert Configurator(dto).debug() is True
    gen_parser = None
    for action in parser._actions:
        if getattr(action, "dest", None) == "command":
            gen_parser = action.choices["press"]
    assert gen_parser is not None
    assert "--debug" in gen_parser.format_help()


def _press_parser():
    parser = build_parser()
    for action in parser._actions:
        if getattr(action, "dest", None) == "command":
            return action.choices["press"]
    raise AssertionError("press subparser missing")


def test_year_cli_flag():
    parser = build_parser()
    args = parser.parse_args(["press", str(NOMAD), "--year", "2027"])
    assert args.year == 2027
    off = parser.parse_args(["press", str(NOMAD)])
    assert off.year is None
    assert "--year" in _press_parser().format_help()


def test_generate_help_has_locale_not_i18n_path():
    help_text = _press_parser().format_help()
    assert "--locale" in help_text
    assert "-l" in help_text
    assert "--i18n-path" not in help_text
    assert "i18n-path" not in help_text
    parser = build_parser()
    args = parser.parse_args(["press", str(NOMAD), "--locale", "en"])
    assert args.locale == "en"
    assert not hasattr(args, "i18n_path")


def test_year_cli_rejects_non_ints():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["press", str(NOMAD), "--year", "true"])
    with pytest.raises(SystemExit):
        parser.parse_args(["press", str(NOMAD), "--year", "nope"])


def test_hand_cli_flag():
    parser = build_parser()
    args = parser.parse_args(["press", str(NOMAD), "--hand", "right"])
    assert args.hand == "right"
    off = parser.parse_args(["press", str(NOMAD)])
    assert off.hand is None
    assert "--hand" in _press_parser().format_help()
    proof = parser.parse_args(["proof", "158x210", "--pages", "1", "--hand", "left"])
    assert proof.hand == "left"
    new = parser.parse_args(["new", "--device", "supernote-nomad", "--hand", "right", "--yes", "-o", "x.toml"])
    assert new.hand == "right"


def test_hand_cli_rejects_unknown():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["press", str(NOMAD), "--hand", "both"])


def test_apply_hand_overlays_side_menu_only():
    dto = apply_hand(load(PAPER_158), "right")
    mos = dto["planner"]["params"]["mos_layout"]
    assert mos["side_menu_position"] == "right"
    assert mos["reverse_months_quarters"] is True
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")["params"]
    assert "columns_width" not in daily
    quarterly = next(s for s in dto["planner"]["sections"] if s["name"] == "quarterly")["params"]
    assert "months_column" not in quarterly
    monthly = next(s for s in dto["planner"]["sections"] if s["name"] == "monthly")["params"]["month_params"]
    assert "week_placement" not in monthly


def test_apply_hand_none_leaves_profile_side():
    dto = apply_hand(load(PAPER_158), None)
    assert dto["planner"]["params"]["mos_layout"]["side_menu_position"] == "left"


def test_apply_hand_rejects_unknown():
    with pytest.raises(ConfigError, match="expected left or right"):
        apply_hand(load(NOMAD), "top")
    with pytest.raises(ConfigError, match="expected left or right"):
        apply_hand(load(NOMAD), True)


def test_apply_year_overlays_start_and_end_dates():
    dto = apply_year(load(NOMAD), 2027)
    params = dto["planner"]["params"]
    assert params["start_date"] == "2027-01-01"
    assert params["end_date"] == "2027-12-31"
    leap = apply_year(load(NOMAD), 2028)
    assert leap["planner"]["params"]["start_date"] == "2028-01-01"
    assert leap["planner"]["params"]["end_date"] == "2028-12-31"


def test_apply_year_none_leaves_file_year():
    dto = apply_year(load(NOMAD), None)
    params = dto["planner"]["params"]
    assert params["start_date"] == "2026-01-01"
    assert params["end_date"] == "2026-12-31"


def test_apply_year_rejects_bools_and_non_ints():
    with pytest.raises(ConfigError, match="expected integer"):
        apply_year(load(NOMAD), True)
    with pytest.raises(ConfigError, match="expected integer"):
        apply_year(load(NOMAD), "nope")


def test_apply_year_rejects_out_of_range():
    dto = load(NOMAD)
    with pytest.raises(ConfigError, match="out of range"):
        apply_year(dto, 0)
    with pytest.raises(ConfigError, match="out of range"):
        apply_year(dto, 10000)
    ok = apply_year(dto, 2027)
    assert ok["planner"]["params"]["start_date"] == "2027-01-01"
    assert ok["planner"]["params"]["end_date"] == "2027-12-31"


def test_apply_year_rewrites_cover_title_year():
    dto = apply_year(load(NOMAD), 2027)
    cover = next(s for s in dto["planner"]["sections"] if s["name"] == "cover")
    assert cover["params"]["name"] == "2027"


def test_apply_year_typst_uses_overlay_year():
    from parch.services.generate import Generate

    dto = apply_year(load(NOMAD), 2027)
    data = dto.to_plain()
    data["planner"]["params"]["end_date"] = "2027-01-07"
    typst = Generate(i18n=load_default()).generate(data)
    assert "2027-01-01" in typst
    assert "<2026-01-01>" not in typst
    assert "2027" in typst


def test_bool_values_are_not_integers():
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(_minimal(enable=["daily_notes"], sections="[section.daily_notes]\npages = true\n"))
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(
                enable=["daily"],
                sections="""[section.daily]
item_spacing = "1mm"

[section.daily.left.schedule]
hour_from = true
hour_to = false

[section.daily.right.priorities]
count = 1
""",
            )
        )


def test_string_field_rejects_integer():
    with pytest.raises(ConfigError, match="expected string"):
        parse_toml(_minimal(calendar="""[calendar]
year = 2026
week_starts = 1
"""))


def test_hour_range_rejects_float_args():
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(
                enable=["daily"],
                sections="""[section.daily]
item_spacing = "1mm"

[section.daily.left.schedule]
hour_from = 8.5
hour_to = 20

[section.daily.right.priorities]
count = 1
""",
            )
        )


def _daily_little_calendar(dto):
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")
    for col in ("left_column", "right_column"):
        for comp in daily["params"].get(col) or []:
            if comp["class"] == "little_calendar":
                return comp["params"]
    raise AssertionError("daily little calendar component missing")


def test_daily_little_calendar_inherits_style_inset():
    style = """[style.stroke]
regular = "0.3pt"
thick = "0.6pt"

[style.type]
body = "8pt"
h1 = "8mm"


[style.gutter]
column = "8pt"

[style.little_calendar]
inset = "3pt"
"""
    sections = """[section.daily]
item_spacing = "1mm"

[section.daily.left.little_calendar]
show_month_name = true

[section.daily.right.priorities]
count = 1
"""
    dto = parse_toml(_minimal(enable=["daily"], style=style, sections=sections))
    params = _daily_little_calendar(dto)
    assert "week_placement" not in params
    assert params["inset"] == "3pt"
    assert params["show_month_name"] is True


def test_daily_little_calendar_section_wins_over_style():
    style = """[style.stroke]
regular = "0.3pt"
thick = "0.6pt"

[style.type]
body = "8pt"
h1 = "8mm"


[style.gutter]
column = "8pt"

[style.little_calendar]
inset = "3pt"
"""
    sections = """[section.daily]
item_spacing = "1mm"

[section.daily.left.little_calendar]
inset = "5pt"

[section.daily.right.priorities]
count = 1
"""
    dto = parse_toml(_minimal(enable=["daily"], style=style, sections=sections))
    params = _daily_little_calendar(dto)
    assert params["inset"] == "5pt"
    assert dto["planner"]["params"]["little_calendar"]["inset"] == "5pt"


def test_device_ppi_may_be_omitted():
    dto = parse_toml(
        _minimal(
            device="""[device]
name = "158x210"
""",
        )
    )
    assert dto["device"] == "158x210"
    assert dto["document"]["layout"]["dimensions"]["width"] == "158mm"
    assert dto["document"]["layout"]["dimensions"]["height"] == "210mm"
    assert dto["document"]["layout"]["margin"]["top"] == "0mm"
    assert dto["document"]["layout"]["margin"]["right"] == "5mm"


def test_dead_toml_keys_are_unknown():
    with pytest.raises(ConfigError, match="unknown key"):
        parse_toml(_minimal() + "\n[style.margin]\ntop = \"5mm\"\n")
    with pytest.raises(ConfigError, match="unknown key"):
        parse_toml(
            _minimal(
                device="""[device]
name = "158x210"
width = "158mm"
height = "210mm"
"""
            )
        )
    with pytest.raises(ConfigError, match="unknown key"):
        parse_toml(
            _minimal(
                enable=["quarterly"],
                sections="""[section.quarterly]
months_column = "left"
show_month_name = true
""",
            )
        )
    with pytest.raises(ConfigError, match="unknown key"):
        parse_toml(
            _minimal(
                enable=["daily"],
                sections="""[section.daily]
columns = ["3fr", "5fr"]
item_spacing = "1mm"

[section.daily.left.schedule]
hour_from = 8
hour_to = 20

[section.daily.right.priorities]
count = 1
""",
            )
        )
    with pytest.raises(ConfigError, match="unknown key: mos.side_menu_width"):
        parse_toml(
            _minimal(
                mos="""[mos]
side_menu = "left"
side_menu_width = "8mm"
reverse_months_quarters = true
menu_rotate = "270deg"
column_gutter = "1.5mm"
row_gutter = "1.5mm"
"""
            )
        )


def test_week_placement_left_right_rejected_none_ok():
    with pytest.raises(ConfigError, match="week_placement"):
        parse_toml(
            _minimal(
                enable=["monthly"],
                sections="""[section.monthly]
week_placement = "left"
week_label_rotation = "90deg"
daily_cell_height = "2.5cm"
""",
            )
        )
    dto = parse_toml(
        _minimal(
            enable=["monthly"],
            sections="""[section.monthly]
week_placement = "none"
week_label_rotation = "90deg"
daily_cell_height = "2.5cm"
""",
        )
    )
    monthly = next(s for s in dto["planner"]["sections"] if s["name"] == "monthly")
    assert monthly["params"]["month_params"]["week_placement"] == "none"


def test_empty_style_scratch_pad_is_dotted():
    style = """[style]
scratch_pad = ""

[style.stroke]
regular = "0.3pt"
thick = "0.6pt"

[style.type]
body = "8pt"
h1 = "8mm"


[style.gutter]
column = "8pt"
"""
    dto = parse_toml(_minimal(style=style))
    assert dto["planner"]["params"]["scratch_pad"] == "dotted"
