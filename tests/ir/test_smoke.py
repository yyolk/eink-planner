from parch.config import load
from parch.i18n import I18n
from parch.ir.mos import build_planner
from parch.ir.typst import render_typst
from tests.helpers import base_config
from tests.toml_fixtures import short_january


def test_build_planner_and_render_typst_short_january():
    dto = short_january(load(base_config("supernote-nomad")))
    doc = build_planner(dto, I18n.load_default())
    src = render_typst(doc)
    assert src.count("#pagebreak()") == len(doc.pages) - 1
    assert "padded_link" in src
    assert "<annual>" in src
    assert "scratch_pad" in src
    assert "#set page" in src
    ids = [p.id for p in doc.pages]
    assert ids[0] is None
    assert "annual" in ids
    assert "month-2026-01-01" in ids
    assert "2026-01-01" in ids
