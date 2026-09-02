#let page-margin(side, toolbar-edge: none, toolbar-clearance: none, writing-clearance: none) = (
  top: if toolbar-edge == top { toolbar-clearance } else { 0mm },
  bottom: 0mm,
  left: if side == right { writing-clearance } else { 0mm },
  right: if side == left { writing-clearance } else { 0mm },
)

// House paper is a tiling fill. dotted_centered, lined_fill, and
// task_fill are the live tiles; lined_well is the full-bleed writing field.
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

#let lined_fill(regular_height: none, regular_stroke: none, paint: luma(130)) = tiling(
  size: (regular_height, regular_height),
  line(
    start: (0pt, regular_height - 0.15mm),
    end: (regular_height, regular_height - 0.15mm),
    stroke: regular_stroke + paint,
  ),
)

#let task_fill(page-width: none, regular_height: none, regular_stroke: none) = tiling(
  size: (page-width, regular_height),
  block(
    width: page-width,
    height: regular_height,
    stroke: (bottom: regular_stroke + black),
    align(
      horizon + start,
      $square.stroked$,
    )
  ),
)

#let padded_link(padding: none, target, content) = box(
  inset: -padding,
  link(target)[#box(inset: padding, content)]
)

#let contents_bars(thick_stroke: none, size: none) = {
  let cap = 0.7 * size
  let gap = (cap - 5 * thick_stroke) / 4
  box(
    width: 0.844 * size,
    height: cap,
    align(horizon + left, stack(
      dir: ttb,
      spacing: gap,
      line(length: 0.844 * size, stroke: thick_stroke + black),
      line(length: 0.844 * size, stroke: thick_stroke + black),
      line(length: 0.844 * size, stroke: thick_stroke + black),
      line(length: 0.844 * size, stroke: thick_stroke + black),
      line(length: 0.844 * size, stroke: thick_stroke + black),
    ))
  )
}

#let lead_pair(mark, title, spacing: 6pt) = stack(
  dir: ltr,
  spacing: spacing,
  align(horizon, mark),
  align(horizon, title),
)

// Title shrinks in the 1fr when it overflows; skip scale when it fits.
#let trail_heading(title, mark, shrink: false) = grid(
  columns: (1fr, auto),
  align: horizon + start,
  if shrink {
    layout(size => context {
      let wanted = measure(title)
      if wanted.width == 0pt or wanted.width <= size.width {
        title
      } else {
        scale(
          size.width / wanted.width * 100%,
          origin: start + horizon,
          reflow: true,
          title,
        )
      }
    })
  } else {
    title
  },
  mark,
)

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

// Descender floor: heading row grows by stroke air. No clip.
#let well_frame(heading, body, heading-height: none, row-gutter: none, heading-stroke: none) = {
  let gap = if heading-stroke == none { 0pt } else { stroke(heading-stroke).thickness }
  grid(
    columns: 1fr,
    rows: (heading-height + gap, 1fr),
    row-gutter: row-gutter,
    grid.cell(
      align: horizon,
      inset: (bottom: gap),
      {
        set text(bottom-edge: "descender")
        box(width: 100%, height: 100%, heading)
      },
    ),
    body,
  )
}

// MOS strip: one column, n 1fr rows; rotate each cell body.
#let mos_tabs(stroke: none, turn: none, columns: none, ..cells) = {
  let gap = if stroke == none { 0pt } else { std.stroke(stroke).thickness }
  let items = cells.pos()
  set text(bottom-edge: "descender")
  table(
    stroke: stroke,
    inset: gap,
    columns: 1fr,
    rows: (1fr,) * items.len(),
    align: horizon + center,
    ..items.map(c => if c.func() == table.cell {
      table.cell(
        fill: c.at("fill", default: none),
        align: horizon + center,
        rotate(turn, origin: center + horizon, c.body),
      )
    } else {
      rotate(turn, origin: center + horizon, c)
    }),
  )
}

// Q/month split; house owns the 1fr/3fr tracks.
#let mos_rail(quarters, months, reverse: false, gutter: none) = grid(
  columns: 1fr,
  rows: if reverse { (3fr, 1fr) } else { (1fr, 3fr) },
  row-gutter: gutter,
  ..if reverse { (months, quarters) } else { (quarters, months) },
)

