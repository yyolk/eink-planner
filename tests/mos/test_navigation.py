from eink_planner.config import StrictDict
from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.mos.manifest import Manifest
from eink_planner.mos.navigation import Navigation
from eink_planner.mos.sections.annual import Annual


def _i18n() -> I18n:
    return I18n(
        {
            "en": {
                "quarters": {"short": "Q"},
                "months": {
                    "short": {
                        "january": "Jan",
                        "february": "Feb",
                        "march": "Mar",
                        "april": "Apr",
                        "may": "May",
                        "june": "Jun",
                        "july": "Jul",
                        "august": "Aug",
                        "september": "Sep",
                        "october": "Oct",
                        "november": "Nov",
                        "december": "Dec",
                    }
                },
            }
        },
        locale="en",
    )


def _nav(reverse: bool = False) -> Navigation:
    dto = StrictDict(
        {
            "planner": {
                "params": {
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "weekday_start": "Monday",
                    "mos_layout": {
                        "menu_rotate": "270deg",
                        "reverse_months_quarters": reverse,
                        "reverse_months_quarters_items": False,
                    },
                    "heading": {"height": "10mm"},
                }
            }
        }
    )
    return Navigation(i18n=_i18n(), manifest=Manifest(), configurator=Configurator(dto))


def test_side_menu_default_quarters_then_months():
    typst = _nav(reverse=False).side_menu_cell(highlight_months=[], highlight_quarters=[])
    assert "rotate(" in typst
    assert "270deg" in typst
    assert "columns: (1fr, 3fr)" in typst
    # Q cells appear before month cells in default order
    assert typst.index("Q1") < typst.index("Jan")


def test_side_menu_reversed_months_then_quarters():
    typst = _nav(reverse=True).side_menu_cell(highlight_months=[], highlight_quarters=[])
    assert "columns: (3fr, 1fr)" in typst
    assert typst.index("Jan") < typst.index("Q1")


def test_heading_menu_omitted_when_annual_unregistered():
    nav = _nav()
    assert nav.heading_menu_grid(page_id="monthly-2026-01") is None


def test_heading_menu_highlights_annual_page():
    nav = _nav()
    nav.manifest.register_source(Annual.ID)
    on_annual = nav.heading_menu_grid(page_id=Annual.ID)
    assert on_annual is not None
    assert "grid.cell(fill: black, text(white)[#padded_link(<annual>, [Calendar])])" in on_annual
    other = nav.heading_menu_grid(page_id="monthly-2026-01")
    assert other is not None
    assert "padded_link(<annual>, [Calendar])" in other
    assert "fill: black" not in other
