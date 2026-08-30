"""PlannerDoc → Typst string. Grids, stacks, padded_link, labels."""

from __future__ import annotations

from parch.ir.nodes import (
    Anchor,
    Box,
    Cell,
    Col,
    DottedPad,
    Grid,
    Length,
    Link,
    Node,
    Page,
    Row,
    Spacer,
    Stroke,
    Text,
    pack_cells,
)
from parch.ir.plan import PlannerDoc, Styles
from parch.ir.units import to_mm


def render_typst(doc: PlannerDoc) -> str:
    preamble = _preamble(doc)
    pages = "\n#pagebreak()\n".join(_page(p, doc.styles) for p in doc.pages)
    return f"{preamble}\n{pages}\n"


def _preamble(doc: PlannerDoc) -> str:
    s = doc.styles
    return f"""#set page(
  width: {doc.page_w},
  height: {doc.page_h},
  margin: (
    top: {doc.margin_top},
    right: {doc.margin_right},
    bottom: {doc.margin_bottom},
    left: {doc.margin_left},
  )
)

#set text(
  size: {s.text_size}
)

#let regular_stroke = {s.regular_stroke}
#let thick_stroke = {s.thick_stroke}
#let regular_height = {s.regular_height}
#let regular_column_gutter = {s.regular_column_gutter}

#let h1 = {s.h1}

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

#let scratch_pad = rect_pattern({"dotted" if s.scratch_pad == "dotted" else "lined"})

#let padded_link(padding: {s.link_padding}, target, content) = box(
  inset: -padding,
  link(target)[#box(inset: padding, content)]
)"""


def _page(page: Page, styles: Styles) -> str:
    body = _emit(page.body, styles)
    return f"""#block(width: 100%, height: 100%, {body})"""


def _emit(node: Node | None, styles: Styles) -> str:
    if node is None:
        return "[]"
    if isinstance(node, Text):
        return _text(node, styles)
    if isinstance(node, Spacer):
        if node.size and node.size.unit in ("mm", "pt"):
            return f"box(width: {node.size}, height: {node.size})"
        return "[]"
    if isinstance(node, DottedPad):
        return "scratch_pad"
    if isinstance(node, Link):
        inner = _emit(node.child, styles)
        return f"padded_link(<{node.target_id}>, {inner})"
    if isinstance(node, Anchor):
        inner = _emit(node.child, styles)
        return f"[#{inner} <{node.id}>]"
    if isinstance(node, Box):
        return _box(node, styles)
    if isinstance(node, Col):
        return _stack(node.children, node.weights, node.gap, axis="col", styles=styles)
    if isinstance(node, Row):
        return _stack(node.children, node.weights, node.gap, axis="row", styles=styles)
    if isinstance(node, Grid):
        return _grid(node, styles)
    return "[]"


def _text(node: Text, styles: Styles) -> str:
    content = _content(node.text)
    args: list[str] = []
    if node.size:
        args.append(f"size: {node.size}")
    if node.bold:
        args.append("weight: \"bold\"")
    if node.color == "white":
        args.append("fill: white")
    elif node.color == "gray":
        args.append("fill: luma(130)")
    body = f"text({', '.join(args)})[{content}]" if args else f"[{content}]"
    if node.align:
        body = f"align({_align(node.align)}, {body})"
    return body


def _content(text: str) -> str:
    escaped = (
        text.replace("\\", "\\\\")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("#", "\\#")
    )
    return escaped.replace("\n", " \\ ")


def _align(value: str | None) -> str:
    if not value:
        return "left + horizon"
    parts = [p.strip() for p in value.replace("+", " ").split() if p.strip()]
    mapped = []
    for p in parts:
        mapped.append(
            {
                "center": "center",
                "left": "left",
                "right": "right",
                "top": "top",
                "bottom": "bottom",
                "horizon": "horizon",
            }.get(p, p)
        )
    if "horizon" not in mapped and "top" not in mapped and "bottom" not in mapped:
        if "center" in mapped:
            mapped.append("horizon")
        else:
            mapped.append("horizon")
    # de-dupe while keeping order
    seen = []
    for p in mapped:
        if p not in seen:
            seen.append(p)
    return " + ".join(seen)


def _stroke(stroke: Stroke | None, styles: Styles) -> str | None:
    if stroke is None:
        return None
    width = stroke.width or styles.regular_stroke
    color = {"black": "black", "white": "white", "gray": "luma(130)"}.get(stroke.color, "black")
    paint = f"{width} + {color}"
    if "all" in stroke.sides:
        return paint
    sides = []
    for side in ("top", "right", "bottom", "left"):
        if stroke.has(side):  # type: ignore[arg-type]
            sides.append(f"{side}: {paint}")
    if not sides:
        return None
    return f"({', '.join(sides)})"


