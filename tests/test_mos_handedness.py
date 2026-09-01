"""Left/right MOS (Months on the Side) handedness and unlocked daily columns."""

from pathlib import Path

import pytest

from parch import ConfigError
from parch.cli import generate_cmd
from parch.config import load
from parch.mos.configurator import Configurator
from parch.services.generate import Generate
from parch.toml_config import apply_hand, parse_toml
from tests.test_toml_omit_sections import compile_pdf
from tests.toml_fixtures import _minimal, short_january
from tests.helpers import base_config, load_default

NOMAD = base_config("supernote-nomad")
PAPER_158 = base_config("158x210")


def _generate(dto) -> str:
    return Generate(i18n=load_default()).generate(dto)


def _daily_section(dto):
    return next(s for s in dto["planner"]["sections"] if s["name"] == "daily")


def test_side_menu_right_parses():
    dto = parse_toml(
        _minimal(
            mos="""[mos]
side_menu = "right"
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
    assert "side_menu_width" not in mos
    assert mos["reverse_months_quarters"] is True


def test_side_menu_position_is_case_insensitive():
    dto = parse_toml(
        _minimal(
            mos="""[mos]
side_menu = "RIGHT"
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
    with pytest.raises(ConfigError, match=r"mos\.side_menu: expected left or right"):
        parse_toml(
            _minimal(
                mos="""[mos]
side_menu = "top"
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
item_spacing = "5mm"

[section.daily.left.notes]
pattern = "dotted"
title_height = "5mm"

[section.daily.left.little_calendar]
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
    assert "week_placement" not in dto["planner"]["params"]["little_calendar"]

    typst_src = _generate(short_january(dto))
    marker = "daily_well("
    body = typst_src[typst_src.index(marker) :]
    assert "daily_well(left," in body
    assert body.index("[Notes") < body.index("[Schedule]")
    assert "rows: (auto, 1fr)" in typst_src


def test_unknown_daily_child_still_rejected():
    with pytest.raises(ConfigError, match=r"unknown key: section\.daily\.left\.banana"):
        parse_toml(
            _minimal(
                enable=["daily"],
                sections="""[section.daily]
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
item_spacing = "5mm"

[section.daily.left.priorities]
count = 1

[section.daily.right]
banana = 1
""",
            ),
            source="unknown-right.toml",
        )


@pytest.mark.parametrize("path", [NOMAD, PAPER_158])
def test_existing_mos_left_and_nomad_daily_still_parse(path: Path):
    dto = load(path)
    params = _daily_section(dto)["params"]
    assert [c["class"] for c in params["left_column"]] == ["schedule", "little_calendar"]
    assert [c["class"] for c in params["right_column"]] == ["priorities", "notes"]
    assert dto["planner"]["params"]["mos_layout"]["side_menu_position"] == "left"


def test_hand_right_generate_compiles_with_mos_on_the_right(tmp_path):
    dto = short_january(apply_hand(load(PAPER_158), "right"))
    mos = dto["planner"]["params"]["mos_layout"]
    assert mos["side_menu_position"] == "right"
    assert "side_menu_width" not in mos
    assert mos["reverse_months_quarters"] is True
    assert mos["menu_rotate"] == "270deg"
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")["params"]
    assert "columns_width" not in daily
    assert [c["class"] for c in daily["left_column"]] == ["schedule", "little_calendar"]
    assert [c["class"] for c in daily["right_column"]] == ["priorities", "notes"]
    quarterly = next(s for s in dto["planner"]["sections"] if s["name"] == "quarterly")["params"]
    assert "months_column" not in quarterly
    monthly = next(s for s in dto["planner"]["sections"] if s["name"] == "monthly")["params"]["month_params"]
    assert "week_placement" not in monthly
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-1] == "colophon"
    typst_src = _generate(dto)
    assert "page-margin(right)" in typst_src
    assert "#mos_frame(\n  right," in typst_src
    assert "#mos_frame(\n  left," not in typst_src
    assert "mos-width: mos-width" in typst_src
    assert "daily_well(right," in typst_src
    assert "month_grid(right," in typst_src
    assert "month_weeks(right," in typst_src
    assert "quarter_well(right," in typst_src
    assert "month_grid(left," not in typst_src
    assert "month_weeks(left," not in typst_src
    assert "quarter_well(left," not in typst_src
    assert "[], [M], [T], [W], [T], [F], [S], [S]" in typst_src
    well = typst_src[typst_src.index("daily_well(") :]
    assert well.index("right,") < well.index("[Schedule]")
    assert well.index("[Schedule]") < well.index("[Priorities]")
    quarter = typst_src[typst_src.index("quarter_well(") :]
    assert quarter.index("right,") < quarter.index("rows: (1fr, 1fr, 1fr)")
    assert quarter.index("rows: (1fr, 1fr, 1fr)") < quarter.index("lined_well(")
    pdf, stderr = compile_pdf(typst_src, tmp_path / "hand-right")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_shipped_158x210_includes_colophon():
    dto = load(PAPER_158)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-1] == "colophon"
    assert names == ["cover", "index", "annual", "quarterly", "monthly", "weekly", "daily", "daily_notes", "colophon"]


def test_nomad_hand_right_generate_compiles_with_mos_on_the_right(tmp_path):
    dto = short_january(apply_hand(load(NOMAD), "right"))
    mos = dto["planner"]["params"]["mos_layout"]
    assert mos["side_menu_position"] == "right"
    assert "side_menu_width" not in mos
    assert mos["reverse_months_quarters"] is True
    assert mos["menu_rotate"] == "270deg"
    daily = next(s for s in dto["planner"]["sections"] if s["name"] == "daily")["params"]
    assert "columns_width" not in daily
    assert daily["items_spacing"] == "4mm"
    assert [c["class"] for c in daily["left_column"]] == ["schedule", "little_calendar"]
    assert [c["class"] for c in daily["right_column"]] == ["priorities", "notes"]
    notes = daily["right_column"][1]["params"]
    assert notes["notes_height"] == "1fr"
    assert notes["title_height"] == "4mm"
    schedule = daily["left_column"][0]["params"]
    assert schedule["from"] == 8
    assert schedule["to"] == 20
    assert schedule["time_format"] == "%k"
    assert schedule["trailing_30_minutes"] is True
    quarterly = next(s for s in dto["planner"]["sections"] if s["name"] == "quarterly")["params"]
    assert "months_column" not in quarterly
    monthly = next(s for s in dto["planner"]["sections"] if s["name"] == "monthly")["params"]["month_params"]
    assert "week_placement" not in monthly
    assert monthly["daily_cell_height"] == "16mm"
    assert monthly["week_label_rotation"] == "90deg"
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-1] == "colophon"
    typst_src = _generate(dto)
    assert "page-margin(right)" in typst_src
    assert "#mos_frame(\n  right," in typst_src
    assert "#mos_frame(\n  left," not in typst_src
    assert "mos-width: mos-width" in typst_src
    assert "rows: 1fr" in typst_src
    assert "rows: (auto, 1fr)" in typst_src
    assert "daily_well(right," in typst_src
    well = typst_src[typst_src.index("daily_well(") :]
    assert well.index("right,") < well.index("[Schedule]")
    assert well.index("[Schedule]") < well.index("[Priorities]")
    pdf, stderr = compile_pdf(typst_src, tmp_path / "nomad-hand-right")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_shipped_nomad_includes_colophon():
    dto = load(NOMAD)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-1] == "colophon"
    assert names == ["cover", "index", "annual", "quarterly", "monthly", "weekly", "daily", "daily_notes", "colophon"]


def test_shipped_mos_daily_tracks_stay_hours_then_writing_on_both_hands():
    """TOML left|right stay hours then writing; --hand does not swap those tables."""
    left = _daily_section(load(PAPER_158))["params"]
    assert "columns_width" not in left
    assert [c["class"] for c in left["left_column"]] == ["schedule", "little_calendar"]
    assert [c["class"] for c in left["right_column"]] == ["priorities", "notes"]

    for path in (PAPER_158, NOMAD):
        right = _daily_section(apply_hand(load(path), "right"))["params"]
        assert "columns_width" not in right, path.name
        assert [c["class"] for c in right["left_column"]] == ["schedule", "little_calendar"]
        assert [c["class"] for c in right["right_column"]] == ["priorities", "notes"]


def test_press_hand_right_sets_page_margin_and_mos_frame(tmp_path, monkeypatch):
    class _DummyCompile:
        def compile(self, workdir, file="index.typst", **_kwargs):
            pdf = Path(workdir) / "index.pdf"
            pdf.write_bytes(b"%PDF-dummy")
            return pdf

    monkeypatch.setattr("parch.cli.Compile", lambda: _DummyCompile())
    ns = type(
        "Args",
        (),
        {
            "config": str(PAPER_158),
            "workdir": str(tmp_path / "out"),
            "locale": "en",
            "with_ghostscript": False,
            "debug": False,
            "year": None,
            "hand": "right",
        },
    )()
    assert generate_cmd(ns, argv=["parch", "press", str(PAPER_158), "--hand", "right"]) == 0
    typst = (tmp_path / "out" / "index.typst").read_text(encoding="utf-8")
    assert "page-margin(right)" in typst
    assert "#mos_frame(\n  right," in typst
    assert "page-margin(left)" not in typst
    assert "#mos_frame(\n  left," not in typst
    assert "daily_well(right," in typst
    well = typst[typst.index("daily_well(") :]
    assert well.index("right,") < well.index("[Schedule]")
    assert well.index("[Schedule]") < well.index("[Priorities]")
    assert "columns: (3fr, 5fr)" not in typst
    assert "columns: (5fr, 3fr)" not in typst
