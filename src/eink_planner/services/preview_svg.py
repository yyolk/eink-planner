"""Shrink Typst SVG pages for previews (third-scale or crop)."""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

_LENGTH = re.compile(
    r"^\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Z%]*)\s*$"
)
_MATRIX = re.compile(
    r"matrix\(\s*([^\s,]+)[\s,]+([^\s,]+)[\s,]+([^\s,]+)[\s,]+"
    r"([^\s,]+)[\s,]+([^\s,]+)[\s,]+([^\s,]+)\s*\)"
)
_TRANSLATE = re.compile(
    r"translate\(\s*([^\s,]+)(?:[\s,]+([^\s,]+))?\s*\)"
)
# SVG matrix (a b c d e f): x' = a x + c y + e, y' = b x + d y + f
_IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
DEFAULT_SCALE = 1 / 3


def parse_pages(spec: str) -> list[int]:
    """Parse a Typst-style page spec (``1,3-5``) into 1-based page numbers."""
    pages: list[int] = []
    seen: set[int] = set()
    for part in spec.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            start_s, end_s = token.split("-", 1)
            start, end = int(start_s), int(end_s)
            if start < 1 or end < start:
                raise ValueError(f"bad page range {token!r}")
            chunk = range(start, end + 1)
        else:
            n = int(token)
            if n < 1:
                raise ValueError(f"page numbers are 1-based, got {n}")
            chunk = (n,)
        for n in chunk:
            if n not in seen:
                seen.add(n)
                pages.append(n)
    if not pages:
        raise ValueError("need at least one page")
    return pages


def format_pages(pages: list[int]) -> str:
    """Turn page numbers back into a compact ``--pages`` spec."""
    if not pages:
        raise ValueError("need at least one page")
    return ",".join(str(n) for n in pages)


def _split_length(value: str) -> tuple[float, str]:
    match = _LENGTH.match(value)
    if not match:
        raise ValueError(f"unparsed length {value!r}")
    return float(match.group(1)), match.group(2)


def _root_open_tag(svg: str) -> tuple[str, int, int]:
    start = svg.find("<svg")
    if start < 0:
        raise ValueError("not an SVG document")
    end = svg.find(">", start)
    if end < 0:
        raise ValueError("unterminated <svg> tag")
    return svg[start : end + 1], start, end + 1


def _set_attr(tag: str, name: str, value: str) -> str:
    pattern = re.compile(rf'\b{name}="[^"]*"')
    if pattern.search(tag):
        return pattern.sub(f'{name}="{value}"', tag, count=1)
    if tag.endswith("/>"):
        return f'{tag[:-2]} {name}="{value}"/>'
    return f'{tag[:-1]} {name}="{value}">'


def scale_svg(svg: str, factor: float = DEFAULT_SCALE) -> str:
    """Keep ``viewBox``; shrink ``width`` / ``height`` by ``factor`` (1/3 default)."""
    if factor <= 0:
        raise ValueError(f"scale factor must be positive, got {factor}")
    tag, start, end = _root_open_tag(svg)
    width_m = re.search(r'\bwidth="([^"]+)"', tag)
    height_m = re.search(r'\bheight="([^"]+)"', tag)
    if width_m:
        n, unit = _split_length(width_m.group(1))
        tag = _set_attr(tag, "width", f"{n * factor}{unit}")
    if height_m:
        n, unit = _split_length(height_m.group(1))
        tag = _set_attr(tag, "height", f"{n * factor}{unit}")
    return svg[:start] + tag + svg[end:]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def _compose(parent: tuple[float, ...], child: tuple[float, ...]) -> tuple[float, ...]:
    a1, b1, c1, d1, e1, f1 = parent
    a2, b2, c2, d2, e2, f2 = child
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _apply(m: tuple[float, ...], x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = m
    return a * x + c * y + e, b * x + d * y + f


def _parse_transform(value: str | None) -> tuple[float, ...]:
    if not value:
        return _IDENT
    current = _IDENT
    pos = 0
    while pos < len(value):
        rest = value[pos:]
        m = _MATRIX.match(rest)
        if m:
            current = _compose(current, tuple(float(g) for g in m.groups()))
            pos += m.end()
            continue
        t = _TRANSLATE.match(rest)
        if t:
            tx = float(t.group(1))
            ty = float(t.group(2) or 0.0)
            current = _compose(current, (1.0, 0.0, 0.0, 1.0, tx, ty))
            pos += t.end()
            continue
        pos += 1
    return current


def _content_points(svg: str) -> list[tuple[float, float]]:
    """Page-space positions of ``<use>`` after Typst's group matrices."""
    root = ET.fromstring(svg)
    points: list[tuple[float, float]] = []

    def walk(el: ET.Element, m: tuple[float, ...]) -> None:
        if _local_name(el.tag) == "defs":
            return
        m = _compose(m, _parse_transform(el.get("transform")))
        if _local_name(el.tag) == "use":
            x = float(el.get("x") or 0.0)
            y = float(el.get("y") or 0.0)
            points.append(_apply(m, x, y))
        for child in el:
            walk(child, m)

    walk(root, _IDENT)
    return points


def crop_svg(svg: str, pad: float = 32.0) -> str:
    """Tighten ``viewBox`` to transformed ``use`` points, plus glyph ``pad``.

    Typst flips Y with ``matrix(1 0 0 -1 tx ty)`` on a parent ``<g>``, so
    raw ``use`` coordinates stay on ``y="0"``. Walk the transform stack.
    Full MOS pages still land near page-sized; crop mainly helps sparse
    pages (cover, quiet colophon).
    """
    points = _content_points(svg)
    if not points:
        raise ValueError("no placed content to crop")
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs) - pad, max(xs) + pad
    min_y, max_y = min(ys) - pad, max(ys) + pad
    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)
    tag, start, end = _root_open_tag(svg)
    w_attr = re.search(r'\bwidth="([^"]+)"', tag)
    unit = _split_length(w_attr.group(1))[1] if w_attr else ""
    tag = _set_attr(tag, "viewBox", f"{min_x} {min_y} {width} {height}")
    tag = _set_attr(tag, "width", f"{width}{unit}")
    tag = _set_attr(tag, "height", f"{height}{unit}")
    return svg[:start] + tag + svg[end:]


def preview_svg(svg: str, *, scale: float = DEFAULT_SCALE, crop: bool = False) -> str:
    """Crop first (optional), then scale. Scale-only keeps the full page."""
    out = crop_svg(svg) if crop else svg
    if scale != 1:
        out = scale_svg(out, scale)
    return out
