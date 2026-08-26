"""Per-section scratch_pad pattern (dotted / lined)."""

from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.config import load
from eink_planner.i18n import I18n
from eink_planner.services.generate import Generate
from eink_planner.toml_config import parse_toml
from tests.toml_fixtures import _minimal, short_january

REPO = Path(__file__).resolve().parents[1]
CONFIGS = REPO / "configs"
NOMAD = CONFIGS / "supernote-nomad.toml"
NOMAD_MOS_RIGHT = CONFIGS / "supernote-nomad-mos-right.toml"
MOS_LEFT = CONFIGS / "158x210-mos-left.toml"
MOS_LEFT_LINED = CONFIGS / "158x210-mos-left-lined.toml"
MOS_RIGHT = CONFIGS / "158x210-mos-right.toml"
SCRIBE = CONFIGS / "kindle-scribe.toml"

_STYLE_LINED = """[style]
scratch_pad = "lined"

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
    notes_body = f'pattern = "{daily_pattern}"\n' if daily_pattern else ""
    notes_pages = f'pattern = "{extra_pattern}"\n' if extra_pattern else ""
    daily = f"""[section.daily]
columns = ["3fr", "5fr"]
item_spacing = "1mm"

[section.daily.left.schedule]
hour_from = 8
hour_to = 20

[section.daily.right.notes]
{notes_body}title_height = "4mm"
"""
    extra = f"""[section.daily_notes]
pages = 1
{notes_pages}"""
    names = ["daily_notes", "daily"] if reverse else ["daily", "daily_notes"]
    return _minimal(enable=names, sections="\n".join((extra, daily) if reverse else (daily, extra)))


def test_mixed_section_patterns_keep_their_values():
    dto = parse_toml(_mixed_sections("lined", "dotted"))
    assert _notes_pattern(dto) == "lined"
    assert _section(dto, "daily_notes")["params"]["pattern"] == "dotted"
    assert dto["planner"]["params"]["scratch_pad"] == "dotted"


def test_mixed_section_patterns_survive_reordering():
    dto = parse_toml(_mixed_sections("lined", "dotted", reverse=True))
    assert _notes_pattern(dto) == "lined"
    assert _section(dto, "daily_notes")["params"]["pattern"] == "dotted"
    assert dto["planner"]["params"]["scratch_pad"] == "dotted"


def test_omitted_pattern_defaults_to_dotted():
    dto = parse_toml(_mixed_sections(None, None))
    assert _notes_pattern(dto) == "dotted"
    assert _section(dto, "daily_notes")["params"]["pattern"] == "dotted"
    assert dto["planner"]["params"]["scratch_pad"] == "dotted"


def test_style_scratch_pad_is_house_default_under_explicit_section():
    text = _mixed_sections(None, "dotted")
    # rebuild with lined house style
    dto = parse_toml(_minimal(
        enable=["daily", "daily_notes"],
        style=_STYLE_LINED,
        sections="""[section.daily]
columns = ["3fr", "5fr"]
item_spacing = "1mm"

[section.daily.left.schedule]
hour_from = 8
hour_to = 20

[section.daily.right.notes]
title_height = "4mm"

[section.daily_notes]
pages = 1
pattern = "dotted"
""",
    ))
    assert dto["planner"]["params"]["scratch_pad"] == "lined"
    assert _notes_pattern(dto) == "lined"
    assert _section(dto, "daily_notes")["params"]["pattern"] == "dotted"
    assert text  # keep helper used


def test_explicit_dotted_wins_over_style_lined():
    dto = parse_toml(_minimal(
        enable=["daily", "daily_notes"],
        style=_STYLE_LINED,
        sections="""[section.daily]
columns = ["3fr", "5fr"]
item_spacing = "1mm"

[section.daily.left.schedule]
hour_from = 8
hour_to = 20

[section.daily.right.notes]
pattern = "dotted"
title_height = "4mm"

