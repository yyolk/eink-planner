"""Colophon section: back-of-notebook about page, layout-agnostic."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from parch import ConfigError, __version__
from parch.config import StrictDict, load
from parch.mos.configurator import Configurator
from parch.provenance import apply_provenance, collect_provenance
from parch.sections.colophon import DEFAULT_TITLE, Colophon, drop_empty_tables
from parch.services.generate import Generate
from parch.toml_config import parse_toml
from tests.test_toml_omit_sections import (
    _LABEL_DEF,
    _PADDED_LINK,
    compile_pdf,
)
from tests.toml_fixtures import _minimal, short_january
from tests.helpers import base_config, load_default

REPO = Path(__file__).resolve().parents[1]
NOMAD = base_config("supernote-nomad")

_BUILD_LOG = ("Command", "Git commit", "SHA-256", "Config path", "Config")
_THEME = ('lang: "toml"', "syntaxes:", "theme:")


def _generate(dto: StrictDict) -> str:
    return Generate(i18n=load_default()).generate(dto)


def _attach(dto: StrictDict, path: Path, argv: list[str] | None = None) -> StrictDict:
    return apply_provenance(
        dto,
        collect_provenance(
            config_path=path,
            argv=argv or ["parch", "generate", str(path)],
            start=REPO,
        ),
    )


def _colo_kwargs(device: str | None = None, **prov) -> dict:
    data: dict = {}
    if device is not None:
        data["device"] = device
    if prov:
        data["planner"] = {"params": {"provenance": prov}}
    return {
        "section_name": "colophon",
        "i18n": load_default(),
        "configurator": Configurator(StrictDict(data) if data else StrictDict({})),
    }


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
    with pytest.raises(ConfigError, match="expected boolean"):
        parse_toml(
            _minimal(enable=["colophon"], sections="[section.colophon]\ncommand = \"parch\"\n"),
            source="command-key.toml",
        )


def test_multiple_colophon_nodes_parse_in_order():
    with pytest.raises(ConfigError, match="duplicate section: colophon"):
        parse_toml(
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


def test_colophon_is_raw_without_mos_chrome():
    colo = Colophon(section_name="colophon", i18n=load_default(), configurator=Configurator(StrictDict({})))
    pages = colo.pages(None)
    assert len(pages) == 1
    assert pages[0].raw_typst is True
    assert pages[0].page_id is None
    content = pages[0].content
    assert "Calendar" not in content
    assert "side_menu" not in content
    assert DEFAULT_TITLE in content
    assert "[*Device*]" in content
    assert "[*Year*]" in content
    assert "[*Version*]" in content
    for label in _BUILD_LOG:
        assert f"[*{label}*]" not in content


def test_default_page_is_device_year_version_only():
    colo = Colophon(**_colo_kwargs(device="supernote-nomad"))
    content = colo.pages(None)[0].content
    assert "[*Device*]" in content
    assert "SuperNote Nomad" in content
    assert "[*Year*]" in content
    assert "[*Version*]" in content
    assert __version__ in content
    for label in _BUILD_LOG:
        assert f"[*{label}*]" not in content
    for token in _THEME:
        assert token not in content
    assert "#raw(block: true" not in content
    assert "[section.colophon]" not in content
    assert "#block[" in content
    assert "rows: regular_height" in content
    assert "column-gutter: regular_column_gutter" in content
    assert 'measure(text(weight: "bold")[Version])' in content


def test_no_command_config_git_or_sha_on_default_page():
    dto = short_january(parse_toml(_minimal(enable=["colophon"], sections=""), source="inject.toml"))
    data = dto.to_plain()
    data["planner"]["params"]["provenance"] = {
        "command": "parch generate custom.toml --debug",
        "version": "9.9.9-test",
        "git_sha": "deadbeef" * 5,
        "config_path": "/tmp/custom.toml",
        "config_sha256": "abc123def456",
        "config_text": "[section.colophon]\ntrue = true\n",
    }
    typst_src = _generate(StrictDict(data))
    assert "parch generate custom.toml --debug" not in typst_src
    assert "deadbeef" not in typst_src
    assert "9.9.9-test" not in typst_src
    assert "abc123def456" not in typst_src
    assert "/tmp/custom.toml" not in typst_src
    assert "[section.colophon]" not in typst_src
    assert DEFAULT_TITLE in typst_src
    assert __version__ in typst_src
    for token in _THEME:
        assert token not in typst_src


def test_sha256_is_not_on_default_page(tmp_path):
    path = tmp_path / "plain.toml"
    path.write_text(_minimal(enable=["colophon"], sections=""), encoding="utf-8")
    dto = _attach(short_january(load(path)), path)
    typst_src = _generate(dto)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert expected not in typst_src
    assert "SHA-256" not in typst_src
    assert DEFAULT_TITLE in typst_src


def test_year_links_to_annual_when_registered(tmp_path):
    path = tmp_path / "year-link.toml"
    path.write_text(
        _minimal(
            enable=["cover", "annual", "colophon"],
            sections="""[section.cover]
title = "Hi"
font_size = "12pt"

[section.annual]
""",
        ),
        encoding="utf-8",
    )
    typst_src = _generate(_attach(short_january(load(path)), path))
    assert "padded_link(<annual>)[2026]" in typst_src
    assert "[*Year*]" in typst_src


def test_year_is_plain_text_when_annual_omitted(tmp_path):
    path = tmp_path / "no-annual.toml"
    path.write_text(_minimal(enable=["colophon"], sections=""), encoding="utf-8")
    typst_src = _generate(_attach(short_january(load(path)), path))
    assert "padded_link(<annual>)" not in typst_src
    assert "[*Year*], [2026]" in typst_src


def test_device_label_is_human_name():
    nomad = Colophon(**_colo_kwargs(device="supernote-nomad")).pages(None)[0].content
    assert "SuperNote Nomad" in nomad
    assert "supernote-nomad" not in nomad
    scribe = Colophon(**_colo_kwargs(device="kindle-scribe")).pages(None)[0].content
    assert "Kindle Scribe" in scribe
    assert "kindle-scribe" not in scribe


def test_colophon_between_cover_and_annual_keeps_links(tmp_path):
    text = _minimal(
        enable=["cover", "colophon", "annual"],
        device="""[device]
name = "supernote-nomad"
width = "118.87mm"
height = "158.5mm"
ppi = 300""",
        sections="""[section.cover]
title = "Hi"
font_size = "12pt"

[section.annual]
""",
    )
    path = tmp_path / "mid.toml"
    path.write_text(text, encoding="utf-8")
    dto = _attach(short_january(load(path)), path)
    names = [s["name"] for s in Configurator(dto).enabled_sections()]
    assert names[:3] == ["cover", "colophon", "annual"]
    typst_src = _generate(dto)
    labels = set(_LABEL_DEF.findall(typst_src))
    links = set(_PADDED_LINK.findall(typst_src))
    assert "annual" in labels
    assert links <= labels
    assert not any(target.startswith("colophon") for target in links)
    assert "padded_link(<colophon" not in typst_src
    pdf, stderr = compile_pdf(typst_src, tmp_path / "mid")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_no_padded_link_to_colophon_from_other_sections(tmp_path):
    path = tmp_path / "links.toml"
    path.write_text(NOMAD.read_text(encoding="utf-8"), encoding="utf-8")
    typst_src = _generate(_attach(short_january(load(path)), path))
    targets = _PADDED_LINK.findall(typst_src)
    assert targets
    # Contents rows may link to <colophon>; no other colophon-* targets.
    assert all(t == "colophon" or not t.startswith("colophon") for t in targets)
    assert "padded_link(<colophon>" in typst_src


def test_two_colophon_nodes_emit_two_pages(tmp_path):
    text = _minimal(
        enable=["cover", "colophon", "colophon"],
        sections="""[section.cover]
title = "Hi"
font_size = "12pt"

[[section.colophon]]

