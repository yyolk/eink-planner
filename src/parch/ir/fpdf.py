"""PlannerDoc → fpdf2 PDF. One-pass top-down fr resolve, then draw."""

from __future__ import annotations

import struct
import tempfile
import zlib
from pathlib import Path

from fpdf import FPDF

from parch.ir.nodes import (
    Anchor,
    Box,
    Col,
    DottedPad,
    Grid,
    Length,
    Link,
    Node,
    Row,
    Spacer,
    Stroke,
    Text,
    collect_anchors,
    pack_cells,
)
from parch.ir.plan import PlannerDoc, Styles
from parch.ir.units import mm_to_pt, resolve_tracks, to_mm

_INK = {"black": 0, "white": 255, "gray": 150}


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _grayscale_png(pixels: bytes, width: int, height: int) -> bytes:
    raw = b"".join(b"\x00" + pixels[y * width : (y + 1) * width] for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )


def _write_dot_tile(path: Path, spacing_mm: float) -> Path:
    """Write a 20×20 dotted tile matching the Typst tiling offsets."""
    cells = 20
    dpi = 180
    radius_mm = 0.141
    gray = 30
    size_mm = spacing_mm * cells
    px = max(cells, int(round(size_mm / 25.4 * dpi)))
    buf = bytearray([255] * (px * px))
    spacing_px = px / cells
    r = max(1.0, radius_mm / 25.4 * dpi)
    dx = (0.5 * 25.4 / 72.0) / 25.4 * dpi
    dy = (spacing_mm - 0.3) / 25.4 * dpi
    r2 = r * r
    for col in range(cells):
        for row in range(cells):
            cx = col * spacing_px + dx
            cy = row * spacing_px + dy
            x0 = max(0, int(cx - r))
            x1 = min(px - 1, int(cx + r))
            y0 = max(0, int(cy - r))
            y1 = min(px - 1, int(cy + r))
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                        buf[y * px + x] = gray
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_grayscale_png(bytes(buf), px, px))
    return path

