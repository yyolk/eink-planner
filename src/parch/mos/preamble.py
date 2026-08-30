"""Typst document preamble (page size, strokes, paper tiles, padded_link)."""

from __future__ import annotations

from parch.mos.configurator import Configurator


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

#let dotted = place(
  dx: 0.5pt,
  dy: regular_height - 0.3mm,
  circle(
    radius: 0.141mm,
    fill: black
  )
)

#let lined = place(
  line(
    start: (0%, regular_height - 0.15mm),
    end: (100%, regular_height - 0.15mm),
    stroke: regular_stroke + luma(130)
  )
)

// House paper is placed tiles, not a tiling fill. Typst SVG of
// rect(fill: tiling) is one userSpaceOnUse pattern on a huge path;
// GitHub/resvg drop that paint and leave the field white.
// Outer rect keeps the old 100% cell size. Tiles sit on the same
// page lattice as userSpaceOnUse (origin at 0,0).
#let rect_pattern(pattern) = rect(
  width: 100%,
  height: 100%,
  stroke: none,
  inset: 0pt,
  context {{
    let pos = here().position()
    let cell = regular_height.to-absolute()
    let ox = pos.x - cell * calc.floor(pos.x.pt() / cell.pt())
    let oy = pos.y - cell * calc.floor(pos.y.pt() / cell.pt())
    layout(size => {{
      let cols = calc.ceil((size.width + ox).pt() / cell.pt())
      let rows = calc.ceil((size.height + oy).pt() / cell.pt())
      box(width: size.width, height: size.height, clip: true, {{
        if cols == 0 or rows == 0 {{
          none
        }} else {{
          for iy in range(rows) {{
            for ix in range(cols) {{
              place(
                dx: cell * ix - ox,
                dy: cell * iy - oy,
                box(width: cell, height: cell, pattern)
              )
            }}
          }}
        }}
      }})
    }})
  }}
)

#let dotted_centered = tiling(
  size: (regular_height, regular_height),
  // place(center + horizon) does not resolve against a tiling cell
  // (circles sit on the origin and clip to quarters). Size the cell
  // first so align can actually center the 0.141mm circle.
  block(
    width: regular_height,
    height: regular_height,
    align(
      center + horizon,
      circle(
        radius: 0.141mm,
        fill: black
      )
    )
  ),
)

#let rect_pattern_centered(pattern) = box(
  width: 100%,
  height: 100%,
  layout(size => {{
    let cell = regular_height.to-absolute()
    let cols = calc.floor(size.width.pt() / cell.pt())
    let rows = calc.floor(size.height.pt() / cell.pt())
    if cols == 0 or rows == 0 {{
      box()
    }} else {{
      let nw = cols * cell
      let nh = rows * cell
      let dx = (size.width - nw) / 2
      let dy = (size.height - nh) / 2
      place(
        dx: dx,
        dy: dy,
        rect(
          width: nw,
          height: nh,
          fill: pattern
        )
      )
    }}
  }})
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