// Week cell is always first in each 8-cell row. MOS-right moves it to the end.
#let _order_week_rows(side, cells) = if side == left {
  cells
} else {
  let out = ()
  for i in range(0, cells.len(), step: 8) {
    let row = cells.slice(i, count: 8)
    out += row.slice(1) + (row.at(0),)
  }
  out
}

// Name + weekdays are auto; week-rows are equal 1fr tracks. Never `rows: 1fr`
// alone (5-week vs 6-week months would move the weekday rule). Columns are
// 8×1fr. Name is caller-owned (colspan 8). House owns the MOS week rail.
#let month_grid(
  side,
  name,
  inset: none,
  week-rows: 6,
  hline-stroke: none,
  ..rows,
) = grid(
  align: center + horizon,
  inset: inset,
  stroke: (x, _) => if x == (if side == left { 1 } else { 7 }) { (left: hline-stroke) },
  columns: (1fr,) * 8,
  rows: (auto, auto) + (1fr,) * week-rows,
  grid.hline(y: 1, stroke: hline-stroke),
  grid.hline(y: 2, stroke: hline-stroke),
  name,
  .._order_week_rows(side, rows.pos()),
)

// Monthly-page calendar. Rows stay caller-owned (live week count). House
// owns week-col seating. Same side token as mos_frame. Block height is
// 1fr so leftover 1fr body rows receive the outer calendar track.
#let month_weeks(side, rows: none, week-col: none, stroke: none, ..cells) = block(
  width: 100%,
  height: 1fr,
  grid(
    stroke: stroke,
    columns: if side == left { (week-col,) + (1fr,) * 7 } else { (1fr,) * 7 + (week-col,) },
    rows: rows,
    .._order_week_rows(side, cells.pos()),
  ),
)

// Full-bleed writing field. Parent is well_frame's 1fr body (bounded).
// Tiling fill.
#let lined_well(pattern) = box(width: 100%, height: 100%, fill: pattern)

// Header on auto; bottom inset is the rule's own thickness. Clipped
// lined_well fills the 1fr.
// Not exported — week_matrix is the only weekly overview entry.
#let week_cell(header, header-stroke: none, pattern: none) = {
  let gap = if header-stroke == none { 0pt } else { stroke(header-stroke).thickness }
  grid(
    columns: 1fr,
    rows: (auto, 1fr),
    grid.cell(
      inset: (bottom: gap),
      stroke: (bottom: header-stroke),
      text(bottom-edge: "descender", header),
    ),
    box(
      width: 100%,
      height: 100%,
      clip: true,
      inset: (top: 0.25em, bottom: 0.25em),
      lined_well(pattern),
    ),
  )
}

// 3×3 of equal 1fr tracks. column-gutter only (no row-gutter). Notes is
// colspan: 2 on the eighth cell so the first column stays one vertical.
#let week_matrix(
  column-gutter: none,
  header-stroke: none,
  pattern: none,
  ..contents,
) = {
  let headers = contents.pos()
  let painted = headers.map(header => week_cell(
    header,
    header-stroke: header-stroke,
    pattern: pattern,
  ))
  grid(
    columns: (1fr, 1fr, 1fr),
    rows: (1fr, 1fr, 1fr),
    column-gutter: column-gutter,
    ..painted.slice(0, 7),
    grid.cell(colspan: 2, painted.at(7)),
  )
}

// Parent is well_frame's 1fr body (bounded). House owns the 3fr/5fr
// split. Same side token as mos_frame.
#let daily_well(side, hours, writing, column-gutter: none) = if side == left {
  grid(columns: (3fr, 5fr), rows: 1fr, column-gutter: column-gutter, hours, writing)
} else {
  grid(columns: (5fr, 3fr), rows: 1fr, column-gutter: column-gutter, writing, hours)
}

// Parent is well_frame's 1fr body (bounded). House owns the 2fr/3fr
// split. Same side token as mos_frame.
#let quarter_well(side, months, pad, column-gutter: none) = if side == left {
  grid(columns: (2fr, 3fr), rows: 1fr, column-gutter: column-gutter, months, pad)
} else {
  grid(columns: (3fr, 2fr), rows: 1fr, column-gutter: column-gutter, pad, months)
}
