from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.cli import build_parser
from eink_planner.config import load, load_yaml
from eink_planner.kdl_config import apply_debug, parse_kdl
from eink_planner.mos.configurator import Configurator

REPO = Path(__file__).resolve().parents[1]
CONFIGS = REPO / "configs"

NOMAD = CONFIGS / "supernote-nomad.kdl"
LEFTIE = CONFIGS / "158x210-leftie.kdl"
SCRIBE = CONFIGS / "kindle-scribe.kdl"


def _minimal(**extra: str) -> str:
    parts = {
        "device": """device "x" {
  page-size 100mm 120mm
  ppi 300
}""",
        "year": "year 2026",
        "week": "week-starts Monday",
        "style": """style {
  stroke {
    regular 0.3pt
    thick 0.6pt
  }
  type {
    body 8pt
    h1 8mm
  }
  margin {
    top 8mm
    bottom 0mm
    left 0mm
    right 4mm
  }
  gutter {
    column 8pt
    row 1.5mm
  }
}""",
        "layout": """layout "mos" {
  side-menu left 8mm
  reverse-months-quarters #true
  menu-rotate 270deg
  column-gutter 1.5mm
  row-gutter 1.5mm
}""",
        "sections": """section cover {
  title "Hi"
  font-size 12pt
}""",
    }
    parts.update(extra)
    return "\n\n".join(parts.values()) + "\n"


@pytest.mark.parametrize("path", [NOMAD, LEFTIE, SCRIBE])
def test_parse_shipped_kdl_profiles(path: Path):
    dto = load(path)
    assert dto["template"] == "mos"
    assert "debug" not in dto
    cfg = Configurator(dto)
    names = [section["name"] if not hasattr(section, "to_plain") else section["name"] for section in cfg.enabled_sections()]
    assert names == ["cover", "annual", "quarterly", "monthly", "weekly", "daily", "daily_notes"]


def test_kdl_matches_yaml_for_nomad_and_scribe():
    for yaml_name, kdl_name in (
        ("supernote-nomad.yaml", "supernote-nomad.kdl"),
        ("kindle-scribe.yaml", "kindle-scribe.kdl"),
    ):
        yaml_dto = load_yaml(CONFIGS / yaml_name).to_plain()
        kdl_dto = load(CONFIGS / kdl_name).to_plain()
        yaml_dto.pop("version", None)
        yaml_dto.pop("debug", None)
        assert kdl_dto == yaml_dto


def test_commented_section_is_disabled():
    text = NOMAD.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    out = []
    commenting = False
    depth = 0
    for line in lines:
        if not commenting and line.startswith("section cover"):
            commenting = True
        if commenting:
            out.append("// " + line if not line.startswith("//") else line)
            depth += line.count("{") - line.count("}")
            if depth <= 0:
                commenting = False
            continue
        out.append(line)
    dto = parse_kdl("".join(out), source="commented.kdl")
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


def test_daily_left_right_columns():
    dto = load(NOMAD)
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
    assert notes["title_height"] == "4mm"
    assert notes["notes_height"] == "1fr"


def test_unknown_node_raises():
    with pytest.raises(ConfigError, match="unknown node"):
        parse_kdl(_minimal() + "\nfoo 1\n")


def test_unknown_section_raises():
    with pytest.raises(ConfigError, match="unknown section"):
        parse_kdl(_minimal(sections='section mystery {\n  pages 1\n}\n'))


def test_missing_required_nodes_raise():
    with pytest.raises(ConfigError, match="missing node: year"):
        parse_kdl(_minimal(year=""))
    with pytest.raises(ConfigError, match="missing node: device"):
        parse_kdl(_minimal(device=""))
    with pytest.raises(ConfigError, match="missing node: style"):
        parse_kdl(_minimal(style=""))
    with pytest.raises(ConfigError, match="missing node: layout"):
        parse_kdl(_minimal(layout=""))


def test_debug_not_required_and_rejected_in_kdl():
    dto = parse_kdl(_minimal())
    assert "debug" not in dto
    assert Configurator(dto).debug() is False
    with pytest.raises(ConfigError, match="debug does not belong"):
        parse_kdl(_minimal() + "\ndebug #true\n")


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


def test_bool_args_are_not_integers():
    with pytest.raises(ConfigError, match="expected integer"):
        parse_kdl(_minimal(sections="""section daily-notes {
  pages #true
}
"""))
    with pytest.raises(ConfigError, match="expected hour range"):
        parse_kdl(_minimal(sections="""section daily {
  item-spacing 1mm
  columns 3fr 5fr
  left {
    schedule #true #false
  }
}
"""))

