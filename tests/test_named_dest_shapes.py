"""Measure which Typst label shapes write PDF named dests."""

from pathlib import Path

import pytest
from pypdf import PdfReader

from parch.services.compile import Compile, typst_py_available
from parch.services.merge import merge_pdfs, named_dest_pages

REPO = Path(__file__).resolve().parents[1]

# Tiny page + the house h1 token live titles interpolate.
_PAGE = """#set page(width: 80pt, height: 100pt)
#let h1 = 14pt
"""

# Bare content dest: tasks/projects/meetings boards (sections/tasks.py _week_page).
_BARE = "#[] <week-a>\n"

# Live week title: sections/weekly.py _title — label inside text(), not after it.
#   text(size: h1)[{week_name} {number} <{week.id}> #h(0.6em) {rng}]
# MOS weekly.py title() is the same shape without the range helper.
_LIVE = "#text(size: h1)[Week 1 <week-a> #h(0.6em) Jan 1 – 7]\n"

# Known-good control from the #153 merge probe.
_HEADING = "#heading[] <week-a>\n"

# Gridwright remedy: hidden heading next to a visible title (no outline, no ink).
_HIDDEN = """#heading(outlined: false)[] <week-a>
#text(size: h1)[Week 1]
"""

_LIVE_A = _PAGE + """#text(size: h1)[Week 1 <week-a> #h(0.6em) Jan 1 – 7]
#pagebreak()
#text(size: h1)[Week 2 <week-b> #h(0.6em) Jan 8 – 14]
"""

_LIVE_B = _PAGE + """#text(size: h1)[Week 2 <week-b> #h(0.6em) Jan 8 – 14]
#pagebreak()
#text(size: h1)[Week 1 <week-a> #h(0.6em) Jan 1 – 7]
"""

_HIDDEN_A = _PAGE + """#heading(outlined: false)[] <week-a>
#text(size: h1)[Week 1]
#pagebreak()
#heading(outlined: false)[] <week-b>
"""

_HIDDEN_B = _PAGE + """#heading(outlined: false)[] <week-b>
#text(size: h1)[Week 2]
#pagebreak()
#heading(outlined: false)[] <week-a>
"""


def _compile(monkeypatch, workdir: Path, src: str) -> Path:
    """Compile a tiny Typst doc with the in-process backend."""
    monkeypatch.setenv("PARCH_TYPST", "py")
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "index.typst").write_text(src, encoding="utf-8")
    return Compile().compile(workdir, tools_dir=REPO / ".tools")


@pytest.mark.skipif(not typst_py_available(), reason="typst extra not installed")
@pytest.mark.parametrize(
    "src,present",
    [
        (_BARE, False),
        (_LIVE, False),
        (_HEADING, True),
        (_HIDDEN, True),
    ],
    ids=["bare_content", "live_title", "heading", "hidden_heading"],
)
def test_label_shape_named_dest(monkeypatch, tmp_path, src, present):
    """Typst 0.15 writes /Names /Dests only for labelled headings."""
    pdf = _compile(monkeypatch, tmp_path / "shape", _PAGE + src)
    dests = named_dest_pages(pdf)
    if present:
        assert dests == {"week-a": 1}
    else:
        assert "week-a" not in dests


@pytest.mark.skipif(not typst_py_available(), reason="typst extra not installed")
def test_live_title_merge_cannot_keep_owning_dests(monkeypatch, tmp_path):
    """Live text titles write no dests, so merge+drop has nothing to union."""
    pdf_a = _compile(monkeypatch, tmp_path / "a", _LIVE_A)
    pdf_b = _compile(monkeypatch, tmp_path / "b", _LIVE_B)
    assert named_dest_pages(pdf_a) == {}
    assert named_dest_pages(pdf_b) == {}

    merged = merge_pdfs([pdf_a, pdf_b], tmp_path / "merged.pdf", drop_pages=[{2}, {2}])
    assert len(PdfReader(str(merged)).pages) == 2
    assert named_dest_pages(merged) == {}


@pytest.mark.skipif(not typst_py_available(), reason="typst extra not installed")
def test_hidden_heading_merge_keeps_owning_pages(monkeypatch, tmp_path):
    """Hidden heading dests union after dest-table drop; owning section wins."""
    pdf_a = _compile(monkeypatch, tmp_path / "a", _HIDDEN_A)
    pdf_b = _compile(monkeypatch, tmp_path / "b", _HIDDEN_B)
    assert named_dest_pages(pdf_a) == {"week-a": 1, "week-b": 2}
    assert named_dest_pages(pdf_b) == {"week-b": 1, "week-a": 2}

    merged = merge_pdfs([pdf_a, pdf_b], tmp_path / "merged.pdf", drop_pages=[{2}, {2}])
    assert len(PdfReader(str(merged)).pages) == 2
    assert named_dest_pages(merged) == {"week-a": 1, "week-b": 2}
