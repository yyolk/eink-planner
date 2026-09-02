from pathlib import Path

import pytest
from pypdf import PdfReader

from parch.services.compile import Compile, typst_py_available
from parch.services.merge import merge_pdfs, named_dest_pages

REPO = Path(__file__).resolve().parents[1]

# Typst 0.15 writes /Names /Dests for labelled headings, not #[] <label>.
_A = """#set page(width: 80pt, height: 100pt)
#heading[] <week-a>
#pagebreak()
#heading[] <week-b>
"""

_B = """#set page(width: 80pt, height: 100pt)
#heading[] <week-b>
#pagebreak()
#heading[] <week-a>
"""


def _compile(monkeypatch, workdir: Path, src: str) -> Path:
    monkeypatch.setenv("PARCH_TYPST", "py")
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "index.typst").write_text(src, encoding="utf-8")
    return Compile().compile(workdir, tools_dir=REPO / ".tools")


@pytest.mark.skipif(not typst_py_available(), reason="typst extra not installed")
def test_merge_unions_named_dests_after_dropping_dest_tables(monkeypatch, tmp_path):
    pdf_a = _compile(monkeypatch, tmp_path / "a", _A)
    pdf_b = _compile(monkeypatch, tmp_path / "b", _B)
    assert named_dest_pages(pdf_a) == {"week-a": 1, "week-b": 2}
    assert named_dest_pages(pdf_b) == {"week-b": 1, "week-a": 2}

    merged = merge_pdfs([pdf_a, pdf_b], tmp_path / "merged.pdf", drop_pages=[{2}, {2}])
    assert len(PdfReader(str(merged)).pages) == 2
    assert named_dest_pages(merged) == {"week-a": 1, "week-b": 2}
