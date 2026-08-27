"""Left/right MOS (Months on the Side) handedness and unlocked daily columns."""

from __future__ import annotations

from pathlib import Path

import pytest

from parch import ConfigError
from parch.config import load
from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.test_toml_omit_sections import compile_pdf
from tests.toml_fixtures import _minimal, short_january

REPO = Path(__file__).resolve().parents[1]
CONFIGS = REPO / "configs"
NOMAD = CONFIGS / "supernote-nomad.toml"
NOMAD_MOS_RIGHT = CONFIGS / "supernote-nomad-mos-right.toml"
MOS_LEFT = CONFIGS / "158x210-mos-left.toml"
MOS_RIGHT = CONFIGS / "158x210-mos-right.toml"


def _generate(dto) -> str:
    return Generate(i18n=I18n.load_default(REPO, "en")).generate(dto)


def _daily_section(dto):
    return next(s for s in dto["planner"]["sections"] if s["name"] == "daily")


def test_side_menu_right_parses():
    dto = parse_toml(
        _minimal(
            layout="""[layout]
name = "mos"
side_menu = "right"
side_menu_width = "10mm"
reverse_months_quarters = true
menu_rotate = "270deg"
column_gutter = "1.5mm"
row_gutter = "1.5mm"
"""
        ),
        source="side-right.toml",
    )
    mos = dto["planner"]["params"]["mos_layout"]
    assert mos["side_menu_position"] == "right"
    assert mos["side_menu_width"] == "10mm"


def test_side_menu_position_is_case_insensitive():
    dto = parse_toml(
        _minimal(
            layout="""[layout]
name = "mos"
side_menu = "RIGHT"
side_menu_width = "10mm"
reverse_months_quarters = true
menu_rotate = "270deg"
column_gutter = "1.5mm"
row_gutter = "1.5mm"
"""
        ),
        source="side-RIGHT.toml",
    )
    assert dto["planner"]["params"]["mos_layout"]["side_menu_position"] == "right"


def test_side_menu_rejects_non_left_right():
    with pytest.raises(ConfigError, match=r"layout\.side_menu: expected left or right"):
        parse_toml(
            _minimal(
                layout="""[layout]
name = "mos"
side_menu = "top"
side_menu_width = "10mm"
reverse_months_quarters = true
menu_rotate = "270deg"
column_gutter = "1.5mm"
row_gutter = "1.5mm"
"""
            ),
            source="side-top.toml",
        )


def test_daily_notes_left_schedule_right_dto_and_typst():
    text = _minimal(
        enable=["daily"],
        sections="""[section.daily]
columns = ["3fr", "5fr"]
item_spacing = "5mm"

[section.daily.left.notes]
pattern = "dotted"
title_height = "5mm"

[section.daily.left.little_calendar]
week_placement = "right"
inset = "5pt"

[section.daily.right.schedule]
hour_from = 8
hour_to = 20
time_format = "%k"

[section.daily.right.priorities]
count = 5
""",
    )
    dto = parse_toml(text, source="swapped-daily.toml")
    params = _daily_section(dto)["params"]
    assert [c["class"] for c in params["left_column"]] == ["notes", "little_calendar"]
    assert [c["class"] for c in params["right_column"]] == ["schedule", "priorities"]
    assert dto["planner"]["params"]["little_calendar"]["week_placement"] == "right"

    typst_src = _generate(short_january(dto))
    marker = "columns: (3fr, 5fr)"
    body = typst_src[typst_src.index(marker) :]
    assert body.index("[Notes") < body.index("[Schedule]")
    assert "rows: (auto, 1fr)" in typst_src


def test_unknown_daily_child_still_rejected():
    with pytest.raises(ConfigError, match=r"unknown key: section\.daily\.left\.banana"):
        parse_toml(
            _minimal(
                enable=["daily"],
                sections="""[section.daily]
columns = ["3fr", "5fr"]
item_spacing = "5mm"

[section.daily.right.priorities]
count = 1

[section.daily.left]
banana = 1
""",
            ),
            source="unknown-left.toml",
        )
    with pytest.raises(ConfigError, match=r"unknown key: section\.daily\.right\.banana"):
        parse_toml(
            _minimal(
                enable=["daily"],
                sections="""[section.daily]
columns = ["3fr", "5fr"]
item_spacing = "5mm"

[section.daily.left.priorities]
count = 1

[section.daily.right]
banana = 1
""",
            ),
            source="unknown-right.toml",
        )


