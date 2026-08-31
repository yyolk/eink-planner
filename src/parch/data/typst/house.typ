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

#let lead_pair(mark, title, spacing: 6pt) = stack(
  dir: ltr,
  spacing: spacing,
  align(horizon, mark),
  align(horizon, title),
)

#let trail_heading(title, mark, spacing: none, direction: ltr) = context {
  let seated_title = title
  let seated_mark = mark
  let band = calc.max(measure(seated_title).height, measure(seated_mark).height)
  stack(
    dir: direction,
    spacing: spacing,
    box(height: band, align(horizon + left, seated_title)),
    box(height: band, align(horizon + left, seated_mark)),
  )
}

#let mos_frame(side, mos, well, mos-width: none, column-gutter: none) = if side == left {
  grid(
    columns: (mos-width, 1fr),
    rows: 1fr,
    column-gutter: column-gutter,
    mos,
    well,
  )
} else {
  grid(
    columns: (1fr, mos-width),
    rows: 1fr,
    column-gutter: column-gutter,
    well,
    mos,
  )
}

#let well_frame(heading, body, heading-height: none, row-gutter: none) = grid(
  columns: 1fr,
  rows: (heading-height, 1fr),
  row-gutter: row-gutter,
  grid.cell(align: horizon, heading),
  body,
)

// Name + weekdays are auto; week-rows are equal 1fr tracks. Never `rows: 1fr`
// alone (5-week vs 6-week months would move the weekday rule). Columns default
// to week + 7 days. Stroke/inset stay caller-owned.
#let month_grid(
  inset: none,
  stroke: none,
  columns: (1fr,) * 8,
  week-rows: 6,
  hline-stroke: none,
  ..cells,
) = grid(
  align: center + horizon,
  inset: inset,
  stroke: stroke,
  columns: columns,
  rows: (auto, auto) + (1fr,) * week-rows,
  grid.hline(y: 1, stroke: hline-stroke),
  grid.hline(y: 2, stroke: hline-stroke),
  ..cells,
)

// Header on auto; rule sits on the descender. Clipped pattern fills the 1fr.
// Not exported — week_matrix is the only weekly overview entry.
#let week_cell(header, header-stroke: none, pattern: none, regular-height: none) = grid(
  columns: 1fr,
  rows: (auto, 1fr),
  grid.cell(
    stroke: (bottom: header-stroke),
    text(bottom-edge: "descender", header),
  ),
  box(
    width: 100%,
    height: 100%,
    clip: true,
    inset: (top: 0.25em, bottom: 0.25em),
    rect_pattern(regular_height: regular-height, pattern),
  ),
)

// 3×3 of equal 1fr tracks. column-gutter only (no row-gutter). Notes is
// colspan: 2 on the eighth cell so the first column stays one vertical.
#let week_matrix(
  column-gutter: none,
  header-stroke: none,
  pattern: none,
  regular-height: none,
  ..contents,
) = {
  let headers = contents.pos()
  let painted = headers.map(header => week_cell(
    header,
    header-stroke: header-stroke,
    pattern: pattern,
    regular-height: regular-height,
  ))
  grid(
    columns: (1fr, 1fr, 1fr),
    rows: (1fr, 1fr, 1fr),
    column-gutter: column-gutter,
    ..painted.slice(0, 7),
    grid.cell(colspan: 2, painted.at(7)),
  )
}

// Full-bleed writing field. Parent is well_frame's 1fr body (bounded).
// One region; clip is rect_pattern's. No header, inset, side, or cells.
#let lined_well(regular-height: none, pattern) = box(
  width: 100%,
  height: 100%,
  clip: true,
  rect_pattern(regular_height: regular-height, pattern),
)

// Parent is well_frame's 1fr body (bounded). One row. House owns the
// 3fr/5fr split; MOS-left seats hours | writing, MOS-right seats
// writing | hours. Same side token as mos_frame / page-margin.
// Spread the pair so the if-block is two grid children, not one join.
#let daily_well(side, hours, writing, column-gutter: 0pt) = grid(
  columns: if side == left { (3fr, 5fr) } else { (5fr, 3fr) },
  rows: (1fr,),
  column-gutter: column-gutter,
  ..if side == left { (hours, writing) } else { (writing, hours) },
)
