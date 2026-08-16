"""Typst document preamble (page size, strokes, tilings, padded_link)."""

from __future__ import annotations

from eink_planner.mos.configurator import Configurator


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

#let dotted = tiling(
  size: (regular_height, regular_height),
  place(
    dx: 0.5pt,
    dy: regular_height - 0.3mm,
    circle(
      radius: 0.141mm,
      fill: black
    )
  ),
)

#let lined = tiling(
  size: (regular_height, regular_height),
  place(
    line(
      start: (0%, regular_height - 0.15mm),
      end: (100%, regular_height - 0.15mm),
      stroke: regular_stroke + luma(130)
    ),
  )
)

#let rect_pattern(pattern) = rect(
  width: 100%,
  height: 100%,
  fill: pattern
)

#let scratch_pad = rect_pattern({_v(p, 'scratch_pad')})

#let padded_link(padding: {_v(p, 'link_padding')}, target, content) = box(
  inset: -padding,
  link(target)[#box(inset: padding, content)]
)"""


def _v(mapping, key: str):
    if hasattr(mapping, "dig_bang"):
        return mapping[key] if key in mapping else mapping.dig_bang(key)
    return mapping[key]
