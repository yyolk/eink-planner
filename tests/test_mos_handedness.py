"""Left/right MOS (Months on the Side) handedness and unlocked daily columns."""

from __future__ import annotations

from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.config import load
from eink_planner.i18n import I18n
from eink_planner.kdl_config import parse_kdl
from eink_planner.mos.configurator import Configurator
from eink_planner.services.generate import Generate
from tests.test_kdl_omit_sections import _short_january, compile_pdf

REPO = Path(__file__).resolve().parents[1]
CONFIGS = REPO / "configs"
NOMAD = CONFIGS / "supernote-nomad.kdl"
LEFTIE = CONFIGS / "158x210-leftie.kdl"
RIGHTIE = CONFIGS / "158x210-rightie.kdl"


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


def _generate(dto) -> str:
    return Generate(i18n=I18n.load_default(REPO, "en")).generate(dto)


def _daily_section(dto):
    return next(s for s in dto["planner"]["sections"] if s["name"] == "daily")


def test_side_menu_right_parses():
    dto = parse_kdl(
        _minimal(
            layout="""layout "mos" {
  side-menu right 10mm
  reverse-months-quarters #true
  menu-rotate 270deg
  column-gutter 1.5mm
  row-gutter 1.5mm
}"""
        ),
        source="side-right.kdl",
    )
    mos = dto["planner"]["params"]["mos_layout"]
    assert mos["side_menu_position"] == "right"
    assert mos["side_menu_width"] == "10mm"


def test_side_menu_position_is_case_insensitive():
    dto = parse_kdl(
        _minimal(
            layout="""layout "mos" {
  side-menu RIGHT 10mm
  reverse-months-quarters #true
  menu-rotate 270deg
  column-gutter 1.5mm
  row-gutter 1.5mm
}"""
        ),
        source="side-RIGHT.kdl",
    )
    assert dto["planner"]["params"]["mos_layout"]["side_menu_position"] == "right"


def test_side_menu_rejects_non_left_right():
    with pytest.raises(ConfigError, match=r"layout\.side-menu: expected left or right"):
        parse_kdl(
            _minimal(
                layout="""layout "mos" {
  side-menu top 10mm
  reverse-months-quarters #true
  menu-rotate 270deg
  column-gutter 1.5mm
  row-gutter 1.5mm
}"""
            ),
            source="side-top.kdl",
        )


def test_daily_notes_left_schedule_right_dto_and_typst():
    text = _minimal(
        sections="""section daily {
  columns (3fr 5fr)
  item-spacing 5mm

  left {
    notes {
      pattern dotted
      title-height 5mm
    }
    little-calendar {
      week-placement right
      inset 5pt
    }
  }

  right {
    schedule 8..20 {
      time-format "%k"
    }
    top-priorities 5
  }
}
"""
    )
    dto = parse_kdl(text, source="swapped-daily.kdl")
    params = _daily_section(dto)["params"]
    assert [c["class"] for c in params["left_column"]] == ["notes", "little_calendar"]
    assert [c["class"] for c in params["right_column"]] == ["schedule", "top_priorities"]
    assert dto["planner"]["params"]["little_calendar"]["week_placement"] == "right"

    typst_src = _generate(_short_january(dto))
    marker = "columns: (3fr, 5fr)"
    body = typst_src[typst_src.index(marker) :]
    assert body.index("[Notes") < body.index("[Schedule]")
    # Daily leftover height under the last column item (little calendar / notes).
    assert "rows: (auto, 1fr)" in typst_src


def test_unknown_daily_child_still_rejected():
    with pytest.raises(ConfigError, match=r"unknown node: section\.daily\.left\.banana"):
        parse_kdl(
            _minimal(
                sections="""section daily {
  columns (3fr 5fr)
  item-spacing 5mm
  left {
    banana 1
  }
}
"""
            ),
            source="unknown-left.kdl",
        )
    with pytest.raises(ConfigError, match=r"unknown node: section\.daily\.right\.banana"):
        parse_kdl(
            _minimal(
                sections="""section daily {
  columns (3fr 5fr)
  item-spacing 5mm
  right {
    banana 1
  }
}
"""
            ),
            source="unknown-right.kdl",
        )


@pytest.mark.parametrize("path", [NOMAD, LEFTIE])
def test_existing_leftie_and_nomad_daily_still_parse(path: Path):
    dto = load(path)
    params = _daily_section(dto)["params"]
    assert [c["class"] for c in params["left_column"]] == ["schedule", "little_calendar"]
    assert [c["class"] for c in params["right_column"]] == ["top_priorities", "notes"]
    assert dto["planner"]["params"]["mos_layout"]["side_menu_position"] == "left"


def test_rightie_generate_compiles_with_mos_on_the_right(tmp_path):
    dto = _short_january(load(RIGHTIE))
    mos = dto["planner"]["params"]["mos_layout"]
    assert mos["side_menu_position"] == "right"
    assert mos["side_menu_width"] == "10mm"
    assert mos["menu_rotate"] == "270deg"
    assert mos["reverse_months_quarters_items"] is True
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")["params"]
    assert [c["class"] for c in daily["left_column"]] == ["top_priorities", "notes"]
    assert [c["class"] for c in daily["right_column"]] == ["schedule", "little_calendar"]
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert "colophon" not in names
    typst_src = _generate(dto)
    assert "columns: (1fr, 10mm)" in typst_src
    assert "columns: (10mm, 1fr)" not in typst_src
    pdf, stderr = compile_pdf(typst_src, tmp_path / "rightie")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_shipped_rightie_omits_colophon():
    dto = load(RIGHTIE)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert "colophon" not in names
    assert names == ["cover", "annual", "quarterly", "monthly", "weekly", "daily", "daily_notes"]
