"""Colophon section: provenance page, layout-agnostic."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.config import StrictDict, load
from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.provenance import apply_provenance, collect_provenance
from eink_planner.sections.colophon import DEFAULT_TITLE, Colophon
from eink_planner.services.generate import Generate
from eink_planner.toml_config import parse_toml
from tests.test_toml_omit_sections import (
    _LABEL_DEF,
    _PADDED_LINK,
    compile_pdf,
)
from tests.toml_fixtures import _minimal, add_toml_section, short_january

REPO = Path(__file__).resolve().parents[1]
NOMAD = REPO / "configs/supernote-nomad.toml"


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
    dto = parse_toml(_minimal(enable=["colophon"], sections=""), source="empty-colophon.toml")
    sections = dto["planner"]["sections"]
    assert len(sections) == 1
    assert sections[0]["name"] == "colophon"
    assert sections[0]["class"] == "colophon"
    assert sections[0]["enabled"] is True
    assert sections[0]["params"].to_plain() == {}


def test_colophon_optional_title():
    dto = parse_toml(
        _minimal(enable=["colophon"], sections='[section.colophon]\ntitle = "Provenance"\n'),
        source="titled.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["title"] == "Provenance"


def test_colophon_rejects_unknown_children():
    with pytest.raises(ConfigError, match="unknown key"):
        parse_toml(
            _minimal(enable=["colophon"], sections="[section.colophon]\ngit = \"abcdef\"\n"),
            source="git-key.toml",
        )
    with pytest.raises(ConfigError, match="unknown key"):
        parse_toml(
            _minimal(enable=["colophon"], sections="[section.colophon]\ncommand = \"lyp\"\n"),
            source="command-key.toml",
        )


def test_multiple_colophon_nodes_parse_in_order():
    dto = parse_toml(
        _minimal(
            enable=["cover", "colophon", "colophon"],
            sections="""[section.cover]
title = "Hi"
font_size = "12pt"

[[section.colophon]]