@pytest.mark.parametrize("path", [NOMAD, MOS_LEFT])
def test_existing_mos_left_and_nomad_daily_still_parse(path: Path):
    dto = load(path)
    params = _daily_section(dto)["params"]
    assert [c["class"] for c in params["left_column"]] == ["schedule", "little_calendar"]
    assert [c["class"] for c in params["right_column"]] == ["priorities", "notes"]
    assert dto["planner"]["params"]["mos_layout"]["side_menu_position"] == "left"


def test_mos_right_generate_compiles_with_mos_on_the_right(tmp_path):
    dto = short_january(load(MOS_RIGHT))
    mos = dto["planner"]["params"]["mos_layout"]
    assert mos["side_menu_position"] == "right"
    assert mos["side_menu_width"] == "10mm"
    assert mos["menu_rotate"] == "270deg"
    assert mos["reverse_months_quarters_items"] is True
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")["params"]
    assert [c["class"] for c in daily["left_column"]] == ["priorities", "notes"]
    assert [c["class"] for c in daily["right_column"]] == ["schedule", "little_calendar"]
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-1] == "colophon"
    typst_src = _generate(dto)
    assert "columns: (1fr, 10mm)" in typst_src
    assert "columns: (10mm, 1fr)" not in typst_src
    pdf, stderr = compile_pdf(typst_src, tmp_path / "mos-right")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_shipped_mos_right_includes_colophon():
    dto = load(MOS_RIGHT)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-1] == "colophon"
    assert names == ["cover", "index", "annual", "quarterly", "monthly", "weekly", "daily", "daily_notes", "colophon"]


def test_nomad_mos_right_generate_compiles_with_mos_on_the_right(tmp_path):
    dto = short_january(load(NOMAD_MOS_RIGHT))
    mos = dto["planner"]["params"]["mos_layout"]
    assert mos["side_menu_position"] == "right"
    assert mos["side_menu_width"] == "8mm"
    assert mos["menu_rotate"] == "270deg"
    assert mos["reverse_months_quarters_items"] is True
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")["params"]
    assert daily["columns_width"] == "(5fr, 3fr)"
    assert daily["items_spacing"] == "4mm"
    assert [c["class"] for c in daily["left_column"]] == ["priorities", "notes"]
    assert [c["class"] for c in daily["right_column"]] == ["schedule", "little_calendar"]
    notes = daily["left_column"][1]["params"]
    assert notes["notes_height"] == "1fr"
    assert notes["title_height"] == "4mm"
    schedule = daily["right_column"][0]["params"]
    assert schedule["from"] == 8
    assert schedule["to"] == 20
    assert schedule["time_format"] == "%k"
    assert schedule["trailing_30_minutes"] is True
    quarterly = next(s for s in dto["planner"]["sections"] if s["name"] == "quarterly")["params"]
    assert quarterly["months_column"] == "right"
    monthly = next(s for s in dto["planner"]["sections"] if s["name"] == "monthly")["params"]["month_params"]
    assert monthly["week_placement"] == "right"
    assert monthly["daily_cell_height"] == "16mm"
    assert monthly["week_label_rotation"] == "90deg"
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-1] == "colophon"
    typst_src = _generate(dto)
    assert "columns: (1fr, 8mm)" in typst_src
    assert "columns: (8mm, 1fr)" not in typst_src
    assert "rows: 1fr" in typst_src
    assert "rows: (auto, 1fr)" in typst_src
    pdf, stderr = compile_pdf(typst_src, tmp_path / "nomad-mos-right")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_shipped_nomad_mos_right_includes_colophon():
    dto = load(NOMAD_MOS_RIGHT)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-1] == "colophon"
    assert names == ["cover", "index", "annual", "quarterly", "monthly", "weekly", "daily", "daily_notes", "habits", "review", "meetings", "colophon"]


def test_shipped_mos_daily_schedule_track_stays_3fr_on_both_handedness():
    """Schedule is 3fr on MOS-left and MOS-right; notes stay 5fr either side."""
    left = _daily_section(load(MOS_LEFT))["params"]
    assert left["columns_width"] == "(3fr, 5fr)"
    assert [c["class"] for c in left["left_column"]] == ["schedule", "little_calendar"]
    assert [c["class"] for c in left["right_column"]] == ["priorities", "notes"]

    for path in (MOS_RIGHT, NOMAD_MOS_RIGHT):
        right = _daily_section(load(path))["params"]
        assert right["columns_width"] == "(5fr, 3fr)", path.name
        assert [c["class"] for c in right["left_column"]] == ["priorities", "notes"]
        assert [c["class"] for c in right["right_column"]] == ["schedule", "little_calendar"]
