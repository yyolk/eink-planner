"""Projects index + per-project kanban boards."""

from __future__ import annotations

import math
import re
from pathlib import Path

import pytest

from parch import ConfigError
from parch.config import load
from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.sections.projects import Projects, _CARD_BASELINES, _NUM_COL, _length_mm
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.test_toml_omit_sections import _LABEL_DEF, _PADDED_LINK, compile_pdf
from tests.toml_fixtures import _minimal, short_january

REPO = Path(__file__).resolve().parents[1]
NOMAD = REPO / "configs/supernote-nomad.toml"

_CARD_STROKE = "stroke: regular_stroke + black"
_CARD_LINE = "line(length: size.width, stroke: 0.2pt + black)"


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
        card_rows=params.get("card_rows", Projects.CARDS),
    )


def test_length_mm_parses_mm_cm_pt():
    assert _length_mm("10mm") == 10
    assert _length_mm("1cm") == 10
    assert abs(_length_mm("72pt") - 25.4) < 1e-9


def test_omit_pages_defaults_to_sixteen():
    dto = parse_toml(_minimal(enable=["projects"], sections=""), source="default-pages.toml")
    section = dto["planner"]["sections"][0]
    assert section["name"] == "projects"
    assert section["class"] == "projects"
    assert section["params"]["pages"] == 16
    assert section["params"]["card_rows"] == 5
    projects = _projects(dto)
    assert projects.card_rows == Projects.CARDS == 5
    assert Projects.DEFAULT_PAGES == 16
    rpp = projects.rows_per_index_page()
    n_index = projects.index_page_count()
    assert rpp >= 1
    assert n_index == math.ceil(16 / rpp)
    typst = _generate(dto)
    assert "<projects>" in typst
    for i in range(1, 17):
        assert f"<project-{i}>" in typst
    assert "<project-17>" not in typst
    assert typst.count("#pagebreak()") == n_index + 16 - 1
    first = min(16, rpp)
    assert "rows: (" + ", ".join(["2 * regular_height"] * first) + ")" in typst
    leftover = 16 - first
    if leftover:
        assert "rows: (" + ", ".join(["2 * regular_height"] * leftover) + ")" in typst
        assert "<projects-2>" in typst
        assert "rows: (" + ", ".join(["1fr"] * leftover) + ")" not in typst
    assert "rows: (" + ", ".join(["1fr"] * 16) + ")" not in typst
    assert typst.count(_CARD_STROKE) >= projects.card_rows * 3 * 16
    assert typst.count(_CARD_LINE) == _CARD_BASELINES * projects.card_rows * 3 * 16
    assert "rect_pattern_centered(dotted_centered)" not in typst
    assert "luma(180)" not in typst
    assert "→" not in typst


def test_pages_three_emits_index_and_three_boards():
    dto = parse_toml(
        _minimal(enable=["projects"], sections="[section.projects]\npages = 3\n"),
        source="pages-3.toml",
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


def test_index_number_is_the_only_board_link():
    dto = parse_toml(
        _minimal(
            enable=["annual", "projects"],
            sections="""[section.annual]
show_month_name = true

[section.projects]
pages = 3
""",
        ),
        source="links.toml",
    )
    typst = _generate(dto)
    pages = typst.split("#pagebreak()")
    index = next(page for page in pages if "<projects>" in page)
    assert "→" not in index
    assert f"columns: ({_NUM_COL}, 1fr)" in index
    assert "2 * regular_height, 2 * regular_height, 2 * regular_height" in index
    for i in (1, 2, 3):
        assert f"padded_link(<project-{i}>," in index
        # write-in cell is paper, not a second door
        assert f"padded_link(<project-{i}>, [])" not in index
        assert f"padded_link(<project-{i}>)[]" not in index
    # number cell is a full-band hit target; write-in is the following []
    assert re.search(
        r"padded_link\(<project-1>, box\(width: 100%, height: 100%",
        index,
    )
    assert index.count("[]") >= 3
    assert "padded_link(<projects>)" in typst
    assert "padded_link(<annual>)" in typst
    labels = set(_LABEL_DEF.findall(typst))
    links = set(_PADDED_LINK.findall(typst))
    assert {"projects", "project-1", "project-2", "project-3", "annual"} <= labels
    assert {"projects", "project-1", "project-2", "project-3", "annual"} <= links


def test_year_is_plain_when_annual_omitted():
    dto = parse_toml(
        _minimal(enable=["projects"], sections="[section.projects]\npages = 2\n"),
        source="no-annual.toml",
    )
    typst = _generate(dto)
    assert "padded_link(<annual>)" not in typst
    assert "2026" in typst
    assert "<projects>" in typst
    assert "padded_link(<projects>)" in typst


def test_locale_strings_appear():
    dto = parse_toml(
        _minimal(enable=["projects"], sections="[section.projects]\npages = 1\n"),
        source="strings.toml",
    )
    typst = _generate(dto)
    for label in ("To do", "Doing", "Done", "Projects"):
        assert label in typst
    assert "TITLE" not in typst
    assert "DATE" not in typst
    assert "TODO" not in typst
    assert "DOING" not in typst
    assert "DONE" not in typst
    assert "rect_pattern_centered(dotted_centered)" not in typst
    assert _CARD_STROKE in typst
    assert typst.count(_CARD_LINE) == _CARD_BASELINES * 5 * 3


def test_unknown_key_on_section_projects_raises():
    with pytest.raises(ConfigError, match="unknown key: section.projects.pattern"):
        parse_toml(
            _minimal(enable=["projects"], sections="[section.projects]\npages = 3\npattern = \"dotted\"\n"),
            source="extra.toml",
        )
    with pytest.raises(ConfigError, match="unknown key: section.projects.foo"):
        parse_toml(
            _minimal(enable=["projects"], sections="[section.projects]\nfoo = 1\n"),
            source="foo.toml",
        )


def test_pages_bool_and_float_rejected():
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(enable=["projects"], sections="[section.projects]\npages = true\n"),
            source="bool.toml",
        )
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(enable=["projects"], sections="[section.projects]\npages = 3.5\n"),
            source="float.toml",
        )


