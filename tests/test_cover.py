"""Unit tests for the raw Typst cover page."""

from __future__ import annotations

from parch.sections.cover_plain import CoverPlain
from tests.helpers import compose_ctx


def _typst(name: str, font_size: str = "36pt") -> str:
    pages = CoverPlain("cover", compose_ctx(), name, font_size).pages(None)
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