def _box(node: Box, styles: Styles) -> str:
    inner = _emit(node.child, styles)
    args: list[str] = []
    if node.padding and node.padding.unit != "auto" and (node.padding.unit != "mm" or node.padding.value):
        args.append(f"inset: {node.padding}")
    stroke = _stroke(node.stroke, styles)
    if stroke:
        args.append(f"stroke: {stroke}")
    if node.fill == "black":
        args.append("fill: black")
    elif node.fill == "white":
        args.append("fill: white")
    chip = bool(node.fill) and node.stroke is None and node.padding.unit in ("mm", "pt") and node.padding.value > 0
    if node.min_w and node.min_w.unit in ("mm", "pt"):
        args.append(f"width: {node.min_w}")
    elif not chip:
        args.append("width: 100%")
    if node.min_h and node.min_h.unit in ("mm", "pt"):
        args.append(f"height: {node.min_h}")
    elif not chip:
        args.append("height: 100%")
    body = f"box({', '.join(args)}, {inner})" if args else f"box({inner})"
    if node.align:
        body = f"align({_align(node.align)}, {body})"
        # align() around a 100% box is a no-op; align the inner content instead
        if "width: 100%" in args:
            inner_aligned = f"align({_align(node.align)}, {inner})"
            args_wo = [a for a in args]
            body = f"box({', '.join(args_wo)}, {inner_aligned})"
    if node.rotate:
        body = f"rotate({node.rotate}deg, origin: center + horizon, {body})"
    return body


def _len_or_auto(length: Length) -> str:
    return str(length)


def _stack(
    children: list[Node],
    weights: list[Length] | None,
    gap: Length,
    *,
    axis: str,
    styles: Styles,
) -> str:
    items = ",\n  ".join(_emit(c, styles) for c in children)
    n = len(children)
    if n == 0:
        return "[]"
    tracks = weights if weights is not None else [Length.fr(1)] * n
    gap_s = str(gap) if gap.unit != "auto" else "0pt"
    if axis == "col":
        rows = ", ".join(_len_or_auto(t) for t in tracks)
        return f"""grid(
  columns: 1fr,
  rows: ({rows}),
  row-gutter: {gap_s},
  {items}
)"""
    cols = ", ".join(_len_or_auto(t) for t in tracks)
    return f"""grid(
  columns: ({cols}),
  rows: 1fr,
  column-gutter: {gap_s},
  {items}
)"""


def _grid(node: Grid, styles: Styles) -> str:
    cells = pack_cells(list(node.cells), max(1, len(node.cols)))
    ncols = max(len(node.cols), 1)
    nrows = max(len(node.rows), 1)
    for cell in cells:
        if cell.col is None or cell.row is None:
            continue
        ncols = max(ncols, cell.col + cell.colspan)
        nrows = max(nrows, cell.row + cell.rowspan)
    cols = list(node.cols) + [Length.fr(1)] * max(0, ncols - len(node.cols))
    rows = list(node.rows) + [Length.fr(1)] * max(0, nrows - len(node.rows))
    if isinstance(node.gutter, tuple):
        cg, rg = node.gutter
    else:
        cg = rg = node.gutter
    args = [
        f"columns: ({', '.join(str(c) for c in cols)})",
        f"rows: ({', '.join(str(r) for r in rows)})",
        f"column-gutter: {cg}",
        f"row-gutter: {rg}",
    ]
    if node.align:
        args.append(f"align: {_align(node.align)}")
    if node.inset:
        args.append(f"inset: {node.inset}")
    emitted = _emit_grid_cells(cells, ncols, nrows, styles)
    head = ",\n  ".join(args)
    return f"""grid(
  {head},
  {emitted}
)"""


def _emit_grid_cells(cells: list[Cell], ncols: int, nrows: int, styles: Styles) -> str:
    by_pos = {(c.col, c.row): c for c in cells if c.col is not None and c.row is not None}
    occupied: set[tuple[int, int]] = set()
    parts: list[str] = []
    for r in range(nrows):
        for c in range(ncols):
            if (c, r) in occupied:
                continue
            cell = by_pos.get((c, r))
            if cell is None:
                parts.append("[]")
                continue
            for rr in range(cell.row or 0, (cell.row or 0) + cell.rowspan):
                for cc in range(cell.col or 0, (cell.col or 0) + cell.colspan):
                    if (cc, rr) != (c, r):
                        occupied.add((cc, rr))
            parts.append(_grid_cell(cell, styles))
    return ",\n  ".join(parts)


def _grid_cell(cell: Cell, styles: Styles) -> str:
    inner = _emit(cell.child, styles)
    args: list[str] = []
    if cell.colspan > 1:
        args.append(f"colspan: {cell.colspan}")
    if cell.rowspan > 1:
        args.append(f"rowspan: {cell.rowspan}")
    if cell.align:
        args.append(f"align: {_align(cell.align)}")
    if cell.fill == "black":
        args.append("fill: black")
    elif cell.fill == "white":
        args.append("fill: white")
    stroke = _stroke(cell.stroke, styles)
    if stroke:
        args.append(f"stroke: {stroke}")
    if not args:
        return inner
    return f"grid.cell({', '.join(args)}, {inner})"


# silence unused import if a refactor drops to_mm
_ = to_mm
