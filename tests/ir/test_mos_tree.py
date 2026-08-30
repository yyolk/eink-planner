from parch.config import StrictDict, load
from parch.i18n import I18n
from parch.ir.mos import build_planner
from parch.ir.nodes import Anchor, Link, Text, collect_anchors, collect_links, walk
from parch.compose.coordinator import Coordinator
from tests.helpers import base_config
from tests.toml_fixtures import short_january


def _short_dto():
    return short_january(load(base_config("supernote-nomad")))


def _i18n() -> I18n:
    return I18n.load_default()


def _string_page_count(dto, i18n: I18n) -> int:
    return sum(len(pages) for _name, pages in Coordinator(dto, i18n).section_pages())


def test_cover_and_january_tree_has_anchors_and_links():
    doc = build_planner(_short_dto(), _i18n())
    assert doc.pages[0].chrome is False
    assert doc.pages[0].id is None
    assert doc.pages[1].id == "index"
    assert doc.pages[1].chrome is False
    annual = next(p for p in doc.pages if p.id == "annual")
    assert annual.chrome is True

    jan = next(p for p in doc.pages if p.id == "month-2026-01-01")
    anchors = set(collect_anchors(jan.body))
    links = set(collect_links(jan.body))
    assert "month-2026-01-01" in anchors
    assert "annual" in links
    assert "2026-01-01" in links
    assert "2026W01" in links
    assert any(isinstance(n, Anchor) and n.id == "month-2026-01-01" for n in walk(jan.body))
    assert any(isinstance(n, Link) and n.target_id == "annual" for n in walk(jan.body))


def test_short_january_includes_enabled_nomad_sections():
    dto = _short_dto()
    i18n = _i18n()
    doc = build_planner(dto, i18n)
    ids = [p.id for p in doc.pages]
    assert ids[0] is None
    assert "index" in ids
    assert "annual" in ids
    assert "quarter-2026-1" in ids
    assert "month-2026-01-01" in ids
    assert "2026W01" in ids
    assert "2026-01-01" in ids
    assert "2026-01-14" in ids
    assert "daily-note-2026-01-01-page-1" in ids
    assert "projects" in ids
    assert any(i and str(i).startswith("project-") for i in ids)
    assert "habits" in ids
    assert "habits-january" in ids
    assert "review" in ids
    assert "tasks" in ids
    assert "meetings" in ids
    assert ids[-1] == "colophon"
    assert len(doc.pages) == _string_page_count(dto, i18n)


def test_full_nomad_plan_page_count_matches_string_mos():
    dto = load(base_config("supernote-nomad"))
    i18n = _i18n()
    doc = build_planner(dto, i18n)
    expected = _string_page_count(dto, i18n)
    assert len(doc.pages) == expected
    assert expected > 1166
    assert doc.pages[0].chrome is False
    assert doc.pages[-1].id == "colophon"
    assert doc.manifest.source("annual")
    assert doc.manifest.source("2026-12-31")


def test_nomad_registers_extra_sections_and_chrome_flags():
    dto = load(base_config("supernote-nomad"))
    doc = build_planner(dto, _i18n())
    for name in ("index", "tasks", "colophon", "habits", "meetings", "review", "projects"):
        assert name in doc.manifest.sections()
        assert doc.manifest.source(name)
        page = next(p for p in doc.pages if p.id == name)
        assert page is not None
        assert page.chrome is False
    habit_months = [p for p in doc.pages if p.id and str(p.id).startswith("habits-")]
    assert habit_months
    assert all(p.chrome is True for p in habit_months)
    raw_ids = (
        "index",
        "projects",
        "habits",
        "review",
        "tasks",
        "meetings",
        "colophon",
    )
    for page in doc.pages:
        if page.id in raw_ids or (
            page.id
            and (
                str(page.id).startswith("project-")
                or str(page.id).startswith("projects-")
                or str(page.id).startswith("review-")
                or str(page.id).startswith("tasks-")
                or str(page.id).startswith("meeting-")
                or str(page.id).startswith("meetings-")
            )
        ):
            assert page.chrome is False, page.id

def _cover_links(doc):
    return [n.target_id for n in walk(doc.pages[0].body) if isinstance(n, Link)]


def _omit(dto, *names):
    data = dto.to_plain()
    for section in data["planner"]["sections"]:
        if section["name"] in names:
            section["enabled"] = False
    return StrictDict(data)


def test_cover_year_taps_index_when_present():
    doc = build_planner(_short_dto(), _i18n())
    assert _cover_links(doc) == ["index"]
    year = next(n for n in walk(doc.pages[0].body) if isinstance(n, Link))
    assert isinstance(year.child, Text) and year.child.text == "2026"


def test_cover_year_taps_annual_when_index_absent():
    doc = build_planner(_omit(_short_dto(), "index"), _i18n())
    assert _cover_links(doc) == ["annual"]


def test_cover_year_stays_plain_without_doors():
    doc = build_planner(_omit(_short_dto(), "index", "annual"), _i18n())
    assert _cover_links(doc) == []
    assert any(isinstance(n, Text) and n.text == "2026" for n in walk(doc.pages[0].body))


def test_cover_only_first_line_is_the_door():
    data = _short_dto().to_plain()
    data["planner"]["sections"][0]["params"]["name"] = "2026\n\nPlanner"
    doc = build_planner(StrictDict(data), _i18n())
    links = [n for n in walk(doc.pages[0].body) if isinstance(n, Link)]
    assert len(links) == 1
    assert links[0].target_id == "index"
    assert isinstance(links[0].child, Text) and links[0].child.text == "2026"
    assert any(isinstance(n, Text) and n.text == "Planner" for n in walk(doc.pages[0].body))
