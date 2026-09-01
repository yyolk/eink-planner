from parch.config import StrictDict
from parch.i18n import I18n
from parch.mos.components.months_menu import MonthsMenu
from parch.mos.components.quarters_menu import QuartersMenu
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.mos.navigation import Navigation
from parch.sections.annual import Annual
from tests.helpers import make_month, make_quarter


def _i18n() -> I18n:
    return I18n(
        {
            "en": {
                "quarter": {"short": "Q"},
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
    assert "mos_tabs(columns: (" in typst
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
    links = [(Annual.ID, "Calendar")]
    on_annual = nav.heading_menu_grid(page_id=Annual.ID, nav_links=links)
    assert on_annual is not None
    assert "grid.cell(fill: black, text(white)[#padded_link(<annual>, [Calendar])])" in on_annual
    other = nav.heading_menu_grid(page_id="monthly-2026-01", nav_links=links)
    assert other is not None
    assert "padded_link(<annual>, [Calendar])" in other
    assert "fill: black" not in other


def test_heading_menu_omitted_nav_links_is_no_chip_when_annual_registered():
    nav = _nav()
    nav.manifest.register_source(Annual.ID)
    assert nav.heading_menu_grid(page_id=Annual.ID) is None
    assert nav.heading_menu_grid(page_id="monthly-2026-01") is None
    assert nav.heading_menu_grid(page_id=Annual.ID, nav_links=[]) is None


def test_heading_menu_uses_page_nav_links():
    nav = _nav()
    nav.manifest.register_source("habits-january")
    nav.manifest.register_source("month-2026-01-01")
    grid = nav.heading_menu_grid(
        page_id="habits-january",
        nav_links=[("habits-january", "Habits"), ("month-2026-01-01", "Calendar")],
    )
    assert grid is not None
    assert "grid.cell(fill: black, text(white)[#padded_link(<habits-january>, [Habits])])" in grid
    assert "padded_link(<month-2026-01-01>, [Calendar])" in grid
    assert "padded_link(<annual>" not in grid


def test_side_menu_months_only_omits_quarters_and_two_column_table():
    typst = _nav().side_menu_cell(
        highlight_months=[],
        highlight_quarters=[],
        show_quarters=False,
    )
    assert "rotate(" in typst
    assert "270deg" in typst
    assert "columns: (1fr, 3fr)" not in typst
    assert "columns: (3fr, 1fr)" not in typst
    assert "Q1" not in typst
    assert "Q2" not in typst
    assert "Q3" not in typst
    assert "Q4" not in typst
    assert "Jan" in typst
    assert "Dec" in typst
    assert "mos_tabs(columns: (" in typst


def test_months_menu_emits_mos_tabs_not_raw_table():
    menu = MonthsMenu(
        i18n=_i18n(),
        manifest=Manifest(),
        range=[make_month("2026-01"), make_month("2026-04")],
    )
    typst = menu.generate()
    assert typst.startswith("mos_tabs(columns: (1fr, 1fr),")
    assert "table(" not in typst
    assert "table.cell([#[Jan]])" in typst
    assert "table.cell([#[Apr]])" in typst
    assert "text(bottom-edge:" not in typst
    assert "stroke:" not in typst
    jan = make_month("2026-01")
    menu.highlight([jan])
    highlighted = menu.generate()
    assert "table.cell(fill: black, text(white)[#[Jan]])" in highlighted
    assert highlighted.startswith("mos_tabs(columns: (1fr, 1fr),")
    assert "text(bottom-edge:" not in highlighted


def test_quarters_menu_emits_mos_tabs_not_raw_table():
    menu = QuartersMenu(
        i18n=_i18n(),
        manifest=Manifest(),
        range=[make_quarter("2026-01-01"), make_quarter("2026-10-01")],
    )
    typst = menu.generate()
    assert typst.startswith("mos_tabs(columns: (1fr, 1fr),")
    assert "table(" not in typst
    assert "table.cell([#[Q1]])" in typst
    assert "table.cell([#[Q4]])" in typst
    assert "text(bottom-edge:" not in typst
    assert "stroke:" not in typst
    q4 = make_quarter("2026-10-01")
    menu.highlight([q4])
    highlighted = menu.generate()
    assert "table.cell(fill: black, text(white)[#[Q4]])" in highlighted
    assert highlighted.startswith("mos_tabs(columns: (1fr, 1fr),")
    assert "text(bottom-edge:" not in highlighted


def test_months_menu_can_retarget_month_ids():
    nav = _nav()
    nav.manifest.register_source("habits-january")
    nav.manifest.register_source("month-2026-01-01")
    default = nav.side_menu_cell(highlight_months=[], highlight_quarters=[])
    assert "padded_link(<month-2026-01-01>)" in default
    assert "padded_link(<habits-january>)" not in default
    retargeted = nav.side_menu_cell(
        highlight_months=[],
        highlight_quarters=[],
        month_link_id=lambda month: f"habits-{month.name}",
    )
    assert "padded_link(<habits-january>)" in retargeted
    assert "padded_link(<month-2026-01-01>)" not in retargeted
