"""Colophon section: provenance page, layout-agnostic.

Calendar sections (annual, quarterly, monthly, weekly, daily, daily-notes)
are not designed to repeat. The ordered section list already allows two
``section daily`` nodes and would duplicate pages; we do not add uniqueness
enforcement. Colophon may repeat: each ``section colophon`` emits another
about page (same content unless titles differ).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.config import StrictDict, load
from eink_planner.i18n import I18n
from eink_planner.kdl_config import parse_kdl
from eink_planner.mos.configurator import Configurator
from eink_planner.provenance import apply_provenance, collect_provenance
from eink_planner.sections.colophon import DEFAULT_TITLE, Colophon
from eink_planner.services.generate import Generate
from tests.test_kdl_omit_sections import (
    _LABEL_DEF,
    _PADDED_LINK,
    _short_january,
    compile_pdf,
)

REPO = Path(__file__).resolve().parents[1]
NOMAD = REPO / "configs/supernote-nomad.kdl"


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
        "sections": "section colophon { }\n",
    }
    parts.update(extra)
    return "\n\n".join(parts.values()) + "\n"


def _generate(dto: StrictDict) -> str:
    return Generate(i18n=I18n.load_default(REPO, "en")).generate(dto)


def _attach(dto: StrictDict, path: Path, argv: list[str] | None = None) -> StrictDict:
    return apply_provenance(
        dto,
        collect_provenance(
            config_path=path,
            argv=argv or ["lyp", "generate", str(path)],
            start=REPO,
        ),
    )


def test_empty_colophon_body_is_valid():
    dto = parse_kdl(_minimal(), source="empty-colophon.kdl")
    sections = dto["planner"]["sections"]
    assert len(sections) == 1
    assert sections[0]["name"] == "colophon"
    assert sections[0]["class"] == "colophon"
    assert sections[0]["enabled"] is True
    assert sections[0]["params"].to_plain() == {}


def test_colophon_optional_title():
    dto = parse_kdl(
        _minimal(sections='section colophon {\n  title "Provenance"\n}\n'),
        source="titled.kdl",
    )
    assert dto["planner"]["sections"][0]["params"]["title"] == "Provenance"


def test_colophon_rejects_unknown_children():
    with pytest.raises(ConfigError, match="unknown node"):
        parse_kdl(
            _minimal(sections="section colophon {\n  git abcdef\n}\n"),
            source="git-key.kdl",
        )
    with pytest.raises(ConfigError, match="unknown node"):
        parse_kdl(
            _minimal(sections="section colophon {\n  command \"lyp\"\n}\n"),
            source="command-key.kdl",
        )


def test_multiple_colophon_nodes_parse_in_order():
    dto = parse_kdl(
        _minimal(
            sections=(
                "section cover {\n  title \"Hi\"\n  font-size 12pt\n}\n"
                "section colophon { }\n"
                'section colophon {\n  title "Again"\n}\n'
            )
        ),
        source="two-colo.kdl",
    )
    names = [s["name"] for s in dto["planner"]["sections"]]
    assert names == ["cover", "colophon", "colophon"]
    assert dto["planner"]["sections"][2]["params"]["title"] == "Again"


def test_colophon_is_raw_without_mos_chrome():
    colo = Colophon(section_name="colophon")
    pages = colo.pages(None)
    assert len(pages) == 1
    assert pages[0].raw_typst is True
    assert pages[0].page_id is None
    assert "Calendar" not in pages[0].content
    assert "side_menu" not in pages[0].content
    assert DEFAULT_TITLE in pages[0].content
    assert "unknown" in pages[0].content


def test_injected_git_sha_and_command_appear_in_typst():
    dto = _short_january(parse_kdl(_minimal(), source="inject.kdl"))
    data = dto.to_plain()
    data["planner"]["params"]["provenance"] = {
        "command": "lyp generate custom.kdl --debug",
        "version": "9.9.9-test",
        "git_sha": "deadbeef" * 5,
        "config_path": "/tmp/custom.kdl",
        "config_sha256": "abc123def456",
        "config_text": "section colophon { }\n#true `ticks`\n",
    }
    typst_src = _generate(StrictDict(data))
    assert "lyp generate custom.kdl --debug" in typst_src
    assert "deadbeef" * 5 in typst_src
    assert "9.9.9-test" in typst_src
    assert "abc123def456" in typst_src
    assert "/tmp/custom.kdl" in typst_src
    assert "section colophon { }" in typst_src
    assert "#true" in typst_src
    assert "`ticks`" in typst_src
    assert DEFAULT_TITLE in typst_src


def test_sha256_matches_hashlib_of_file_bytes(tmp_path):
    path = tmp_path / "plain.kdl"
    path.write_text(_minimal(), encoding="utf-8")
    dto = _attach(_short_january(load(path)), path)
    typst_src = _generate(dto)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert expected in typst_src
    assert expected == hashlib.sha256(path.read_bytes()).hexdigest()


def test_colophon_last_dumps_config_and_compiles(tmp_path):
    text = NOMAD.read_text(encoding="utf-8").rstrip() + "\n\nsection colophon { }\n"
    path = tmp_path / "last.kdl"
    path.write_text(text, encoding="utf-8")
    dto = _attach(_short_january(load(path)), path)
    typst_src = _generate(dto)
    dump = path.read_text(encoding="utf-8")
    assert "supernote-nomad" in typst_src
    assert "section colophon { }" in typst_src
    assert hashlib.sha256(path.read_bytes()).hexdigest() in typst_src
    for snippet in ("year 2026", "week-starts Monday", "reverse-months-quarters"):
        assert snippet in dump
        assert snippet in typst_src
    pdf, stderr = compile_pdf(typst_src, tmp_path / "last")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_colophon_between_cover_and_annual_keeps_links(tmp_path):
    text = NOMAD.read_text(encoding="utf-8").replace(
        "section annual",
        "section colophon { }\n\nsection annual",
        1,
    )
    path = tmp_path / "mid.kdl"
    path.write_text(text, encoding="utf-8")
    dto = _attach(_short_january(load(path)), path)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[:3] == ["cover", "colophon", "annual"]
    typst_src = _generate(dto)
    labels = set(_LABEL_DEF.findall(typst_src))
    links = set(_PADDED_LINK.findall(typst_src))
    assert any(re.fullmatch(r"\d{4}-\d{2}-\d{2}", label) for label in labels)
    assert any(label.startswith("month-") for label in labels)
    assert links <= labels
    assert not any(target.startswith("colophon") for target in links)
    assert "padded_link(<colophon" not in typst_src
    pdf, stderr = compile_pdf(typst_src, tmp_path / "mid")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_no_padded_link_to_colophon_from_other_sections(tmp_path):
    text = NOMAD.read_text(encoding="utf-8").rstrip() + "\n\nsection colophon { }\n"
    path = tmp_path / "links.kdl"
    path.write_text(text, encoding="utf-8")
    typst_src = _generate(_attach(_short_january(load(path)), path))
    targets = _PADDED_LINK.findall(typst_src)
    assert targets
    assert all(not t.startswith("colophon") for t in targets)


def test_two_colophon_nodes_emit_two_pages(tmp_path):
    text = NOMAD.read_text(encoding="utf-8").rstrip() + (
        "\n\nsection colophon { }\nsection colophon { }\n"
    )
    path = tmp_path / "two.kdl"
    path.write_text(text, encoding="utf-8")
    typst_src = _generate(_attach(_short_january(load(path)), path))
    assert typst_src.count(DEFAULT_TITLE) == 2
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert typst_src.count(digest) == 2
    pdf, stderr = compile_pdf(typst_src, tmp_path / "two")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_generate_cmd_attaches_provenance(tmp_path, monkeypatch):
    from eink_planner.cli import generate_cmd

    path = tmp_path / "cli.kdl"
    path.write_text(_minimal(), encoding="utf-8")

    class _DummyCompile:
        def compile(self, workdir, file="index.typst", **_kwargs):
            pdf = Path(workdir) / "index.pdf"
            pdf.write_bytes(b"%PDF-dummy")
            return pdf

    monkeypatch.setattr("eink_planner.cli.Compile", lambda: _DummyCompile())
    ns = type(
        "Args",
        (),
        {
            "config": str(path),
            "workdir": str(tmp_path / "out"),
            "locale": "en",
            "i18n_path": None,
            "with_ghostscript": False,
            "debug": False,
        },
    )()
    assert generate_cmd(ns, argv=["lyp", "generate", str(path)]) == 0
    typst_src = (tmp_path / "out" / "index.typst").read_text(encoding="utf-8")
    assert hashlib.sha256(path.read_bytes()).hexdigest() in typst_src
    assert "lyp generate" in typst_src
    assert DEFAULT_TITLE in typst_src


def test_shipped_profiles_still_omit_colophon():
    for name in ("supernote-nomad.kdl", "kindle-scribe.kdl", "158x210-leftie.kdl"):
        dto = load(REPO / "configs" / name)
        names = [s["name"] for s in Configurator(dto).enabled_sections()]
        assert "colophon" not in names
