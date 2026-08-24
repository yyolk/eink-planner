from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.cli import build_parser
from eink_planner.config import load
from eink_planner.kdl_config import apply_debug, apply_year, parse_kdl
from eink_planner.mos.configurator import Configurator

REPO = Path(__file__).resolve().parents[1]
CONFIGS = REPO / "configs"

NOMAD = CONFIGS / "supernote-nomad.kdl"
NOMAD_MOS_RIGHT = CONFIGS / "supernote-nomad-mos-right.kdl"
MOS_LEFT = CONFIGS / "158x210-mos-left.kdl"
MOS_LEFT_LINED = CONFIGS / "158x210-mos-left-lined.kdl"
MOS_RIGHT = CONFIGS / "158x210-mos-right.kdl"
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


@pytest.mark.parametrize("path", [NOMAD, NOMAD_MOS_RIGHT, MOS_LEFT, MOS_LEFT_LINED, MOS_RIGHT, SCRIBE])
def test_parse_shipped_kdl_profiles(path: Path):
    dto = load(path)
    assert dto["template"] == "mos"
    assert "debug" not in dto
    cfg = Configurator(dto)
    names = [section["name"] if not hasattr(section, "to_plain") else section["name"] for section in cfg.enabled_sections()]
    assert names == ["cover", "annual", "quarterly", "monthly", "weekly", "daily", "daily_notes"]


def test_load_rejects_yaml_device_profiles():
    with pytest.raises(ConfigError, match="KDL"):
        load("foo.yaml")
    with pytest.raises(ConfigError, match="KDL"):
        load("foo.yml")
    with pytest.raises(ConfigError, match="KDL"):
        load(CONFIGS / "supernote-nomad.yaml")


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


def test_style_gutter_row_is_unknown():
    text = _minimal().replace(
        "gutter {\n    column 8pt\n  }",
        "gutter {\n    column 8pt\n    row 1.5mm\n  }",
    )
    with pytest.raises(ConfigError, match="unknown node: style.gutter.row"):
        parse_kdl(text)


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


def test_hour_range_rejects_float_args():
    with pytest.raises(ConfigError, match="expected hour range"):
        parse_kdl(_minimal(sections="""section daily {
  item-spacing 1mm
  columns 3fr 5fr
  left {
    schedule 8.5 20
  }
}
"""))


def test_arg0_requires_exactly_one_argument():
    with pytest.raises(ConfigError, match="expected one argument"):
        parse_kdl(_minimal(sections="""section cover {
  title "A" "B"
  font-size 12pt
}
"""))
    with pytest.raises(ConfigError, match="expected one argument"):
        parse_kdl(_minimal(sections="""section cover {
  title "Hi"
  font-size 12pt 99pt
}
"""))


def test_section_requires_exactly_one_argument():
    with pytest.raises(ConfigError, match="expected one type argument"):
        parse_kdl(_minimal(sections="""section daily extra {
  item-spacing 1mm
  columns 3fr 5fr
}
"""))


def _daily_little_calendar(dto):
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")
    for col in ("left_column", "right_column"):
        for comp in daily["params"].get(col) or []:
            if comp["class"] == "little_calendar":
                return comp["params"]
    raise AssertionError("daily little calendar component missing")


def test_daily_little_calendar_inherits_style_week_placement_and_inset():
    style = """style {
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
  }
  little-calendar {
    week-placement left
    inset 3pt
  }
}"""
    sections = """section daily {
  columns 3fr 5fr
  item-spacing 1mm
  left {
    little-calendar {
      show-month-name #true
    }
  }
}
"""
    dto = parse_kdl(_minimal(style=style, sections=sections))
    params = _daily_little_calendar(dto)
    assert params["week_placement"] == "left"
    assert params["inset"] == "3pt"
    assert params["show_month_name"] is True


def test_daily_little_calendar_section_wins_over_style():
    style = """style {
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
  }
  little-calendar {
    inset 3pt
  }
}"""
    sections = """section daily {
  columns 3fr 5fr
  item-spacing 1mm
  left {
    little-calendar {
      inset 5pt
    }
  }
}
"""
    dto = parse_kdl(_minimal(style=style, sections=sections))
    params = _daily_little_calendar(dto)
    assert params["inset"] == "5pt"
    assert dto["planner"]["params"]["little_calendar"]["inset"] == "5pt"