def _latin1(text: str) -> str:
    """Times core fonts are latin-1; map MOS dashes so review/tasks paint."""
    return (
        text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


class IrPDF(FPDF):
    def __init__(self, page_w: float, page_h: float, styles: Styles) -> None:
        super().__init__(unit="mm", format=(page_w, page_h))
        self.styles = styles
        self.set_margins(0, 0, 0)
        self.set_auto_page_break(False, 0)
        self.c_margin = 0
        self._font: tuple[str, str, float] = ("Times", "", mm_to_pt(to_mm(styles.text_size)))
        self.set_font(*self._font)
        self._dot_path: Path | None = None
        self._dot_tile_mm = to_mm(styles.regular_height) * 20
        self._tmp = Path(tempfile.mkdtemp(prefix="parch-ir-"))
        self.links: dict[str, int] = {}

    def font(self, style: str = "", size_pt: float | None = None) -> None:
        # Always call set_font. rotation()/local_context restore fpdf2's
        # font size on exit, which would desync a cache and leave later
        # 7pt menu labels at the previous page's 36pt cover size.
        size = self._font[2] if size_pt is None else float(size_pt)
        self.set_font("Times", style, size)
        self._font = ("Times", style, size)


def render_fpdf(doc: PlannerDoc, dest: str | Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    page_w = to_mm(doc.page_w)
    page_h = to_mm(doc.page_h)
    pdf = IrPDF(page_w, page_h, doc.styles)
    id_to_page: dict[str, int] = {}
    for index, page in enumerate(doc.pages, start=1):
        if page.id:
            id_to_page[page.id] = index
        for aid in collect_anchors(page.body):
            id_to_page.setdefault(aid, index)
        if page.title:
            for aid in collect_anchors(page.title):
                id_to_page.setdefault(aid, index)
    for page_id, number in id_to_page.items():
        pdf.links[page_id] = pdf.add_link(page=number)

    painter = _Painter(pdf, doc)
    mx, my = to_mm(doc.margin_left), to_mm(doc.margin_top)
    cw = page_w - mx - to_mm(doc.margin_right)
    ch = page_h - my - to_mm(doc.margin_bottom)
    for page in doc.pages:
        pdf.add_page()
        pdf.font("", mm_to_pt(to_mm(doc.styles.text_size)))
        painter.place(page.body, mx, my, cw, ch)
    pdf.output(str(dest))
    return dest


class _Painter:
    def __init__(self, pdf: IrPDF, doc: PlannerDoc) -> None:
        self.pdf = pdf
        self.doc = doc
        self.styles = doc.styles

    def place(self, node: Node | None, x: float, y: float, w: float, h: float) -> None:
        if node is None or w <= 0.05 or h <= 0.05:
            return
        if isinstance(node, Text):
            self._text(node, x, y, w, h)
        elif isinstance(node, Spacer):
            return
        elif isinstance(node, DottedPad):
            self._dots(x, y, w, h)
        elif isinstance(node, Link):
            self.place(node.child, x, y, w, h)
            self._hit(x, y, w, h, node.target_id)
        elif isinstance(node, Anchor):
            self.place(node.child, x, y, w, h)
        elif isinstance(node, Box):
            self._box(node, x, y, w, h)
        elif isinstance(node, Col):
            self._col(node, x, y, w, h)
        elif isinstance(node, Row):
            self._row(node, x, y, w, h)
        elif isinstance(node, Grid):
            self._grid(node, x, y, w, h)

    def _ink(self, color: str) -> int:
        return _INK.get(color, 0)

    def _font_pt(self, size: Length | None) -> float:
        if size is None:
            return mm_to_pt(to_mm(self.styles.text_size))
        if size.unit == "pt":
            return float(size.value)
        return mm_to_pt(to_mm(size))

    def _text(self, node: Text, x: float, y: float, w: float, h: float, *, skip_color: bool = False) -> None:
        size_pt = self._font_pt(node.size)
        self.pdf.font("B" if node.bold else "", size_pt)
        if not skip_color:
            self.pdf.set_text_color(self._ink(node.color))
        lines = _latin1(node.text).split("\n")
        th = size_pt * 25.4 / 72.0
        block = th * 1.15 * max(1, len(lines))
        align = (node.align or "center").split("+")[0].strip()
        yy = y + max(0.0, (h - block) / 2.0)
        for line in lines:
            tw = self.pdf.get_string_width(line) if line else 0.0
            if align == "left":
                tx = x + 0.4
            elif align == "right":
                tx = x + w - tw - 0.4
            else:
                tx = x + (w - tw) / 2.0
            self.pdf.text(tx, yy + th * 0.80, line)
            yy += th * 1.15

    def _hit(self, x: float, y: float, w: float, h: float, target_id: str) -> None:
        dest = self.pdf.links.get(target_id)
        if dest is None or w <= 0 or h <= 0:
            return
        if not self.doc.manifest.source(target_id):
            return
        pad = to_mm(self.styles.link_padding)
        self.pdf.link(x - pad * 0.1, y - pad * 0.05, w + pad * 0.2, h + pad * 0.1, dest)

    def _stroke_box(self, x: float, y: float, w: float, h: float, stroke: Stroke | None, fill: str | None) -> None:
        if fill is not None:
            self.pdf.set_fill_color(self._ink(fill))
            self.pdf.rect(x, y, w, h, style="F")
        if stroke is None:
            return
        width = to_mm(stroke.width or self.styles.regular_stroke)
        self.pdf.set_line_width(width)
        self.pdf.set_draw_color(self._ink(stroke.color))
        if stroke.has("all"):
            self.pdf.rect(x, y, w, h, style="D")
            return
        if stroke.has("top"):
            self.pdf.line(x, y, x + w, y)
        if stroke.has("right"):
            self.pdf.line(x + w, y, x + w, y + h)
        if stroke.has("bottom"):
            self.pdf.line(x, y + h, x + w, y + h)
        if stroke.has("left"):
            self.pdf.line(x, y, x, y + h)

    def _box(self, node: Box, x: float, y: float, w: float, h: float) -> None:
        self._stroke_box(x, y, w, h, node.stroke, node.fill)
        pad = 0.0
        if node.padding and node.padding.unit in ("mm", "pt"):
            pad = to_mm(node.padding)
        ix, iy, iw, ih = x + pad, y + pad, max(0.0, w - 2 * pad), max(0.0, h - 2 * pad)
        child = node.child
        if child is None:
            return
        # Shrink-wrapped checkbox: honor min size and align inside the cell.
        cw, ch = iw, ih
        if node.min_w and node.min_w.unit in ("mm", "pt"):
            cw = min(iw, to_mm(node.min_w))
        if node.min_h and node.min_h.unit in ("mm", "pt"):
            ch = min(ih, to_mm(node.min_h))
        cx, cy = ix, iy
        align = node.align or ""
        if "center" in align or align == "center":
            cx = ix + (iw - cw) / 2.0
            cy = iy + (ih - ch) / 2.0
        elif "right" in align:
            cx = ix + iw - cw
            cy = iy + (ih - ch) / 2.0
        elif "left" in align or "horizon" in align:
            cy = iy + (ih - ch) / 2.0
        if node.fill == "black" and isinstance(child, Text):
            self.pdf.set_text_color(255)
        if node.rotate:
            self._rotated(node, child, x, y, w, h, cx, cy, cw, ch)
        else:
            self.place(child, cx, cy, cw, ch)
        if node.fill == "black":
            self.pdf.set_text_color(0)

    def _leaf_text(self, node: Node | None) -> Text | None:
        while isinstance(node, (Link, Anchor)):
            node = node.child
        return node if isinstance(node, Text) else None

    def _rotated(
        self,
        node: Box,
        child: Node,
        x: float,
        y: float,
        w: float,
        h: float,
        cx: float,
        cy: float,
        cw: float,
        ch: float,
    ) -> None:
        """Rotate a label around the box centre. Font is set *before* the fpdf2 rotation context so local_context cannot restore a stale size over the draw. Links stay on the unrotated box (fpdf2 does not transform annotations)."""
        text = self._leaf_text(child)
        rcx, rcy = cx + cw / 2.0, cy + ch / 2.0
        if text is not None:
            size_pt = self._font_pt(text.size)
            self.pdf.font("B" if text.bold else "", size_pt)
            if node.fill == "black" or text.color == "white":
                self.pdf.set_text_color(255)
            else:
                self.pdf.set_text_color(self._ink(text.color))
            tw = self.pdf.get_string_width(text.text)
            th = size_pt * 25.4 / 72.0
            with self.pdf.rotation(node.rotate, rcx, rcy):
                self.pdf.text(rcx - tw / 2.0, rcy + th * 0.35, text.text)
            if isinstance(child, Link):
                self._hit(x, y, w, h, child.target_id)
            elif isinstance(child, Anchor) and isinstance(child.child, Link):
                self._hit(x, y, w, h, child.child.target_id)
            return
        with self.pdf.rotation(node.rotate, rcx, rcy):
            self.place(child, cx, cy, cw, ch)

    def _col(self, node: Col, x: float, y: float, w: float, h: float) -> None:
        n = len(node.children)
        if n == 0:
            return
        gap = to_mm(node.gap) if node.gap.unit in ("mm", "pt") else 0.0
        weights = node.weights if node.weights is not None else [Length.fr(1)] * n
        autos = [self._intrinsic_h(ch, w) if wt.unit == "auto" else 0.0 for ch, wt in zip(node.children, weights)]
        heights = resolve_tracks(weights, h, gap, autos=autos)
        yy = y
        for child, ch in zip(node.children, heights):
            self.place(child, x, yy, w, ch)
            yy += ch + gap

    def _row(self, node: Row, x: float, y: float, w: float, h: float) -> None:
        n = len(node.children)
        if n == 0:
            return
        gap = to_mm(node.gap) if node.gap.unit in ("mm", "pt") else 0.0
        weights = node.weights if node.weights is not None else [Length.fr(1)] * n
        autos = [self._intrinsic_w(ch, h) if wt.unit == "auto" else 0.0 for ch, wt in zip(node.children, weights)]
        widths = resolve_tracks(weights, w, gap, autos=autos)
        xx = x
        for child, cw in zip(node.children, widths):
            self.place(child, xx, y, cw, h)
            xx += cw + gap

    def _grid(self, node: Grid, x: float, y: float, w: float, h: float) -> None:
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
            cg = to_mm(node.gutter[0]) if node.gutter[0].unit in ("mm", "pt") else 0.0
            rg = to_mm(node.gutter[1]) if node.gutter[1].unit in ("mm", "pt") else 0.0
        else:
            cg = rg = to_mm(node.gutter) if node.gutter.unit in ("mm", "pt") else 0.0
        inset = to_mm(node.inset) if node.inset and node.inset.unit in ("mm", "pt") else 0.0
        col_w = resolve_tracks(cols, w, cg)
        row_h = resolve_tracks(rows, h, rg)
        xs = [x]
        for cw in col_w[:-1]:
            xs.append(xs[-1] + cw + cg)
        ys = [y]
        for rh in row_h[:-1]:
            ys.append(ys[-1] + rh + rg)
        for cell in cells:
            if cell.col is None or cell.row is None:
                continue
            cx = xs[cell.col]
            cy = ys[cell.row]
            cw = sum(col_w[cell.col : cell.col + cell.colspan]) + cg * max(0, cell.colspan - 1)
            ch = sum(row_h[cell.row : cell.row + cell.rowspan]) + rg * max(0, cell.rowspan - 1)
            self._stroke_box(cx, cy, cw, ch, cell.stroke, cell.fill)
            ix, iy = cx + inset, cy + inset
            iw, ih = max(0.0, cw - 2 * inset), max(0.0, ch - 2 * inset)
            child = cell.child
            if cell.fill == "black":
                self.pdf.set_text_color(255)
            if cell.align and isinstance(child, Text) and not child.align:
                child = Text(child.text, size=child.size, bold=child.bold, color=child.color, align=cell.align)
            self.place(child, ix, iy, iw, ih)
            if cell.fill == "black":
                self.pdf.set_text_color(0)

    def _dots(self, x: float, y: float, w: float, h: float) -> None:
        if w < 0.3 or h < 0.3:
            return
        pdf = self.pdf
        if pdf._dot_path is None:
            pdf._dot_path = _write_dot_tile(pdf._tmp / "dots.png", to_mm(self.styles.regular_height))
        tile = pdf._dot_tile_mm
        with pdf.rect_clip(x, y, w, h):
            yy = y
            while yy < y + h - 0.01:
                xx = x
                while xx < x + w - 0.01:
                    pdf.image(str(pdf._dot_path), x=xx, y=yy, w=tile, h=tile)
                    xx += tile
                yy += tile

    def _intrinsic_h(self, node: Node | None, width: float) -> float:
        if node is None:
            return 0.0
        if isinstance(node, Text):
            size_pt = self._font_pt(node.size)
            lines = node.text.count("\n") + 1
            return (size_pt * 25.4 / 72.0) * 1.15 * lines
        if isinstance(node, Spacer):
            return to_mm(node.size) if node.size and node.size.unit in ("mm", "pt") else 0.0
        if isinstance(node, DottedPad):
            return 0.0
        if isinstance(node, (Link, Anchor)):
            return self._intrinsic_h(node.child, width)
        if isinstance(node, Box):
            pad = to_mm(node.padding) if node.padding and node.padding.unit in ("mm", "pt") else 0.0
            child_h = self._intrinsic_h(node.child, max(0.0, width - 2 * pad))
            h = child_h + 2 * pad
            if node.min_h and node.min_h.unit in ("mm", "pt"):
                h = max(h, to_mm(node.min_h))
            return h
        if isinstance(node, Col):
            gap = to_mm(node.gap) if node.gap.unit in ("mm", "pt") else 0.0
            weights = node.weights or [Length.auto()] * len(node.children)
            total = gap * max(0, len(node.children) - 1)
            for child, wt in zip(node.children, weights):
                if wt.unit == "fr":
                    continue
                if wt.unit in ("mm", "pt"):
                    total += to_mm(wt)
                else:
                    total += self._intrinsic_h(child, width)
            return total
        if isinstance(node, Row):
            return max((self._intrinsic_h(c, width) for c in node.children), default=0.0)
        if isinstance(node, Grid):
            rows = list(node.rows)
            if isinstance(node.gutter, tuple):
                rg = to_mm(node.gutter[1]) if node.gutter[1].unit in ("mm", "pt") else 0.0
            else:
                rg = to_mm(node.gutter) if node.gutter.unit in ("mm", "pt") else 0.0
            total = rg * max(0, len(rows) - 1)
            for row in rows:
                if row.unit in ("mm", "pt"):
                    total += to_mm(row)
            return total
        return 0.0

    def _intrinsic_w(self, node: Node | None, height: float) -> float:
        if node is None:
            return 0.0
        if isinstance(node, Text):
            size_pt = self._font_pt(node.size)
            self.pdf.font("B" if node.bold else "", size_pt)
            lines = _latin1(node.text).split("\n")
            return max((self.pdf.get_string_width(line) for line in lines), default=0.0) + 1.2
        if isinstance(node, Spacer):
            return to_mm(node.size) if node.size and node.size.unit in ("mm", "pt") else 0.0
        if isinstance(node, (Link, Anchor)):
            return self._intrinsic_w(node.child, height)
        if isinstance(node, Box):
            pad = to_mm(node.padding) if node.padding and node.padding.unit in ("mm", "pt") else 0.0
            child_w = self._intrinsic_w(node.child, height)
            w = child_w + 2 * pad
            if node.min_w and node.min_w.unit in ("mm", "pt"):
                w = max(w, to_mm(node.min_w))
            return w
        if isinstance(node, Row):
            gap = to_mm(node.gap) if node.gap.unit in ("mm", "pt") else 0.0
            weights = node.weights or [Length.auto()] * len(node.children)
            total = gap * max(0, len(node.children) - 1)
            for child, wt in zip(node.children, weights):
                if wt.unit == "fr":
                    continue
                if wt.unit in ("mm", "pt"):
                    total += to_mm(wt)
                else:
                    total += self._intrinsic_w(child, height)
            return total
        if isinstance(node, Col):
            return max((self._intrinsic_w(c, height) for c in node.children), default=0.0)
        return 0.0