[[section.colophon]]
title = "Again"
""",
        ),
        source="two-colo.toml",
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
    dto = short_january(parse_toml(_minimal(enable=["colophon"], sections=""), source="inject.toml"))
    data = dto.to_plain()
    data["planner"]["params"]["provenance"] = {
        "command": "lyp generate custom.toml --debug",
        "version": "9.9.9-test",
        "git_sha": "deadbeef" * 5,
        "config_path": "/tmp/custom.toml",
        "config_sha256": "abc123def456",
        "config_text": "[section.colophon]\ntrue = true\n",
    }
    typst_src = _generate(StrictDict(data))
    assert "lyp generate custom.toml --debug" in typst_src
    assert "deadbeef" * 5 in typst_src
    assert "9.9.9-test" in typst_src
    assert "abc123def456" in typst_src
    assert "/tmp/custom.toml" in typst_src
    assert "[section.colophon]" in typst_src
    assert DEFAULT_TITLE in typst_src


def test_sha256_matches_hashlib_of_file_bytes(tmp_path):
    path = tmp_path / "plain.toml"
    path.write_text(_minimal(enable=["colophon"], sections=""), encoding="utf-8")
    dto = _attach(short_january(load(path)), path)
    typst_src = _generate(dto)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert expected in typst_src
    assert expected == hashlib.sha256(path.read_bytes()).hexdigest()


def test_colophon_last_dumps_config_and_compiles(tmp_path):
    text = add_toml_section(NOMAD.read_text(encoding="utf-8"), "colophon")
    path = tmp_path / "last.toml"
    path.write_text(text, encoding="utf-8")
    dto = _attach(short_january(load(path)), path)
    typst_src = _generate(dto)
    dump = path.read_text(encoding="utf-8")
    assert "supernote-nomad" in typst_src
    assert "[section.colophon]" in typst_src
    assert hashlib.sha256(path.read_bytes()).hexdigest() in typst_src
    for snippet in ("year = 2026", "week_starts", "Monday", "reverse_months_quarters"):
        assert snippet in dump
        assert snippet in typst_src
    pdf, stderr = compile_pdf(typst_src, tmp_path / "last")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_colophon_between_cover_and_annual_keeps_links(tmp_path):
    text = add_toml_section(NOMAD.read_text(encoding="utf-8"), "colophon", before="annual")
    path = tmp_path / "mid.toml"
    path.write_text(text, encoding="utf-8")
    dto = _attach(short_january(load(path)), path)
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
    text = add_toml_section(NOMAD.read_text(encoding="utf-8"), "colophon")
    path = tmp_path / "links.toml"
    path.write_text(text, encoding="utf-8")
    typst_src = _generate(_attach(short_january(load(path)), path))
    targets = _PADDED_LINK.findall(typst_src)
    assert targets
    assert all(not t.startswith("colophon") for t in targets)


def test_two_colophon_nodes_emit_two_pages(tmp_path):
    text = add_toml_section(NOMAD.read_text(encoding="utf-8"), "colophon")
    text = add_toml_section(text, "colophon", table=False)
    path = tmp_path / "two.toml"
    path.write_text(text, encoding="utf-8")
    typst_src = _generate(_attach(short_january(load(path)), path))
    assert typst_src.count(DEFAULT_TITLE) == 2
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert typst_src.count(digest) == 2
    pdf, stderr = compile_pdf(typst_src, tmp_path / "two")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_generate_cmd_attaches_provenance(tmp_path, monkeypatch):
    from eink_planner.cli import generate_cmd

    path = tmp_path / "cli.toml"
    path.write_text(_minimal(enable=["colophon"], sections=""), encoding="utf-8")

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
            "with_ghostscript": False,
            "debug": False,
            "year": None,
        },
    )()
    assert generate_cmd(ns, argv=["lyp", "generate", str(path)]) == 0
    typst_src = (tmp_path / "out" / "index.typst").read_text(encoding="utf-8")
    assert hashlib.sha256(path.read_bytes()).hexdigest() in typst_src
    assert "lyp generate" in typst_src
    assert DEFAULT_TITLE in typst_src


def test_shipped_profiles_still_omit_colophon():
    for name in (
        "supernote-nomad.toml",
        "supernote-nomad-mos-right.toml",
        "kindle-scribe.toml",
        "158x210-mos-left.toml",
        "158x210-mos-left-lined.toml",
        "158x210-mos-right.toml",
    ):
        dto = load(REPO / "configs" / name)
        names = [s["name"] for s in Configurator(dto).enabled_sections()]
        assert "colophon" not in names


def _colophon_with_dump(highlight: bool | None = None, config_text: str = "year = 2026\n") -> Colophon:
    cfg = StrictDict(
        {
            "planner": {
                "params": {
                    "provenance": {
                        "command": "lyp generate x.toml",
                        "config_text": config_text,
                    }
                }
            }
        }
    )
    kwargs = {} if highlight is None else {"highlight": highlight}
    return Colophon(section_name="colophon", configurator=cfg, **kwargs)


def test_colophon_highlight_false_parses():
    dto = parse_toml(
        _minimal(enable=["colophon"], sections="[section.colophon]\nhighlight = false\n"),
        source="hl-false.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["highlight"] is False


def test_colophon_highlight_true_parses():
    dto = parse_toml(
        _minimal(enable=["colophon"], sections="[section.colophon]\nhighlight = true\n"),
        source="hl-true.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["highlight"] is True


def test_colophon_highlight_non_bool_rejected():
    with pytest.raises(ConfigError, match="expected boolean"):
        parse_toml(
            _minimal(enable=["colophon"], sections="[section.colophon]\nhighlight = 1\n"),
            source="hl-int.toml",
        )
    with pytest.raises(ConfigError, match="expected boolean"):
        parse_toml(
            _minimal(enable=["colophon"], sections='[section.colophon]\nhighlight = "no"\n'),
            source="hl-str.toml",
        )


def test_colophon_highlight_on_emits_toml_syntax():
    on = _colophon_with_dump(highlight=True).pages(None)[0].content
    default = _colophon_with_dump().pages(None)[0].content
    for content in (on, default):
        assert 'lang: "toml"' in content
        assert "syntaxes:" in content
        assert "theme:" in content
        assert "#raw(block: true, lang:" in content


def test_colophon_highlight_off_emits_plain_raw():
    content = _colophon_with_dump(highlight=False).pages(None)[0].content
    assert "#raw(block: true," in content
    assert 'lang: "toml"' not in content
    assert "syntaxes:" not in content
    assert "theme:" not in content
    assert f'#raw("{DEFAULT_TITLE}")' in content
    assert 'raw("lyp generate x.toml")' in content


def test_colophon_highlight_on_compiles(tmp_path):
    path = tmp_path / "hl-on.toml"
    path.write_text(_minimal(enable=["colophon"], sections=""), encoding="utf-8")
    dto = _attach(short_january(load(path)), path)
    typst_src = _generate(dto)
    assert 'lang: "toml"' in typst_src
    assert "syntaxes:" in typst_src
    pdf, stderr = compile_pdf(typst_src, tmp_path / "hl-on")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_colophon_highlight_false_compiles(tmp_path):
    path = tmp_path / "hl-off.toml"
    path.write_text(
        _minimal(enable=["colophon"], sections="[section.colophon]\nhighlight = false\n"),
        encoding="utf-8",
    )
    dto = _attach(short_january(load(path)), path)
    typst_src = _generate(dto)
    assert 'lang: "toml"' not in typst_src
    assert "syntaxes:" not in typst_src
    pdf, stderr = compile_pdf(typst_src, tmp_path / "hl-off")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr
