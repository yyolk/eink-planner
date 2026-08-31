"""Unit tests for the raw Typst cover page."""

from parch.config import StrictDict
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.sections.cover_plain import CoverPlain
from tests.helpers import load_default


def _typst(name: str, font_size: str = "36pt", manifest=None) -> str:
    pages = CoverPlain(
        "cover",
        i18n=load_default(),
        configurator=Configurator(StrictDict({})),
        name=name,
        font_size=font_size,
    ).pages(manifest)
    assert len(pages) == 1
    assert pages[0].raw_typst is True
    return pages[0].content


def test_single_line_year_sits_in_upper_third():
    typst = _typst("2026")
    assert "rows: (1fr, 2fr)" in typst
    assert "text(size: 36pt)[2026]" in typst
    assert " \\ " not in typst
    assert "Planner" not in typst
    assert "link(" not in typst


def test_blank_lines_collapse_to_tight_stack():
    typst = _typst("2026\n\nPlanner")
    assert "stack(spacing: 36pt * 0.12," in typst
    assert "text(size: 36pt)[2026]" in typst
    assert "text(size: 36pt * 0.45)[Planner]" in typst
    assert " \\ " not in typst
    assert "link(" not in typst


def test_empty_name_is_empty_cell():
    typst = _typst("")
    assert "rows: (1fr, 2fr)" in typst
    assert "[]" in typst
    assert "text(" not in typst


def test_empty_manifest_stays_unlinked():
    typst = _typst("2026", manifest=Manifest())
    assert "text(size: 36pt)[2026]" in typst
    assert "padded_link" not in typst
    assert "link(" not in typst


def test_year_taps_index_when_registered():
    manifest = Manifest()
    manifest.register_source("index")
    typst = _typst("2026", manifest=manifest)
    assert "padded_link(<index>)[2026]" in typst
    assert "text(size: 36pt, padded_link(<index>)[2026])" in typst
    assert "padded_link(<annual>)" not in typst


def test_year_prefers_index_when_both_registered():
    manifest = Manifest()
    manifest.register_source("index")
    manifest.register_source("annual")
    typst = _typst("2026", manifest=manifest)
    assert "padded_link(<index>)[2026]" in typst
    assert "padded_link(<annual>)" not in typst


def test_year_taps_annual_when_index_absent():
    manifest = Manifest()
    manifest.register_source("annual")
    typst = _typst("2026", manifest=manifest)
    assert "padded_link(<annual>)[2026]" in typst
    assert "text(size: 36pt, padded_link(<annual>)[2026])" in typst
    assert "padded_link(<index>)" not in typst


def test_only_first_line_is_the_door():
    manifest = Manifest()
    manifest.register_source("index")
    typst = _typst("2026\n\nPlanner", manifest=manifest)
    assert "text(size: 36pt, padded_link(<index>)[2026])" in typst
    assert "text(size: 36pt * 0.45)[Planner]" in typst
    assert "padded_link(<index>)[Planner]" not in typst
