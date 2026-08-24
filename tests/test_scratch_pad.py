"""Per-section scratch-pad pattern (dotted / lined)."""

from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.config import load
from eink_planner.i18n import I18n
from eink_planner.kdl_config import parse_kdl
from eink_planner.services.generate import Generate
from tests.test_kdl_config import _minimal
from tests.test_kdl_omit_sections import _short_january

REPO = Path(__file__).resolve().parents[1]
CONFIGS = REPO / "configs"
NOMAD = CONFIGS / "supernote-nomad.kdl"
NOMAD_MOS_RIGHT = CONFIGS / "supernote-nomad-mos-right.kdl"
MOS_LEFT = CONFIGS / "158x210-mos-left.kdl"
MOS_RIGHT = CONFIGS / "158x210-mos-right.kdl"
SCRIBE = CONFIGS / "kindle-scribe.kdl"

_STYLE_LINED = """style {
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
  scratch-pad lined
}"""

def _generate(dto) -> str:
    return Generate(i18n=I18n.load_default(REPO, "en")).generate(dto)


def _section(dto, name: str):
    return next(s for s in dto["planner"]["sections"] if s["name"] == name)


def _notes_pattern(dto) -> str:
    daily = _section(dto, "daily")
    for col in ("left_column", "right_column"):
        for comp in daily["params"].get(col) or []:
            if comp["class"] == "notes":
                return comp["params"]["pattern"]
    raise AssertionError("daily notes component missing")


def _mixed_sections(daily_pattern: str | None, extra_pattern: str | None, reverse: bool = False) -> str:
    notes_body = f"pattern {daily_pattern}" if daily_pattern else ""
    notes_pages = f"pattern {extra_pattern}" if extra_pattern else ""
    daily = f"""section daily {{
  columns 3fr 5fr
  item-spacing 1mm
  right {{
    notes {{
      {notes_body}
      title-height 4mm
    }}
  }}
}}"""
    extra = f"""section daily-notes {{
  pages 1
  {notes_pages}
}}"""
    return "\n\n".join((extra, daily) if reverse else (daily, extra))


def test_mixed_section_patterns_keep_their_values():
    dto = parse_kdl(_minimal(sections=_mixed_sections("lined", "dotted")))
    assert _notes_pattern(dto) == "lined"
    assert _section(dto, "daily_notes")["params"]["pattern"] == "dotted"
    assert dto["planner"]["params"]["scratch_pad"] == "dotted"


def test_mixed_section_patterns_survive_reordering():
    dto = parse_kdl(_minimal(sections=_mixed_sections("lined", "dotted", reverse=True)))
    assert _notes_pattern(dto) == "lined"
    assert _section(dto, "daily_notes")["params"]["pattern"] == "dotted"
    assert dto["planner"]["params"]["scratch_pad"] == "dotted"


def test_omitted_pattern_defaults_to_dotted():
    dto = parse_kdl(_minimal(sections=_mixed_sections(None, None)))
    assert _notes_pattern(dto) == "dotted"
    assert _section(dto, "daily_notes")["params"]["pattern"] == "dotted"
    assert dto["planner"]["params"]["scratch_pad"] == "dotted"


def test_style_scratch_pad_is_house_default_under_explicit_section():
    sections = _mixed_sections(None, "dotted")
    dto = parse_kdl(_minimal(style=_STYLE_LINED, sections=sections))
    assert dto["planner"]["params"]["scratch_pad"] == "lined"
    assert _notes_pattern(dto) == "lined"
    assert _section(dto, "daily_notes")["params"]["pattern"] == "dotted"


def test_explicit_dotted_wins_over_style_lined():
    sections = _mixed_sections("dotted", None)
    dto = parse_kdl(_minimal(style=_STYLE_LINED, sections=sections))
    assert dto["planner"]["params"]["scratch_pad"] == "lined"
    assert _notes_pattern(dto) == "dotted"
    assert _section(dto, "daily_notes")["params"]["pattern"] == "lined"


def test_unknown_pattern_raises():
    with pytest.raises(ConfigError, match="unknown"):
        parse_kdl(_minimal(sections=_mixed_sections("grid", None)))
    with pytest.raises(ConfigError, match="unknown"):
        parse_kdl(
            _minimal(
                style=_STYLE_LINED.replace("scratch-pad lined", "scratch-pad mesh"),
                sections=_mixed_sections(None, None),
            )
        )
    with pytest.raises(ConfigError, match="unknown"):
        parse_kdl(
            _minimal(
                sections="""section weekly {
  column-gutter 4pt
  pattern graph
}
"""
            )
        )


def test_mixed_profile_typst_emits_both_rect_patterns():
    dto = _short_january(parse_kdl(_minimal(sections=_mixed_sections("lined", "dotted"))))
    typst = _generate(dto)
    pages = typst.split("#pagebreak()")
    daily_pages = [page for page in pages if " <2026-01-01>" in page]
    extra_pages = [page for page in pages if " <daily-note-" in page]
    assert daily_pages
    assert extra_pages
    assert any("rect_pattern(lined)" in page for page in daily_pages)
    assert any("rect_pattern(dotted)" in page for page in extra_pages)
    assert all("rect_pattern(lined)" not in page for page in extra_pages)


@pytest.mark.parametrize("path", [NOMAD, NOMAD_MOS_RIGHT, MOS_LEFT, MOS_RIGHT, SCRIBE])
def test_shipped_profiles_keep_dotted_scratch_areas(path: Path):
    dto = load(path)
    assert dto["planner"]["params"]["scratch_pad"] == "dotted"
    assert _notes_pattern(dto) == "dotted"
    for name in ("daily_notes", "quarterly", "monthly", "weekly"):
        assert _section(dto, name)["params"]["pattern"] == "dotted"
    typst = _generate(_short_january(dto))
    assert "rect_pattern(lined)" not in typst
    assert "rect_pattern(dotted)" in typst
    assert "grid.cell(colspan: 3, scratch_pad)" not in typst
    assert "#let scratch_pad = rect_pattern(dotted)" in typst


def test_week_month_quarter_accept_pattern_lined():
    sections = """section quarterly {
  months-column left
  pattern lined
}

section monthly {
  week-placement left
  week-label-rotation 90deg
  daily-cell-height 16mm
  pattern lined
}

section weekly {
  column-gutter 4pt
  pattern lined
}
"""
    dto = parse_kdl(_minimal(sections=sections))
    assert _section(dto, "quarterly")["params"]["pattern"] == "lined"
    assert _section(dto, "monthly")["params"]["pattern"] == "lined"
    assert "pattern" not in _section(dto, "monthly")["params"]["month_params"]
    assert _section(dto, "weekly")["params"]["pattern"] == "lined"
    typst = _generate(_short_january(dto))
    pages = typst.split("#pagebreak()")
    quarter = next(page for page in pages if "Quarter 1 <quarter-2026-1>" in page)
    month = next(page for page in pages if "<month-2026-01-01>" in page)
    week = next(page for page in pages if "Week 1 <2026W01>" in page)
    assert "rect_pattern(lined)" in quarter
    assert "rect_pattern(lined)" in month
    assert "rect_pattern(lined)" in week
    assert week.count("rect_pattern(lined)") == 3
