#let dotted(regular_height: none) = place(
  dx: 0.5pt,
  dy: regular_height - 0.3mm,
  circle(
    radius: 0.141mm,
    fill: black
  )
)

#let lined(regular_height: none, regular_stroke: none) = place(
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
#let rect_pattern(regular_height: none, pattern) = rect(
  width: 100%,
  height: 100%,
  stroke: none,
  inset: 0pt,
  context {
    let pos = here().position()
    let cell = regular_height.to-absolute()
    let ox = pos.x - cell * calc.floor(pos.x.pt() / cell.pt())
    let oy = pos.y - cell * calc.floor(pos.y.pt() / cell.pt())
    layout(size => {
      let cols = calc.ceil((size.width + ox).pt() / cell.pt())
      let rows = calc.ceil((size.height + oy).pt() / cell.pt())
      box(width: size.width, height: size.height, clip: true, {
        if cols == 0 or rows == 0 {
          none
        } else {
          for iy in range(rows) {
            for ix in range(cols) {
              place(
                dx: cell * ix - ox,
                dy: cell * iy - oy,
                box(width: cell, height: cell, pattern)
              )
            }
          }
        }
      })
    })
  }
)

#let dotted_centered(regular_height: none) = tiling(
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

#let rect_pattern_centered(regular_height: none, pattern) = box(
  width: 100%,
  height: 100%,
  layout(size => {
    let cell = regular_height.to-absolute()
    let cols = calc.floor(size.width.pt() / cell.pt())
    let rows = calc.floor(size.height.pt() / cell.pt())
    if cols == 0 or rows == 0 {
      box()
    } else {
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
    }
  })
)

#let padded_link(padding: none, target, content) = box(
  inset: -padding,
  link(target)[#box(inset: padding, content)]
)

#let contents_bars(thick_stroke: none, size: none) = text(size: size, context {
  let cap = 0.7em.to-absolute()
  let gap = (cap - 5 * thick_stroke) / 4
  box(
    width: 0.844em,
    height: cap,
    align(horizon + left, stack(
      dir: ttb,
      spacing: gap,
      line(length: 0.844em, stroke: thick_stroke + black),
      line(length: 0.844em, stroke: thick_stroke + black),
      line(length: 0.844em, stroke: thick_stroke + black),
      line(length: 0.844em, stroke: thick_stroke + black),
      line(length: 0.844em, stroke: thick_stroke + black),
    ))
  )
})
