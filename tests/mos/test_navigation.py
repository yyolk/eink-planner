from parch.config import StrictDict
from parch.i18n import I18n
from parch.mos.builder import Builder
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


def _nav(reverse: bool = False, reverse_items: bool | None = None) -> Navigation:
    items = reverse if reverse_items is None else reverse_items
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
                        "reverse_months_quarters_items": items,
                    },
                    "heading": {"height": "10mm"},
                }
            }
        }
    )
    return Navigation(i18n=_i18n(), manifest=Manifest(), configurator=Configurator(dto))


def _builder(reverse: bool = False) -> Builder:
    dto = StrictDict(
        {
            "planner": {
                "params": {
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "weekday_start": "Monday",
                    "regular_stroke": "0.3pt",
                    "thick_stroke": "0.6pt",
                    "regular_height": "6mm",
                    "regular_column_gutter": "2mm",
                    "link_padding": "2mm",
                    "scratch_pad": "dotted",
                    "mos_layout": {
                        "menu_rotate": "270deg",
                        "reverse_months_quarters": reverse,
                        "reverse_months_quarters_items": reverse,
                        "side_menu_position": "left",
                        "column_gutter": "2mm",
                        "row_gutter": "2mm",
                    },
                    "heading": {"height": "10mm"},
                }
            },
            "document": {"text": {"size": "8pt", "h1": "8mm"}},
        }
    )
    configurator = Configurator(dto)
    return Builder(i18n=_i18n(), configurator=configurator, manifest=Manifest())


def test_side_menu_emits_highlights_only():
    typst = _nav(reverse=False).side_menu_cell(highlight_months=[], highlight_quarters=[])
    assert typst == "mos_strip(highlight-months: (), highlight-quarters: ())"
    assert "mos_rail(" not in typst
    assert "mos_tabs(" not in typst
    assert "padded_link" not in typst
    assert "table.cell" not in typst


def test_side_menu_reversed_seating_stays_in_prelude():
    typst = _nav(reverse=True).side_menu_cell(highlight_months=[], highlight_quarters=[])
    assert typst == "mos_strip(highlight-months: (), highlight-quarters: ())"
    assert "reverse:" not in typst
    assert "mos_rail(" not in typst


def test_year_items_are_jan_to_dec_and_q1_to_q4():
    nav = _nav(reverse=False)
    months = nav.year_month_items()
    quarters = nav.year_quarter_items()
    assert months.index("[Jan]") < months.index("[Dec]")
    assert quarters.index("[Q1]") < quarters.index("[Q4]")
    assert months.startswith("((none, [Jan]),")
    assert quarters.startswith("((none, [Q1]),")
    assert "padded_link" not in months
    assert "table.cell" not in months
    assert "mos_tabs" not in months


def test_year_items_follow_python_array_order():
    nav = _nav(reverse=True, reverse_items=True)
    months = nav.year_month_items()
    quarters = nav.year_quarter_items()
    assert months.index("[Dec]") < months.index("[Jan]")
    assert quarters.index("[Q4]") < quarters.index("[Q1]")


def test_builder_binds_year_dests_once():
    builder = _builder(reverse=False)
    for month in (
        "month-2026-01-01",
        "month-2026-12-01",
        "quarter-2026-1",
        "quarter-2026-4",
    ):
        builder.manifest.register_source(month)
    bind = builder._mos_strip_bind()
    assert bind.startswith("#let mos_strip = mos_strip.with(months: ((")
    assert "(<month-2026-01-01>, [Jan])" in bind
    assert "(<month-2026-12-01>, [Dec])" in bind
    assert bind.index("[Jan]") < bind.index("[Dec]")
    assert "(<quarter-2026-1>, [Q1])" in bind
    assert "(<quarter-2026-4>, [Q4])" in bind
    assert bind.index("[Q1]") < bind.index("[Q4]")
    assert "reverse: false)" in bind
    assert "padded_link" not in bind
    assert "table.cell" not in bind
    assert builder.generate().count("#let mos_strip = mos_strip.with(months:") == 1


def test_builder_bind_reverse_is_seating_only():
    builder = _builder(reverse=True)
    bind = builder._mos_strip_bind()
    assert "reverse: true)" in bind
    assert bind.index("[Dec]") < bind.index("[Jan]")


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


def test_side_menu_months_only_omits_quarters():
    typst = _nav().side_menu_cell(
        highlight_months=[],
        highlight_quarters=[],
        show_quarters=False,
    )
    assert typst == "mos_strip(highlight-months: (), highlight-quarters: (), show-quarters: false)"
    assert "mos_rail(" not in typst
    assert "mos_tabs(" not in typst
    assert "Q1" not in typst
    assert "Jan" not in typst


def test_months_menu_emits_dest_label_pairs():
    menu = MonthsMenu(
        i18n=_i18n(),
        manifest=Manifest(),
        range=[make_month("2026-01"), make_month("2026-04")],
    )
    typst = menu.generate()
    assert typst == "((none, [Jan]), (none, [Apr]),)"
    assert "mos_tabs" not in typst
    assert "table.cell" not in typst
    assert "padded_link" not in typst
    jan = make_month("2026-01")
    menu.manifest.register_source(jan.id)
    linked = menu.generate()
    assert linked == "((<month-2026-01-01>, [Jan]), (none, [Apr]),)"


def test_quarters_menu_emits_dest_label_pairs():
    menu = QuartersMenu(
        i18n=_i18n(),
        manifest=Manifest(),
        range=[make_quarter("2026-01-01"), make_quarter("2026-10-01")],
    )
    typst = menu.generate()
    assert typst == "((none, [Q1]), (none, [Q4]),)"
    assert "mos_tabs" not in typst
    assert "table.cell" not in typst
    q4 = make_quarter("2026-10-01")
    menu.manifest.register_source(q4.id)
    linked = menu.generate()
    assert linked == "((none, [Q1]), (<quarter-2026-4>, [Q4]),)"


def test_months_menu_can_retarget_month_ids():
    nav = _nav()
    nav.manifest.register_source("habits-january")
    nav.manifest.register_source("month-2026-01-01")
    default = nav.year_month_items()
    assert "(<month-2026-01-01>, [Jan])" in default
    assert "(<habits-january>, [Jan])" not in default
    retargeted = nav.side_menu_cell(
        highlight_months=[],
        highlight_quarters=[],
        month_link_id=lambda month: f"habits-{month.name}",
        show_quarters=False,
    )
    assert retargeted.startswith("mos_strip(months: ((")
    assert "(<habits-january>, [Jan])" in retargeted
    assert "(<month-2026-01-01>, [Jan])" not in retargeted
    assert "show-quarters: false" in retargeted
    assert "padded_link" not in retargeted


def test_side_menu_highlights_are_dests():
    nav = _nav()
    jan = make_month("2026-01")
    q1 = make_quarter("2026-01-01")
    nav.manifest.register_source(jan.id)
    nav.manifest.register_source(q1.id)
    typst = nav.side_menu_cell(highlight_months=[jan], highlight_quarters=[q1])
    assert typst == (
        "mos_strip(highlight-months: (<month-2026-01-01>,), "
        "highlight-quarters: (<quarter-2026-1>,))"
    )
    missing = nav.side_menu_cell(
        highlight_months=[make_month("2026-02")],
        highlight_quarters=[],
    )
    assert missing == "mos_strip(highlight-months: (), highlight-quarters: ())"