def test_card_rows_bool_and_float_rejected():
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(enable=["projects"], sections="[section.projects]\ncard_rows = true\n"),
            source="card_rows-bool.toml",
        )
    with pytest.raises(ConfigError, match="expected integer"):
        parse_toml(
            _minimal(enable=["projects"], sections="[section.projects]\ncard_rows = 5.5\n"),
            source="card_rows-float.toml",
        )


def test_pages_are_raw_typst_without_mos_chrome():
    dto = parse_toml(
        _minimal(enable=["projects"], sections="[section.projects]\npages = 1\n"),
        source="raw.toml",
    )
    typst = _generate(dto)
    assert "side_menu" not in typst
    assert "rotate(" not in typst
    assert "<projects>" in typst
    assert "<project-1>" in typst


def test_index_rows_are_fixed_line_height_and_boards_use_five_fat_cards():
    assert Projects.CARDS == 5
    dto = parse_toml(
        _minimal(enable=["projects"], sections="[section.projects]\npages = 3\n"),
        source="layout.toml",
    )
    typst = _generate(dto)
    assert "rows: (2 * regular_height, 2 * regular_height, 2 * regular_height)" in typst
    # leftover index rows stay 2× regular_height; card interiors use placed 1/4–3/4 lines
    assert "rows: (1fr, 1fr, 1fr)" not in typst  # no 1fr baseline grid
    assert "1/4 * size.height" in typst
    assert "2/4 * size.height" in typst
    assert "3/4 * size.height" in typst
    assert "rows: (" + ", ".join(["1fr"] * 5) + ")" in typst
    assert "rows: (" + ", ".join(["1fr"] * 8) + ")" not in typst
    assert typst.count(_CARD_STROKE) >= 5 * 3 * 3
    assert typst.count(_CARD_LINE) == _CARD_BASELINES * 5 * 3 * 3
    assert "rect_pattern_centered(dotted_centered)" not in typst
    assert "luma(180)" not in typst


def test_card_rows_eight_emits_eight_one_fr_rows_per_column():
    dto = parse_toml(
        _minimal(enable=["projects"], sections="[section.projects]\npages = 1\ncard_rows = 8\n"),
        source="card_rows-8.toml",
    )
    params = dto["planner"]["sections"][0]["params"]
    assert params["pages"] == 1
    assert params["card_rows"] == 8
    projects = _projects(dto)
    assert projects.card_rows == 8
    assert Projects.CARDS == 5
    typst = _generate(dto)
    assert "rows: (" + ", ".join(["1fr"] * 8) + ")" in typst
    assert typst.count(_CARD_LINE) == _CARD_BASELINES * 8 * 3 * 1


def test_index_paginates_and_late_board_links_to_its_index_page():
    dto = load(NOMAD)
    projects = _projects(dto)
    rpp = projects.rows_per_index_page()
    assert rpp == 16
    n = rpp + 1
    slim = parse_toml(
        _minimal(
            device="""[device]
name = "supernote-nomad"
width = "118.87mm"
height = "158.5mm"
ppi = 300""",
            enable=["annual", "projects"],
            sections=f"""[section.annual]
show_month_name = true

[section.projects]
pages = {n}
""",
        ),
        source="paged-index.toml",
    )
    slim_projects = _projects(slim)
    assert slim_projects.rows_per_index_page() == rpp
    assert slim_projects.index_page_count() == 2
    typst = _generate(slim)
    labels = set(_LABEL_DEF.findall(typst))
    assert {"projects", "projects-2", f"project-{n}", "annual"} <= labels
    pages = typst.split("#pagebreak()")
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


