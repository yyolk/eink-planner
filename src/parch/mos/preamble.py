"""Typst document preamble (page size, strokes, paper tiles, padded_link)."""

from importlib.resources import files
from pathlib import Path

from parch.devices import Device, get_device
from parch.mos.configurator import Configurator
from parch.sections._shared import _WELL_PATTERN

HOUSE_TYP = "house.typ"
DEVICE_TYP = "device.typ"


def house_typ_resource():
    """Packaged house.typ (functions of tokens)."""
    return files("parch.data") / "typst" / HOUSE_TYP


def render_device_typ(device: Device) -> str:
    """Fill the parameterized device.typ from a Python device record."""
    return (
        f"#let page-width = {device.page_width}\n"
        f"#let page-height = {device.page_height}\n"
        f"#let toolbar-edge = {device.toolbar_edge}\n"
        f"#let toolbar-clearance = {device.toolbar_clearance}\n"
        f"#let writing-clearance = {device.writing_clearance}\n"
        f"#let mos-width = {device.mos_width}\n"
    )


def write_device_typ(workdir: Path, device: str | Device) -> Path:
    """Write device.typ next to index.typst for relative #import."""
    if isinstance(device, str):
        device = get_device(device)
    dest = Path(workdir) / DEVICE_TYP
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render_device_typ(device), encoding="utf-8")
    return dest


def copy_house_typ(workdir: Path, device: str | Device | None = None) -> Path:
    """Copy house.typ next to index.typst. When *device* is given, write device.typ."""
    dest = Path(workdir) / HOUSE_TYP
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(house_typ_resource().read_bytes())
    if device is not None:
        write_device_typ(workdir, device)
    return dest


class Preamble:
    def __init__(self, configurator: Configurator) -> None:
        self.configurator = configurator
        self.planner_params = configurator.dig_bang("planner", "params")

    def generate(self) -> str:
        p = self.planner_params
        text_size = self.configurator.dig_bang("document", "text", "size")
        h1 = self.configurator.dig_bang("document", "text", "h1")
        mos_layout = _v(p, "mos_layout")
        heading = _v(p, "heading")
        side = _v(mos_layout, "side_menu_position")
        scratch = _v(p, "scratch_pad")
        return f"""#import "device.typ": page-width, page-height, toolbar-edge, toolbar-clearance, writing-clearance, mos-width
#import "house.typ": dotted, lined, rect_pattern, dotted_centered, lined_fill, rect_pattern_centered, padded_link, contents_bars, lead_pair, trail_heading, mos_frame, well_frame, mos_tabs, mos_rail, month_grid, month_weeks, week_matrix, lined_well, daily_well, quarter_well, page-margin
#let page-margin = page-margin.with(toolbar-edge: toolbar-edge, toolbar-clearance: toolbar-clearance, writing-clearance: writing-clearance)
#set page(width: page-width, height: page-height, margin: page-margin({side}))

#set text(
  size: {text_size}
)

#let regular_stroke = {_v(p, 'regular_stroke')}
#let thick_stroke = {_v(p, 'thick_stroke')}
#let regular_height = {_v(p, 'regular_height')}
#let regular_column_gutter = {_v(p, 'regular_column_gutter')}

#let h1 = {h1}
#let link_padding = {_v(p, 'link_padding')}

#let dotted = dotted(regular_height: regular_height)
#let lined = lined(regular_height: regular_height, regular_stroke: regular_stroke)
#let rect_pattern = rect_pattern.with(regular_height: regular_height)
#let dotted_centered = dotted_centered(regular_height: regular_height)
#let lined_fill = lined_fill.with(regular_height: regular_height, regular_stroke: regular_stroke)
#let review_lined = lined_fill(paint: black)
#let lined_fill = lined_fill()
#let rect_pattern_centered = rect_pattern_centered.with(regular_height: regular_height)
#let scratch_pad = lined_well({_WELL_PATTERN.get(scratch, scratch)})
#let padded_link = padded_link.with(padding: link_padding)
#let contents_bars = contents_bars.with(thick_stroke: thick_stroke)
#let mos_frame = mos_frame.with(mos-width: mos-width, column-gutter: {_v(mos_layout, 'column_gutter')})
#let well_frame = well_frame.with(heading-height: {_v(heading, 'height')}, row-gutter: {_v(mos_layout, 'row_gutter')}, heading-stroke: regular_stroke)
#let mos_tabs = mos_tabs.with(stroke: regular_stroke, turn: {_v(mos_layout, 'menu_rotate')})
#let mos_rail = mos_rail.with(gutter: regular_column_gutter)
#let month_grid = month_grid.with(hline-stroke: regular_stroke + black)
#let month_weeks = month_weeks.with(week-col: regular_height, stroke: regular_stroke)
#let week_matrix = week_matrix.with(header-stroke: regular_stroke + black, regular-height: regular_height)
#let daily_well = daily_well.with(column-gutter: regular_column_gutter)
#let quarter_well = quarter_well.with(column-gutter: regular_column_gutter)"""


def _v(mapping, key: str):
    if hasattr(mapping, "dig_bang"):
        return mapping[key] if key in mapping else mapping.dig_bang(key)
    return mapping[key]
