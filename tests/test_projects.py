"""Projects index + per-project kanban boards."""

from __future__ import annotations

from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.config import load
from eink_planner.i18n import I18n
from eink_planner.kdl_config import parse_kdl
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.sections.projects import Projects
from eink_planner.services.generate import Generate
from tests.test_kdl_config import _minimal
from tests.test_kdl_omit_sections import _LABEL_DEF, _PADDED_LINK, _short_january, compile_pdf

REPO = Path(__file__).resolve().parents[1]
NOMAD = REPO / "configs/supernote-nomad.kdl"


def _generate(dto) -> str:
    return Generate(i18n=I18n.load_default(REPO, "en")).generate(dto)


def test_omit_pages_defaults_to_twenty():
    dto = parse_kdl(_minimal(sections="section projects { }\n"), source="default-pages.kdl")
    section = dto["planner"]["sections"][0]
    assert section["name"] == "projects"
    assert section["class"] == "projects"
    assert section["params"]["pages"] == 20
    typst = _generate(dto)
    assert "<projects>" in typst
    for i in range(1, 21):
        assert f"<project-{i}>" in typst
    assert "<project-21>" not in typst
    assert typst.count("#pagebreak()") == 20
    assert "rows: (" + ", ".join(["auto"] * 20) + ")" in typst
    assert "rows: (" + ", ".join(["1fr"] * 20) + ")" not in typst
    card = "grid.cell(stroke: regular_stroke, inset: 0pt, rect_pattern(dotted))"
    assert typst.count(card) == Projects.CARDS * 3 * 20


def test_pages_three_emits_index_and_three_boards():
    dto = parse_kdl(
        _minimal(sections="section projects {\n  pages 3\n}\n"),
        source="pages-3.kdl",
    )
    assert dto["planner"]["sections"][0]["params"]["pages"] == 3
    typst = _generate(dto)
    assert "<projects>" in typst
    assert "<project-1>" in typst
    assert "<project-2>" in typst
    assert "<project-3>" in typst
    assert "<project-4>" not in typst
    assert typst.count("#pagebreak()") == 3


def test_index_links_to_boards_and_board_links_back():
    dto = parse_kdl(
        _minimal(
            sections=(
                "section annual {\n  little-calendar {\n    show-month-name #true\n  }\n}\n"
                "section projects {\n  pages 3\n}\n"
            )
        ),
        source="links.kdl",
    )
    typst = _generate(dto)
    assert "padded_link(<project-1>)" in typst
    assert "padded_link(<project-2>)" in typst
    assert "padded_link(<project-3>)" in typst
    assert "padded_link(<projects>)" in typst
    assert "padded_link(<annual>)" in typst
    labels = set(_LABEL_DEF.findall(typst))
    links = set(_PADDED_LINK.findall(typst))
    assert {"projects", "project-1", "project-2", "project-3", "annual"} <= labels
    assert {"projects", "project-1", "project-2", "project-3", "annual"} <= links


def test_year_is_plain_when_annual_omitted():
    dto = parse_kdl(
        _minimal(sections="section projects {\n  pages 2\n}\n"),
        source="no-annual.kdl",
    )
    typst = _generate(dto)
    assert "padded_link(<annual>)" not in typst
    assert "2026" in typst
    assert "<projects>" in typst
    assert "padded_link(<projects>)" in typst


def test_locale_strings_appear():
    dto = parse_kdl(
        _minimal(sections="section projects {\n  pages 1\n}\n"),
        source="strings.kdl",
    )
    typst = _generate(dto)
    for label in ("TITLE", "DATE", "TODO", "DOING", "DONE", "Projects"):
        assert label in typst
    assert "rect_pattern(dotted)" in typst


def test_unknown_node_on_section_projects_raises():
    with pytest.raises(ConfigError, match="unknown node: section.projects.pattern"):
        parse_kdl(
            _minimal(sections="section projects {\n  pages 3\n  pattern dotted\n}\n"),
            source="extra.kdl",
        )
    with pytest.raises(ConfigError, match="unknown node: section.projects.foo"):
        parse_kdl(
            _minimal(sections="section projects {\n  foo 1\n}\n"),
            source="foo.kdl",
        )


def test_pages_bool_and_float_rejected():
    with pytest.raises(ConfigError, match="expected integer"):
        parse_kdl(
            _minimal(sections="section projects {\n  pages #true\n}\n"),
            source="bool.kdl",
        )
    with pytest.raises(ConfigError, match="expected integer"):
        parse_kdl(
            _minimal(sections="section projects {\n  pages 3.5\n}\n"),
            source="float.kdl",
        )


def test_pages_are_raw_typst_without_mos_chrome():
    dto = parse_kdl(
        _minimal(sections="section projects {\n  pages 1\n}\n"),
        source="raw.kdl",
    )
    typst = _generate(dto)
    assert "side_menu" not in typst
    assert "rotate(" not in typst
    assert "<projects>" in typst
    assert "<project-1>" in typst


def test_index_rows_are_auto_and_boards_use_eight_even_cards():
    assert Projects.CARDS == 8
    dto = parse_kdl(
        _minimal(sections="section projects {\n  pages 3\n}\n"),
        source="layout.kdl",
    )
    typst = _generate(dto)
    assert "rows: (auto, auto, auto)" in typst
    assert "rows: (1fr, 1fr, 1fr)" not in typst
    assert "rows: (" + ", ".join(["1fr"] * 8) + ")" in typst
    card = "grid.cell(stroke: regular_stroke, inset: 0pt, rect_pattern(dotted))"
    assert typst.count(card) == 8 * 3 * 3


def test_nomad_parses_and_compiles(tmp_path):
    dto = load(NOMAD)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-1] == "projects"
    assert dto["planner"]["sections"][-1]["params"]["pages"] == 20
    typst = _generate(_short_january(dto))
    assert "<projects>" in typst
    assert "<project-1>" in typst
    assert "<project-20>" in typst
    assert "padded_link(<annual>)" in typst
    pdf, stderr = compile_pdf(typst, tmp_path / "nomad-projects")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_tiny_cover_annual_projects_compiles(tmp_path):
    dto = parse_kdl(
        _minimal(
            sections=(
                'section cover {\n  title "Hi"\n  font-size 12pt\n}\n'
                "section annual {\n  little-calendar {\n    show-month-name #true\n  }\n}\n"
                "section projects {\n  pages 3\n}\n"
            )
        ),
        source="tiny.kdl",
    )
    typst = _generate(dto)
    pdf, stderr = compile_pdf(typst, tmp_path / "tiny-projects")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr
