from parch.config import load
from parch.i18n import I18n
from parch.ir.mos import build_planner
from parch.ir.nodes import Anchor, Link, collect_anchors, collect_links, walk
from tests.helpers import base_config
from tests.toml_fixtures import short_january


def _short_dto():
    return short_january(load(base_config("supernote-nomad")))


def _i18n() -> I18n:
    return I18n.load_default()


def test_cover_and_january_tree_has_anchors_and_links():
    doc = build_planner(_short_dto(), _i18n())
    assert doc.pages[0].chrome is False
    assert doc.pages[0].id is None
    assert doc.pages[1].id == "annual"
    assert doc.pages[1].chrome is True

    jan = next(p for p in doc.pages if p.id == "month-2026-01-01")
    anchors = set(collect_anchors(jan.body))
    links = set(collect_links(jan.body))
    assert "month-2026-01-01" in anchors
    assert "annual" in links
    assert "2026-01-01" in links
    assert "2026W01" in links
    assert any(isinstance(n, Anchor) and n.id == "month-2026-01-01" for n in walk(jan.body))
    assert any(isinstance(n, Link) and n.target_id == "annual" for n in walk(jan.body))


def test_short_january_emits_core_mos_pages():
    doc = build_planner(_short_dto(), _i18n())
    ids = [p.id for p in doc.pages]
    assert ids[0] is None
    assert ids[1] == "annual"
    assert "quarter-2026-1" in ids
    assert "month-2026-01-01" in ids
    assert "2026W01" in ids
    assert "2026-01-01" in ids
    assert "2026-01-14" in ids
    assert "daily-note-2026-01-01-page-1" in ids
    assert "daily-note-2026-01-01-page-2" in ids
    # extra Nomad sections are skipped
    assert "index" not in ids
    assert not any(i and str(i).startswith("project") for i in ids)
    # cover + annual + Q1 + January + 5 weeks + 14 days + 28 notes
    assert len(doc.pages) == 1 + 1 + 1 + 1 + 5 + 14 + 28


def test_full_nomad_plan_has_1166_core_pages():
    dto = load(base_config("supernote-nomad"))
    doc = build_planner(dto, _i18n())
    assert len(doc.pages) == 1166
    assert doc.pages[0].chrome is False
    assert doc.pages[1].id == "annual"
    assert doc.pages[6].id == "month-2026-01-01"
    assert doc.manifest.source("annual")
    assert doc.manifest.source("2026-12-31")
