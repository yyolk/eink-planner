"""Typst document preamble (page size, strokes, paper tiles, padded_link)."""

from importlib.resources import files
from pathlib import Path

from parch.mos.configurator import Configurator

HOUSE_TYP = "house.typ"


def house_typ_resource():
    """Packaged house.typ (functions of tokens)."""
    return files("parch.data") / "typst" / HOUSE_TYP


def copy_house_typ(workdir: Path) -> Path:
    """Copy house.typ next to index.typst for relative #import."""
    dest = Path(workdir) / HOUSE_TYP
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(house_typ_resource().read_bytes())
    return dest


class Preamble:
    def __init__(self, configurator: Configurator) -> None:
        self.configurator = configurator
        self.dimensions = configurator.dig_bang("document", "layout", "dimensions")
        self.margin = configurator.dig_bang("document", "layout", "margin")
        self.planner_params = configurator.dig_bang("planner", "params")

    def generate(self) -> str:
        d = self.dimensions
        m = self.margin
        p = self.planner_params
        text_size = self.configurator.dig_bang("document", "text", "size")
        h1 = self.configurator.dig_bang("document", "text", "h1")
        return f"""#set page(
  width: {_v(d, 'width')},
  height: {_v(d, 'height')},

  margin: (
    top: {_v(m, 'top')},
    right: {_v(m, 'right')},
    bottom: {_v(m, 'bottom')},
    left: {_v(m, 'left')},
  )
)

#set text(
  size: {text_size}
)

#let regular_stroke = {_v(p, 'regular_stroke')}
#let thick_stroke = {_v(p, 'thick_stroke')}
#let regular_height = {_v(p, 'regular_height')}
#let regular_column_gutter = {_v(p, 'regular_column_gutter')}

#let h1 = {h1}
#let link_padding = {_v(p, 'link_padding')}

#import "house.typ": dotted, lined, rect_pattern, dotted_centered, rect_pattern_centered, padded_link, contents_bars, lead_pair, trail_heading

#let dotted = dotted(regular_height: regular_height)
#let lined = lined(regular_height: regular_height, regular_stroke: regular_stroke)
#let rect_pattern = rect_pattern.with(regular_height: regular_height)
#let dotted_centered = dotted_centered(regular_height: regular_height)
#let rect_pattern_centered = rect_pattern_centered.with(regular_height: regular_height)
#let scratch_pad = rect_pattern({_v(p, 'scratch_pad')})
#let padded_link = padded_link.with(padding: link_padding)
#let contents_bars = contents_bars.with(thick_stroke: thick_stroke)"""


def _v(mapping, key: str):
    if hasattr(mapping, "dig_bang"):
        return mapping[key] if key in mapping else mapping.dig_bang(key)
    return mapping[key]
