# Layout IR (exploration)

MOS should build a **layout tree**. Backends only paint.

This branch keeps the existing Typst-string (`mos/`) generate path. `--ir` is
additive: same calendar, Configurator, Manifest, and I18n, a new tree in the
middle. Index, projects, habits, review, tasks, meetings, and colophon are in
the tree now (raw pages, `chrome=False`, except habit month grids which use MOS
chrome). The string MOS path is still the default.

## Why this shape

The two backends had already drifted. Typst emits strings with `#grid` /
`#stack` / `padded_link`. A later fpdf2 painter walked the calendar again and
drew into absolute boxes. Chrome (side Q/month menu + heading + Calendar link)
lived in two places. A little calendar was a Typst string *or* a drawer, never
a value.

A small flex/grid IR is enough for MOS:

| Node | Role |
| --- | --- |
| `Length` | `mm` / `pt` / `fr` / `auto` |
| `Page` | id, chrome flag, highlight metadata, `body` |
| `Col` / `Row` | children + gap + per-child weights |
| `Grid` | tracks, gutter, cells (colspan / rowspan / stroke) |
| `Box` | padding, stroke, fill, align, min size, optional rotate |
| `Text` | string, size, bold, black/white |
| `Link` / `Anchor` | intra-PDF navigation |
| `DottedPad` | the one semantic leaf painters must special-case |
| `Spacer` | empty space |

`LittleCalendar`, schedule, priorities, side menu, and the MOS frame are
**helpers that return trees** (`widgets.py`). Chrome is in the tree
(`widgets.frame`) so a page is one value, not a body plus a side channel.

There is no constraint solver. `resolve_tracks` is one pass: take fixed and
`auto` (intrinsic) sizes, then split the leftover across `fr`. Negative leftover
clamps to zero.

## What we learned

- The node set is rich enough for every MOS page type (cover, index, annual,
  quarterly, monthly, weekly, daily, daily notes, projects, habits, review,
  tasks, meetings, colophon). Painful bits were *partial strokes*, *rotated
  labels*, and *rowspan chrome* — not missing page-level primitives.
- Putting chrome in the tree is the right call. The cost is one side-menu copy
  per chrome page. Fine for an exploration; a later pass could intern it.
- Typst-IR and a later fpdf2-IR will not be pixel-identical. Fonts (Typst
  default vs Times), fr leftover, and how rotate is applied all differ.
  Recognizable MOS is the bar, not a screenshot diff.
- One-pass top-down is enough when MOS is honest about `auto` vs `fr`. Daily
  left column is `auto` schedule + `1fr` calendar. That is the whole trick.
- Special-casing a whole page in one painter is how the backends drifted. If a
  page is painful, add a field (`Box.rotate`, `Stroke.sides`) rather than a
  `draw_monthly`.
- Both IR painters write the full 2026 Nomad book, including the extra
  sections. Page count is whatever the builders emit (string MOS and IR match).

## Honest gaps

- **Rotate** is a `Box` property, not a transformed subtree. Side-menu cells
  rotate their label; we do not reflow a table 270° the way Typst `mos/` does.
- **Text metrics** are crude (Times width, `1.15 × em` line height). Typst
  measures a different font. Heading `Row` is `auto` Calendar + `1fr` title,
  so January / Week 1 titles do not sit in the same place.
- **No wrapping**. Labels that overflow clip or spill.
- **Grid packing** is row-major with explicit `Cell` positions for chrome. A
  real CSS grid this is not.
- **DottedPad** tiling matches the existing Typst `tiling`, but alignment vs
  cell edges can drift by a fraction of a millimetre.
- Cover, Contents, and the other raw Nomad sections are `chrome=False`. Habit
  month grids (and the core calendar pages) go through `frame`.
- Ruled leftover paper is a `Grid` of bottom-stroked rows, not a `Line` leaf.
  Empty habit-name headers are stroked boxes — no diagonal in the node set.
  Colophon dump pagination (Typst page state / 1/N headers) is a single
  `Text` block when `dump` is on.

## Commands

```shell
parch press supernote-nomad --ir -w out/ir-typst
```

The default generate path (`Generate` string MOS + Compile) is unchanged.

## What we would change if we keep this

1. Delete the parallel `mos/` string builders once IR looks right. One MOS.
2. A cheap measure pass (or cache intrinsics) so daily/weekly headings size
   without guessing.
3. Intern chrome: one side-menu prototype, highlight as a parameter, not one
   tree per chrome page.
4. Drop `Page.title` / highlight fields if chrome stays in the tree — they are
   now metadata for tests.
5. Consider a `Line` leaf if we ever want ruled pads without a second tiling.
