from pathlib import Path

import hashlib
import pytest

from eink_planner import ConfigError
from eink_planner.cli import build_parser
from eink_planner.config import load
from eink_planner.mos.configurator import Configurator
from eink_planner.toml_config import apply_debug, apply_year, load_toml, parse_toml
from tests.toml_fixtures import _minimal, omit_toml_sections

REPO = Path(__file__).resolve().parents[1]
CONFIGS = REPO / "configs"

NOMAD = CONFIGS / "supernote-nomad.toml"
NOMAD_MOS_RIGHT = CONFIGS / "supernote-nomad-mos-right.toml"
MOS_LEFT = CONFIGS / "158x210-mos-left.toml"
MOS_LEFT_LINED = CONFIGS / "158x210-mos-left-lined.toml"
MOS_RIGHT = CONFIGS / "158x210-mos-right.toml"
SCRIBE = CONFIGS / "kindle-scribe.toml"

GOLDEN_SHA256 = {
    "supernote-nomad": "90dd194483872ef8c52879e57dfafe88ff3c66a0e06c0a2cf949cf240ebd3454",
    "158x210-mos-left": "43f733d39303de4d1e732a135c278f50b922d427b28fe4ec131bbf5c08449cbf",
}


@pytest.mark.parametrize("path", [NOMAD, NOMAD_MOS_RIGHT, MOS_LEFT, MOS_LEFT_LINED, MOS_RIGHT, SCRIBE])
def test_parse_shipped_toml_profiles(path: Path):
    dto = load(path)
    assert dto["template"] == "mos"
    assert "debug" not in dto
    cfg = Configurator(dto)
    names = [section["name"] for section in cfg.enabled_sections()]
    expected = ["cover", "annual", "quarterly", "monthly", "weekly", "daily", "daily_notes"]
    if path == NOMAD:
        expected = expected + ["projects"]
    if path in {NOMAD, NOMAD_MOS_RIGHT}:
        expected = expected + ["habits", "review"]
    assert names == expected


def test_load_rejects_yaml_and_kdl_device_profiles():
    with pytest.raises(ConfigError, match="TOML"):
        load("foo.yaml")
    with pytest.raises(ConfigError, match="TOML"):
        load("foo.yml")
    with pytest.raises(ConfigError, match="TOML"):
        load("foo.kdl")
    with pytest.raises(ConfigError, match="TOML"):
        load(CONFIGS / "supernote-nomad.kdl")
    with pytest.raises(ConfigError, match="TOML"):
        load(CONFIGS / "supernote-nomad.yaml")


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
    dto = load(MOS_LEFT)
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")
    params = daily["params"]
    assert params["columns_width"] == "(3fr, 5fr)"
    assert [c["class"] for c in params["left_column"]] == ["schedule", "little_calendar"]
    assert [c["class"] for c in params["right_column"]] == ["top_priorities", "notes"]
    schedule = params["left_column"][0]["params"]
    assert schedule["from"] == 8
    assert schedule["to"] == 20
    assert schedule["time_format"] == "%k"
    assert schedule["trailing_30_minutes"] is True
    notes = params["right_column"][1]["params"]
    assert notes["title_height"] == "5mm"
    assert notes["notes_height"] == "1fr"


def test_mos_right_daily_track_flip():
    dto = load(MOS_RIGHT)
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")
    params = daily["params"]
    assert params["columns_width"] == "(5fr, 3fr)"
    assert [c["class"] for c in params["left_column"]] == ["top_priorities", "notes"]
    assert [c["class"] for c in params["right_column"]] == ["schedule", "little_calendar"]
    assert params["left_column"][0]["params"]["number"] == 5
    schedule = params["right_column"][0]["params"]
    assert schedule["from"] == 8
    assert schedule["to"] == 20


def test_nomad_projects_pages_and_card_rows():
    dto = load(NOMAD)
    projects = next(s for s in dto["planner"]["sections"] if s["name"] == "projects")
    assert projects["params"]["pages"] == 16
    assert projects["params"]["card_rows"] == 5
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert "projects" in names
    assert names[-1] == "review"
    assert names[-2] == "habits"


def test_lined_scratch_pad():
    dto = load(MOS_LEFT_LINED)
    assert dto["planner"]["params"]["scratch_pad"] == "lined"
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")
    notes = next(c for c in daily["params"]["right_column"] if c["class"] == "notes")
    assert notes["params"]["pattern"] == "dotted"
    extra = next(s for s in dto["planner"]["sections"] if s["name"] == "daily_notes")
    assert extra["params"]["pattern"] == "lined"


def test_unknown_key_raises():
    with pytest.raises(ConfigError, match="unknown key"):
        parse_toml("foo = 1\n" + _minimal())