def test_nomad_default_is_one_index_page():
    dto = load(NOMAD)
    projects = _projects(dto)
    assert projects.pages_num == 16
    assert projects.card_rows == 5
    assert projects.rows_per_index_page() == 16
    assert projects.index_page_count() == 1
    typst = _generate(short_january(dto))
    assert "<projects>" in typst
    assert "<projects-2>" not in typst
    assert "<project-1>" in typst
    assert "<project-16>" in typst
    assert "<project-17>" not in typst
    assert "padded_link(<annual>)" in typst
    index = next(page for page in typst.split("#pagebreak()") if "<projects>" in page)
    assert "→" not in index
    assert f"columns: ({_NUM_COL}, 1fr)" in index
    assert "rows: (" + ", ".join(["2 * regular_height"] * 16) + ")" in index
    assert "rows: (" + ", ".join(["1fr"] * 16) + ")" not in index


def test_pages_twenty_paginates_without_stretching_leftover_rows():
    slim = parse_toml(
        _minimal(
            device="""[device]
name = "supernote-nomad"
width = "118.87mm"
height = "158.5mm"
ppi = 300""",
            enable=["projects"],
            sections="""[section.projects]
pages = 20
""",
        ),
        source="pages-20-leftover.toml",
    )
    projects = _projects(slim)
    assert projects.rows_per_index_page() == 16
    assert projects.index_page_count() == 2
    typst = _generate(slim)
    assert "<projects>" in typst
    assert "<projects-2>" in typst
    assert "<project-20>" in typst
    assert "<project-21>" not in typst
    leftover = "rows: (" + ", ".join(["2 * regular_height"] * 4) + ")"
    fattened = "rows: (" + ", ".join(["1fr"] * 4) + ")"
    assert leftover in typst
    assert fattened not in typst
    pages = typst.split("#pagebreak()")
    second = next(page for page in pages if "<projects-2>" in page)
    assert leftover in second
    assert fattened not in second
    assert "→" not in second
    board_late = next(page for page in pages if "<project-17>" in page and "1fr, 1fr, 1fr" in page)
    assert "padded_link(<projects-2>)" in board_late
    assert "padded_link(<projects>)" not in board_late


def test_nomad_parses_and_compiles(tmp_path):
    dto = load(NOMAD)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert "projects" in names
    projects = next(s for s in dto["planner"]["sections"] if s["name"] == "projects")
    assert projects["params"]["pages"] == 16
    assert projects["params"]["card_rows"] == 5
    typst = _generate(short_january(dto))
    assert "<projects>" in typst
    assert "<projects-2>" not in typst
    assert "<project-1>" in typst
    assert "<project-16>" in typst
    assert "padded_link(<annual>)" in typst
    pdf, stderr = compile_pdf(typst, tmp_path / "nomad-projects")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_tiny_cover_annual_projects_compiles(tmp_path):
    dto = parse_toml(
        _minimal(
            enable=["cover", "annual", "projects"],
            sections="""[section.cover]
title = "Hi"
font_size = "12pt"

[section.annual]
show_month_name = true

[section.projects]
pages = 3
""",
        ),
        source="tiny.toml",
    )
    typst = _generate(dto)
    pdf, stderr = compile_pdf(typst, tmp_path / "tiny-projects")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_kanban_baselines_leave_notes_global_dotted():
    dto = parse_toml(
        _minimal(
            enable=["daily", "daily_notes", "projects"],
            sections="""[section.daily]
columns = ["3fr", "5fr"]
item_spacing = "4mm"

[section.daily.left.schedule]
hour_from = 8
hour_to = 20

[section.daily.right.notes]
pattern = "dotted"
title_height = "4mm"

[section.daily_notes]
pages = 1
pattern = "dotted"

[section.projects]
pages = 1
""",
        ),
        source="baselines-vs-notes.toml",
    )
    typst = _generate(dto)
    assert "#let dotted =" in typst
    assert "dx: 0.5pt" in typst
    assert "dy: regular_height - 0.3mm" in typst
    assert "#let rect_pattern(pattern) = rect(" in typst
    assert "rect_pattern_centered(dotted_centered)" not in typst
    assert _CARD_STROKE in typst
    assert typst.count(_CARD_LINE) == _CARD_BASELINES * _projects(dto).card_rows * 3
    assert "#let scratch_pad = rect_pattern(dotted)" in typst
    pages = typst.split("#pagebreak()")
    board_pages = [page for page in pages if "1/1 <project-1>" in page]
    assert board_pages
    assert all("rect_pattern_centered" not in page for page in board_pages)
    assert all(_CARD_STROKE in page for page in board_pages)
    assert all(_CARD_LINE in page for page in board_pages)
    notes_body_pages = [
        page
        for page in pages
        if "rect_pattern(dotted)" in page and "rect_pattern_centered" not in page
    ]
    assert notes_body_pages, "notes pages must still call rect_pattern(dotted)"
