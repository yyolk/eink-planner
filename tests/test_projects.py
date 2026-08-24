"""Projects index + per-project kanban boards."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.config import load
from eink_planner.i18n import I18n
from eink_planner.kdl_config import parse_kdl
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.sections.projects import Projects, _length_mm
from eink_planner.services.generate import Generate
from tests.test_kdl_config import _minimal
from tests.test_kdl_omit_sections import _LABEL_DEF, _PADDED_LINK, _short_january, compile_pdf

REPO = Path(__file__).resolve().parents[1]
NOMAD = REPO / "configs/supernote-nomad.kdl"


def _generate(dto) -> str:
    return Generate(i18n=I18n.load_default(REPO, "en")).generate(dto)


def _projects(dto, pages: int | None = None) -> Projects:
    params = {}
    for section in dto["planner"]["sections"]:
        if section.get("class") == "projects" or section.get("name") == "projects":
            params = dict(section.get("params") or {})
            break
    if pages is not None:
        params["pages"] = pages
    return Projects(
        section_name="projects",
        i18n=I18n.load_default(REPO, "en"),
        configurator=Configurator(dto),
        pages=params.get("pages", Projects.DEFAULT_PAGES),
    )


def test_length_mm_parses_mm_cm_pt():
    assert _length_mm("10mm") == 10
    assert _length_mm("1cm") == 10
    assert abs(_length_mm("72pt") - 25.4) < 1e-9


def test_omit_pages_defaults_to_twenty():
    dto = parse_kdl(_minimal(sections="section projects { }\n"), source="default-pages.kdl")
    section = dto["planner"]["sections"][0]
    assert section["name"] == "projects"
    assert section["class"] == "projects"
    assert section["params"]["pages"] == 20
    projects = _projects(dto)
    rpp = projects.rows_per_index_page()
    n_index = projects.index_page_count()
    assert rpp >= 1
    assert n_index == math.ceil(20 / rpp)
    typst = _generate(dto)
    assert "<projects>" in typst
    for i in range(1, 21):
        assert f"<project-{i}>" in typst
    assert "<project-21>" not in typst
    assert typst.count("#pagebreak()") == n_index + 20 - 1
    first = min(20, rpp)
    assert "rows: (" + ", ".join(["2 * regular_height"] * first) + ")" in typst
    leftover = 20 - first
    if leftover:
        assert "rows: (" + ", ".join(["2 * regular_height"] * leftover) + ")" in typst
        assert "<projects-2>" in typst
    assert "rows: (" + ", ".join(["1fr"] * 20) + ")" not in typst
    card = "grid.cell(stroke: regular_stroke + luma(180), inset: 0pt, rect_pattern_centered(dotted_centered))"
    assert typst.count(card) == Projects.CARDS * 3 * 20


def test_pages_three_emits_index_and_three_boards():
    dto = parse_kdl(
        _minimal(sections="section projects {\n  pages 3\n}\n"),
        source="pages-3.kdl",
    )
    assert dto["planner"]["sections"][0]["params"]["pages"] == 3
    projects = _projects(dto)
    assert 3 <= projects.rows_per_index_page()
    assert projects.index_page_count() == 1
    typst = _generate(dto)
    assert "<projects>" in typst
    assert "<projects-2>" not in typst
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
    assert "rect_pattern_centered(dotted_centered)" in typst


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


def test_index_rows_are_fixed_line_height_and_boards_use_eight_even_cards():
    assert Projects.CARDS == 8
    dto = parse_kdl(
        _minimal(sections="section projects {\n  pages 3\n}\n"),
        source="layout.kdl",
    )
    typst = _generate(dto)
    assert "rows: (2 * regular_height, 2 * regular_height, 2 * regular_height)" in typst
    assert "rows: (1fr, 1fr, 1fr)" not in typst
    assert "rows: (" + ", ".join(["1fr"] * 8) + ")" in typst
    card = "grid.cell(stroke: regular_stroke + luma(180), inset: 0pt, rect_pattern_centered(dotted_centered))"
    assert typst.count(card) == 8 * 3 * 3


def test_index_paginates_and_late_board_links_to_its_index_page():
    dto = load(NOMAD)
    projects = _projects(dto)
    rpp = projects.rows_per_index_page()
    # Nomad: 158.5 − 8 − 0 − 8 − 4 − 3 = 135.5; 135.5 / (2×4) → 16
    assert rpp == 16
    n = rpp + 1
    slim = parse_kdl(
        _minimal(
            device="""device "supernote-nomad" {
  page-size 118.87mm 158.5mm
  ppi 300
}""",
            sections=(
                "section annual {\n  little-calendar {\n    show-month-name #true\n  }\n}\n"
                f"section projects {{\n  pages {n}\n}}\n"
            ),
        ),
        source="paged-index.kdl",
    )
    slim_projects = _projects(slim)
    assert slim_projects.rows_per_index_page() == rpp
    assert slim_projects.index_page_count() == 2
    typst = _generate(slim)
    labels = set(_LABEL_DEF.findall(typst))
    assert {"projects", "projects-2", f"project-{n}", "annual"} <= labels
    pages = typst.split("#pagebreak()")
    # annual, index 1, index 2, boards 1..n
    assert len(pages) == 3 + n
    board_first = pages[3]
    board_late = pages[3 + rpp]
    assert f"<project-1>" in board_first
    assert f"<project-{n}>" in board_late
    assert "padded_link(<projects>)" in board_first
    assert "padded_link(<projects-2>)" not in board_first
    assert "padded_link(<projects-2>)" in board_late
    assert "padded_link(<projects>)" not in board_late
    assert "padded_link(<annual>)" in board_late
    assert "padded_link(<projects>)" in pages[2]


def test_nomad_parses_and_compiles(tmp_path):
    dto = load(NOMAD)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[-1] == "projects"
    assert dto["planner"]["sections"][-1]["params"]["pages"] == 20
    typst = _generate(_short_january(dto))
    assert "<projects>" in typst
    assert "<projects-2>" in typst
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


def test_kanban_centered_dots_leave_notes_global_dotted():
    dto = parse_kdl(
        _minimal(
            sections=(
                "section daily {\n"
                "  columns (3fr 5fr)\n"
                "  item-spacing 4mm\n"
                "  right {\n"
                "    notes {\n"
                "      pattern dotted\n"
                "      title-height 4mm\n"
                "    }\n"
                "  }\n"
                "}\n"
                "section daily-notes {\n  pages 1\n  pattern dotted\n}\n"
                "section projects {\n  pages 1\n}\n"
            )
        ),
        source="centered-vs-notes.kdl",
    )
    typst = _generate(dto)
    assert "#let dotted =" in typst
    assert "dx: 0.5pt" in typst
    assert "dy: regular_height - 0.3mm" in typst
    assert "#let dotted_centered = tiling(" in typst
    assert "center + horizon" in typst
    assert "#let rect_pattern_centered(pattern) = box(" in typst
    assert "layout(size =>" in typst
    assert "calc.floor(size.width.pt() / cell.pt())" in typst
    assert "calc.floor(size.height.pt() / cell.pt())" in typst
    assert "let nw = cols * cell" in typst
    assert "let nh = rows * cell" in typst
    assert "calc.rem(" not in typst
    assert "clip: true" not in typst
    card = "grid.cell(stroke: regular_stroke + luma(180), inset: 0pt, rect_pattern_centered(dotted_centered))"
    assert typst.count(card) == Projects.CARDS * 3
    assert "inset: 0pt, rect_pattern(dotted)" not in typst
    assert "#let scratch_pad = rect_pattern(dotted)" in typst
    pages = typst.split("#pagebreak()")
    board_pages = [page for page in pages if "1/1 <project-1>" in page]
    assert board_pages
    assert all("rect_pattern_centered(dotted_centered)" in page for page in board_pages)
    assert all("rect_pattern(dotted)" not in page for page in board_pages)
    notes_body_pages = [
        page
        for page in pages
        if "rect_pattern(dotted)" in page and "rect_pattern_centered" not in page
    ]
    assert notes_body_pages, "notes pages must still call rect_pattern(dotted)"