[section.daily_notes]
pages = 1
""",
    ))
    assert dto["planner"]["params"]["scratch_pad"] == "lined"
    assert _notes_pattern(dto) == "dotted"
    assert _section(dto, "daily_notes")["params"]["pattern"] == "lined"


def test_unknown_pattern_raises():
    with pytest.raises(ConfigError, match="unknown"):
        parse_toml(_mixed_sections("grid", None))
    with pytest.raises(ConfigError, match="unknown"):
        parse_toml(_minimal(
            enable=["daily", "daily_notes"],
            style=_STYLE_LINED.replace('scratch_pad = "lined"', 'scratch_pad = "mesh"'),
            sections="""[section.daily]
columns = ["3fr", "5fr"]
item_spacing = "1mm"

[section.daily.left.schedule]
hour_from = 8
hour_to = 20

[section.daily.right.notes]
title_height = "4mm"

[section.daily_notes]
pages = 1
""",
        ))
    with pytest.raises(ConfigError, match="unknown"):
        parse_toml(_minimal(
            enable=["weekly"],
            sections="""[section.weekly]
column_gutter = "4pt"
pattern = "graph"
""",
        ))


def test_mixed_profile_typst_emits_both_rect_patterns():
    dto = short_january(parse_toml(_mixed_sections("lined", "dotted")))
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
    typst = _generate(short_january(dto))
    names = [s["name"] for s in dto["planner"]["sections"]]
    if "review" in names:
        for page in typst.split("#pagebreak()"):
            if "rect_pattern(lined)" in page:
                assert "rotate(" not in page
                assert "<review-" in page
    else:
        assert "rect_pattern(lined)" not in typst
    assert "rect_pattern(dotted)" in typst
    assert "grid.cell(colspan: 3, scratch_pad)" not in typst
    assert "#let scratch_pad = rect_pattern(dotted)" in typst


def test_mos_left_lined_sibling_keeps_daily_notes_dotted():
    dto = load(MOS_LEFT_LINED)
    assert dto["planner"]["params"]["scratch_pad"] == "lined"
    assert _notes_pattern(dto) == "dotted"
    for name in ("daily_notes", "quarterly", "monthly", "weekly"):
        assert _section(dto, name)["params"]["pattern"] == "lined"
    typst = _generate(short_january(dto))
    assert "rect_pattern(dotted)" in typst
    assert "rect_pattern(lined)" in typst
    pages = typst.split("#pagebreak()")
    daily_pages = [page for page in pages if " <2026-01-01>" in page]
    extra_pages = [page for page in pages if " <daily-note-" in page]
    assert daily_pages
    assert extra_pages
    assert any("rect_pattern(dotted)" in page for page in daily_pages)
    assert any("rect_pattern(lined)" in page for page in extra_pages)
    assert all("rect_pattern(dotted)" not in page for page in extra_pages)


def test_week_month_quarter_accept_pattern_lined():
    sections = """[section.quarterly]
months_column = "left"
pattern = "lined"

[section.monthly]
week_placement = "left"
week_label_rotation = "90deg"
daily_cell_height = "16mm"
pattern = "lined"

[section.weekly]
column_gutter = "4pt"
pattern = "lined"
"""
    dto = parse_toml(_minimal(enable=["quarterly", "monthly", "weekly"], sections=sections))
    assert _section(dto, "quarterly")["params"]["pattern"] == "lined"
    assert _section(dto, "monthly")["params"]["pattern"] == "lined"
    assert "pattern" not in _section(dto, "monthly")["params"]["month_params"]
    assert _section(dto, "weekly")["params"]["pattern"] == "lined"
    typst = _generate(short_january(dto))
    pages = typst.split("#pagebreak()")
    quarter = next(page for page in pages if "Quarter 1 <quarter-2026-1>" in page)
    month = next(page for page in pages if "<month-2026-01-01>" in page)
    week = next(page for page in pages if "Week 1 <2026W01>" in page)
    assert "rect_pattern(lined)" in quarter
    assert "rect_pattern(lined)" in month
    assert "rect_pattern(lined)" in week
    assert week.count("rect_pattern(lined)") == 8
    assert "grid.cell(colspan: 3, rect_pattern" not in week