[[section.colophon]]
""",
    )
    path = tmp_path / "two.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError, match="duplicate section: colophon"):
        load(path)


def test_generate_cmd_attaches_provenance_but_page_stays_quiet(tmp_path, monkeypatch):
    from parch.cli import generate_cmd

    path = tmp_path / "cli.toml"
    path.write_text(_minimal(enable=["colophon"], sections=""), encoding="utf-8")

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
            "config": str(path),
            "workdir": str(tmp_path / "out"),
            "locale": "en",
            "with_ghostscript": False,
            "debug": False,
            "year": None,
        },
    )()
    assert generate_cmd(ns, argv=["parch", "generate", str(path)]) == 0
    typst_src = (tmp_path / "out" / "index.typst").read_text(encoding="utf-8")
    assert hashlib.sha256(path.read_bytes()).hexdigest() not in typst_src
    assert "parch generate" not in typst_src
    assert DEFAULT_TITLE in typst_src
    assert __version__ in typst_src


def test_shipped_profiles_include_colophon_where_shipped():
    include = {
        "supernote-nomad.toml",
        "supernote-nomad-mos-right.toml",
        "kindle-scribe.toml",
        "kindle-scribe-mos-right.toml",
        "158x210-mos-left.toml",
        "158x210-mos-left-lined.toml",
        "158x210-mos-right.toml",
        "158x210-mos-right-lined.toml",
    }
    for name in include:
        dto = load(base_config(name.removesuffix(".toml")))
        names = [s["name"] for s in Configurator(dto).enabled_sections()]
        assert names[-1] == "colophon", name


def _colophon_with_flags(
    dump: bool | None = None,
    command: bool | None = None,
    sha: bool | None = None,
    config_text: str = "year = 2026\n",
    device: str = "supernote-nomad",
    provenance: dict | None = None,
) -> Colophon:
    prov = {
        "command": "parch generate x.toml",
        "config_text": config_text,
        "config_sha256": "abc123def456",
    }
    if provenance is not None:
        prov.update(provenance)
    cfg = StrictDict(
        {
            "device": device,
            "planner": {
                "params": {
                    "start_date": "2026-01-01",
                    "provenance": prov,
                }
            },
        }
    )
    return Colophon(
        section_name="colophon",
        i18n=load_default(),
        configurator=Configurator(cfg),
        dump=dump,
        command=command,
        sha=sha,
    )


def _colophon_with_dump(
    dump: bool | None = True,
    config_text: str = "year = 2026\n",
    device: str = "supernote-nomad",
) -> Colophon:
    return _colophon_with_flags(dump=dump, config_text=config_text, device=device)


def test_colophon_dump_parses():
    dto = parse_toml(
        _minimal(enable=["colophon"], sections="[section.colophon]\ndump = true\n"),
        source="dump-true.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["dump"] is True
    dto = parse_toml(
        _minimal(enable=["colophon"], sections="[section.colophon]\ndump = false\n"),
        source="dump-false.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["dump"] is False


def test_colophon_dump_non_bool_rejected():
    with pytest.raises(ConfigError, match="expected boolean"):
        parse_toml(
            _minimal(enable=["colophon"], sections="[section.colophon]\ndump = 1\n"),
            source="dump-int.toml",
        )


def test_colophon_highlight_is_unknown_key():
    with pytest.raises(ConfigError, match="unknown key"):
        parse_toml(
            _minimal(enable=["colophon"], sections="[section.colophon]\nhighlight = true\n"),
            source="hl-gone.toml",
        )


def test_dump_absent_or_false_is_one_page_without_raw_config():
    for dump in (None, False):
        content = _colophon_with_dump(dump=dump).pages(None)[0].content
        assert "#raw(block: true" not in content
        assert "year = 2026" not in content
        for token in _THEME:
            assert token not in content
        assert "[*Device*]" in content
        assert "[*Year*]" in content
        assert "[*Version*]" in content


def test_dump_true_is_plain_raw_without_syntax_theme():
    content = _colophon_with_dump(dump=True).pages(None)[0].content
    assert "#raw(block: true," in content
    assert "year = 2026" in content
    for token in _THEME:
        assert token not in content
    assert "parch generate x.toml" not in content
    assert "[*Device*]" in content


def test_dump_true_drops_empty_section_colophon_table():
    dumped = "[calendar]\nyear = 2026\n\n[section.colophon]\n\n[section.cover]\ntitle = \"2026\"\n"
    content = _colophon_with_dump(dump=True, config_text=dumped).pages(None)[0].content
    assert "year = 2026" in content
    assert "[section.cover]" in content
    assert "[section.colophon]" not in content


def test_drop_empty_tables_helper():
    text = "[device]\nname = \"x\"\n\n[section.colophon]\n\n[section.cover]\ntitle = \"Hi\"\n"
    out = drop_empty_tables(text)
    assert "[section.colophon]" not in out
    assert "[device]" in out
    assert "[section.cover]" in out


def test_drop_empty_tables_keeps_quoted_and_dotted_keys():
    text = (
        '[a]\n"a b" = 1\n\n'
        "[b]\nfoo.bar = 1\n\n"
        "[empty]\n# comment only\n\n"
        "[c]\n'x y' = 2\n"
    )
    out = drop_empty_tables(text)
    assert "[a]" in out
    assert '"a b" = 1' in out
    assert "[b]" in out
    assert "foo.bar = 1" in out
    assert "[c]" in out
    assert "'x y' = 2" in out
    assert "[empty]" not in out


def test_two_dump_colophons_use_unique_start_and_end():
    a = _colophon_with_dump(dump=True)
    b = _colophon_with_dump(dump=True)
    ca = a.pages(None)[0].content
    cb = b.pages(None)[0].content
    assert a._dump_state_name() != b._dump_state_name()
    assert a._dump_end_label() != b._dump_end_label()
    assert a._dump_state_name() in ca
    assert a._dump_end_label() in ca
    assert b._dump_state_name() in cb
    assert b._dump_end_label() in cb
    assert a._dump_state_name() not in cb
    assert b._dump_state_name() not in ca
    assert "colophon-start\"" not in ca
    assert "<colophon-end>" not in ca
    assert "header:" in ca
    assert DEFAULT_TITLE in ca
    # continuation title + quiet 1/N stay in the header
    assert 'align(left, text(size: h1, weight: "bold")[' + DEFAULT_TITLE + "])" in ca
    assert "0.85em" in ca


def test_colophon_last_default_does_not_dump(tmp_path):
    path = tmp_path / "last.toml"
    path.write_text(NOMAD.read_text(encoding="utf-8"), encoding="utf-8")
    dto = _attach(short_january(load(path)), path)
    typst_src = _generate(dto)
    assert "SuperNote Nomad" in typst_src
    assert "[section.colophon]" not in typst_src
    assert hashlib.sha256(path.read_bytes()).hexdigest() not in typst_src
    for token in _THEME:
        assert token not in typst_src
    assert "Command" not in typst_src or "[*Command*]" not in typst_src
    pdf, stderr = compile_pdf(typst_src, tmp_path / "last")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr


def test_dump_true_compiles_without_syntax_theme(tmp_path):
    path = tmp_path / "dump-on.toml"
    path.write_text(
        _minimal(enable=["colophon"], sections="[section.colophon]\ndump = true\n"),
        encoding="utf-8",
    )
    dto = _attach(short_january(load(path)), path)
    typst_src = _generate(dto)
    assert "#raw(block: true," in typst_src
    for token in _THEME:
        assert token not in typst_src
    assert "[section.colophon]" not in typst_src or "dump = true" in typst_src
    # empty leftover table must not survive
    assert not re.search(r"\[section\.colophon\]\\n\\n", typst_src)
    pdf, stderr = compile_pdf(typst_src, tmp_path / "dump-on")
    assert pdf.is_file() and pdf.stat().st_size > 0, stderr

def test_colophon_command_parses():
    dto = parse_toml(
        _minimal(enable=["colophon"], sections="[section.colophon]\ncommand = true\n"),
        source="command-true.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["command"] is True
    dto = parse_toml(
        _minimal(enable=["colophon"], sections="[section.colophon]\ncommand = false\n"),
        source="command-false.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["command"] is False


def test_colophon_command_non_bool_rejected():
    with pytest.raises(ConfigError, match="expected boolean"):
        parse_toml(
            _minimal(enable=["colophon"], sections="[section.colophon]\ncommand = 1\n"),
            source="command-int.toml",
        )


def test_colophon_sha_parses():
    dto = parse_toml(
        _minimal(enable=["colophon"], sections="[section.colophon]\nsha = true\n"),
        source="sha-true.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["sha"] is True
    dto = parse_toml(
        _minimal(enable=["colophon"], sections="[section.colophon]\nsha = false\n"),
        source="sha-false.toml",
    )
    assert dto["planner"]["sections"][0]["params"]["sha"] is False


def test_colophon_sha_non_bool_rejected():
    with pytest.raises(ConfigError, match="expected boolean"):
        parse_toml(
            _minimal(enable=["colophon"], sections="[section.colophon]\nsha = 1\n"),
            source="sha-int.toml",
        )


def test_command_true_shows_command_row():
    content = _colophon_with_flags(command=True).pages(None)[0].content
    assert "[*Command*]" in content
    assert "parch generate x.toml" in content
    assert "[*SHA-256*]" not in content
    assert "#raw(block: true" not in content
    assert "colo-mono(" in content
    assert "DejaVu Sans Mono" in content
    assert "[*Device*]" in content
    assert "[*Year*]" in content
    assert "[*Version*]" in content


def test_sha_true_shows_sha_row():
    content = _colophon_with_flags(sha=True).pages(None)[0].content
    assert "[*SHA-256*]" in content
    assert "abc123def456" in content
    assert "[*Command*]" not in content
    assert "#raw(block: true" not in content
    assert "colo-mono(" in content
    assert "DejaVu Sans Mono" in content


def test_command_and_sha_join_same_grid_after_version():
    content = _colophon_with_flags(command=True, sha=True).pages(None)[0].content
    device = content.index("[*Device*]")
    year = content.index("[*Year*]")
    version = content.index("[*Version*]")
    command = content.index("[*Command*]")
    sha = content.index("[*SHA-256*]")
    assert device < year < version < command < sha
    assert "[*Git commit*]" not in content
    assert "[*Config*]" not in content
    assert "[*Config path*]" not in content
    for token in _THEME:
        assert token not in content


def test_command_true_missing_provenance_still_emits_empty_row():
    content = Colophon(
        section_name="colophon", i18n=load_default(), configurator=Configurator(StrictDict({})), command=True
    ).pages(None)[0].content
    assert "[*Command*]" in content
    assert "colo-mono(" in content


def test_sha_true_missing_provenance_still_emits_empty_row():
    content = Colophon(
        section_name="colophon", i18n=load_default(), configurator=Configurator(StrictDict({})), sha=True
    ).pages(None)[0].content
    assert "[*SHA-256*]" in content
    assert "colo-mono(" in content


def test_command_sha_dump_together():
    content = _colophon_with_flags(command=True, sha=True, dump=True).pages(None)[0].content
    assert "[*Command*]" in content
    assert "parch generate x.toml" in content
    assert "[*SHA-256*]" in content
    assert "abc123def456" in content
    assert "#raw(block: true," in content
    assert "year = 2026" in content
    for token in _THEME:
        assert token not in content
    assert "header:" in content
    assert DEFAULT_TITLE in content


def test_default_still_omits_command_sha_dump():
    content = _colophon_with_flags().pages(None)[0].content
    assert "[*Command*]" not in content
    assert "[*SHA-256*]" not in content
    assert "parch generate x.toml" not in content
    assert "abc123def456" not in content
    assert "#raw(block: true" not in content
    assert "colo-mono(" not in content
    assert "[*Device*]" in content
    assert "[*Year*]" in content
    assert "[*Version*]" in content


def test_default_composition_is_one_block_on_house_pitch():
    content = Colophon(**_colo_kwargs(device="supernote-nomad")).pages(None)[0].content
    assert "#block[" in content
    assert "#v(1em)" in content
    assert "rows: regular_height" in content
    assert "column-gutter: regular_column_gutter" in content
    assert 'measure(text(weight: "bold")[Version])' in content
    assert "align: horizon" in content
    assert "column-gutter: 1em" not in content
    assert "row-gutter:" not in content
    assert "#v(1.4em)" not in content
    assert "colo-label-width" not in content
    assert "colo-mono(" not in content


def test_scribe_uses_same_title_facts_gap_and_row_pitch():
    nomad = Colophon(**_colo_kwargs(device="supernote-nomad")).pages(None)[0].content
    scribe = Colophon(**_colo_kwargs(device="kindle-scribe")).pages(None)[0].content
    assert "#v(1em)" in nomad
    assert "#v(1em)" in scribe
    assert "#v(1.4em)" not in scribe
    assert "0.85em" not in scribe
    assert "0.6em" not in scribe
    assert "rows: regular_height" in scribe
    assert "column-gutter: regular_column_gutter" in scribe
    assert 'measure(text(weight: "bold")[Version])' in scribe
    assert "#block[" in scribe


def test_sha_widens_label_column_to_longest_enabled_label():
    content = _colophon_with_flags(sha=True).pages(None)[0].content
    assert "colo-label-width" in content
    assert "calc.max" in content
    assert 'measure(text(weight: "bold")[Version])' in content
    assert 'measure(text(weight: "bold")[SHA-256])' in content
    assert "columns: (colo-label-width, 1fr)" in content
    assert "rows: regular_height" in content
    assert "column-gutter: regular_column_gutter" in content


def test_command_uses_same_label_rail():
    content = _colophon_with_flags(command=True).pages(None)[0].content
    assert "colo-label-width" in content
    assert 'measure(text(weight: "bold")[Command])' in content
    assert 'measure(text(weight: "bold")[Version])' in content
    assert "columns: (colo-label-width, 1fr)" in content