def test_style_gutter_row_is_optional_and_ignored():
    style = """[style.stroke]
regular = "0.3pt"
thick = "0.6pt"

[style.type]
body = "8pt"
h1 = "8mm"

[style.margin]
top = "8mm"
bottom = "0mm"
left = "0mm"
right = "4mm"

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
    with pytest.raises(ConfigError, match="section.colophon: expected a table"):
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
    with pytest.raises(ConfigError, match="missing key: layout"):
        parse_toml(_minimal(layout=""))


def test_debug_not_required_and_rejected_in_toml():
    dto = parse_toml(_minimal())
    assert "debug" not in dto
    assert Configurator(dto).debug() is False
    with pytest.raises(ConfigError, match="debug does not belong"):
        parse_toml("debug = true\n" + _minimal())


def test_debug_cli_flag():
    parser = build_parser()
    args = parser.parse_args(["generate", str(NOMAD), "--debug"])
    assert args.debug is True
    off = parser.parse_args(["generate", str(NOMAD)])
    assert off.debug is False
    dto = apply_debug(load(NOMAD), debug=True)
    assert dto["debug"] is True
    assert Configurator(dto).debug() is True
    gen_parser = None
    for action in parser._actions:
        if getattr(action, "dest", None) == "command":
            gen_parser = action.choices["generate"]
    assert gen_parser is not None
    assert "--debug" in gen_parser.format_help()


def _generate_parser():
    parser = build_parser()
    for action in parser._actions:
        if getattr(action, "dest", None) == "command":
            return action.choices["generate"]
    raise AssertionError("generate subparser missing")


def test_year_cli_flag():
    parser = build_parser()
    args = parser.parse_args(["generate", str(NOMAD), "--year", "2027"])
    assert args.year == 2027
    off = parser.parse_args(["generate", str(NOMAD)])
    assert off.year is None
    assert "--year" in _generate_parser().format_help()


def test_generate_help_has_locale_not_i18n_path():
    help_text = _generate_parser().format_help()
    assert "--locale" in help_text
    assert "-l" in help_text
    assert "--i18n-path" not in help_text
    assert "i18n-path" not in help_text
    parser = build_parser()
    args = parser.parse_args(["generate", str(NOMAD), "--locale", "en"])
    assert args.locale == "en"
    assert not hasattr(args, "i18n_path")


def test_year_cli_rejects_non_ints():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["generate", str(NOMAD), "--year", "true"])
    with pytest.raises(SystemExit):
        parser.parse_args(["generate", str(NOMAD), "--year", "nope"])


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
    assert cover["params"]["name"] == "2027\n\nPlanner"


def test_apply_year_typst_uses_overlay_year():
    from eink_planner.i18n import I18n
    from eink_planner.services.generate import Generate

    dto = apply_year(load(NOMAD), 2027)
    data = dto.to_plain()
    data["planner"]["params"]["end_date"] = "2027-01-07"
    typst = Generate(i18n=I18n.load_default(REPO, "en")).generate(data)
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
columns = ["3fr", "5fr"]

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
columns = ["3fr", "5fr"]

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


def test_daily_little_calendar_inherits_style_week_placement_and_inset():
    style = """[style.stroke]
regular = "0.3pt"
thick = "0.6pt"

[style.type]
body = "8pt"
h1 = "8mm"

[style.margin]
top = "8mm"
bottom = "0mm"
left = "0mm"
right = "4mm"

[style.gutter]
column = "8pt"

[style.little_calendar]
week_placement = "left"
inset = "3pt"
"""
    sections = """[section.daily]
columns = ["3fr", "5fr"]
item_spacing = "1mm"

[section.daily.left.little_calendar]
show_month_name = true

[section.daily.right.priorities]
count = 1
"""
    dto = parse_toml(_minimal(enable=["daily"], style=style, sections=sections))
    params = _daily_little_calendar(dto)
    assert params["week_placement"] == "left"
    assert params["inset"] == "3pt"
    assert params["show_month_name"] is True


def test_daily_little_calendar_section_wins_over_style():
    style = """[style.stroke]
regular = "0.3pt"
thick = "0.6pt"

[style.type]
body = "8pt"
h1 = "8mm"

[style.margin]
top = "8mm"
bottom = "0mm"
left = "0mm"
right = "4mm"

[style.gutter]
column = "8pt"

[style.little_calendar]
inset = "3pt"
"""
    sections = """[section.daily]
columns = ["3fr", "5fr"]
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


@pytest.mark.parametrize("name", list(GOLDEN_SHA256))
def test_golden_typst_hash(name: str):
    from eink_planner.i18n import I18n
    from eink_planner.services.generate import Generate

    dto = load(CONFIGS / f"{name}.toml")
    typst = Generate(i18n=I18n.load_default(REPO, "en")).generate(dto)
    digest = hashlib.sha256(typst.encode("utf-8")).hexdigest()
    assert digest == GOLDEN_SHA256[name]
    golden = REPO / "out" / "toml-goldens" / f"{name}.typst"
    if golden.is_file():
        assert typst == golden.read_text(encoding="utf-8")


def test_device_ppi_may_be_omitted():
    dto = parse_toml(
        _minimal(
            device="""[device]
name = "x"
width = "100mm"
height = "120mm"
""",
        )
    )
    assert dto["device"] == "x"
    assert dto["document"]["layout"]["dimensions"]["width"] == "100mm"
    assert dto["document"]["layout"]["dimensions"]["height"] == "120mm"


def test_empty_style_scratch_pad_is_dotted():
    style = """[style]
scratch_pad = ""

[style.stroke]
regular = "0.3pt"
thick = "0.6pt"

[style.type]
body = "8pt"
h1 = "8mm"

[style.margin]
top = "8mm"
bottom = "0mm"
left = "0mm"
right = "4mm"

[style.gutter]
column = "8pt"
"""
    dto = parse_toml(_minimal(style=style))
    assert dto["planner"]["params"]["scratch_pad"] == "dotted"
