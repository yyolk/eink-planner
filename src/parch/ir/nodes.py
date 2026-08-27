"""Small layout-tree node set. Painters walk this; MOS builds it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Literal, Union

Unit = Literal["mm", "pt", "fr", "auto"]
Color = Literal["black", "white", "gray"]
Side = Literal["all", "top", "right", "bottom", "left"]


@dataclass(frozen=True)
class Length:
    value: float
    unit: Unit = "mm"

    @classmethod
    def mm(cls, value: float) -> Length:
        return cls(float(value), "mm")

    @classmethod
    def pt(cls, value: float) -> Length:
        return cls(float(value), "pt")

    @classmethod
    def fr(cls, value: float = 1.0) -> Length:
        return cls(float(value), "fr")

    @classmethod
    def auto(cls) -> Length:
        return cls(0.0, "auto")

    def __str__(self) -> str:
        if self.unit == "auto":
            return "auto"
        if self.value == int(self.value):
            return f"{int(self.value)}{self.unit}"
        return f"{self.value}{self.unit}"


MM0 = Length.mm(0)
AUTO = Length.auto()
FR1 = Length.fr(1)


@dataclass(frozen=True)
class Stroke:
    width: Length | None = None
    color: Color = "black"
    sides: tuple[Side, ...] = ("all",)

    def has(self, side: Side) -> bool:
        return "all" in self.sides or side in self.sides


@dataclass
class Cell:
    """One grid cell. ``col`` / ``row`` are 0-based; omit to pack row-major."""

    child: Node
    col: int | None = None
    row: int | None = None
    colspan: int = 1
    rowspan: int = 1
    align: str | None = None
    fill: Color | None = None
    stroke: Stroke | None = None


@dataclass
class Page:
    """One planner page. ``body`` is the whole page (chrome included when framed)."""

    id: str | None
    body: Node
    title: Node | None = None
    highlight_months: list = field(default_factory=list)
    highlight_quarters: list = field(default_factory=list)
    chrome: bool = True


@dataclass
class Col:
    """Vertical stack. ``weights`` are per-child (fr / fixed / auto). None → equal fr."""

    children: list[Node]
    gap: Length = MM0
    weights: list[Length] | None = None


@dataclass
class Row:
    """Horizontal stack. Same weight rules as ``Col``."""

    children: list[Node]
    gap: Length = MM0
    weights: list[Length] | None = None


@dataclass
class Grid:
    cols: list[Length]
    rows: list[Length]
    cells: list[Node | Cell]
    gutter: Length | tuple[Length, Length] = MM0
    align: str | None = None
    inset: Length | None = None


@dataclass
class Box:
    child: Node | None = None
    padding: Length = MM0
    stroke: Stroke | None = None
    fill: Color | None = None
    align: str | None = None
    min_w: Length | None = None
    min_h: Length | None = None
    rotate: float | None = None  # degrees, clockwise-positive like Typst


@dataclass
class Text:
    text: str
    size: Length | None = None
    bold: bool = False
    color: Color = "black"
    align: str | None = None


@dataclass
class Link:
    target_id: str
    child: Node


@dataclass
class Anchor:
    id: str
    child: Node


@dataclass
class DottedPad:
    """Semantic dotted scratch area. Painters pick a tile / Typst tiling."""


@dataclass
class Spacer:
    size: Length | None = None


Node = Union[Col, Row, Grid, Box, Text, Link, Anchor, DottedPad, Spacer]


def children_of(node: Node | None) -> list[Node]:
    if node is None:
        return []
    if isinstance(node, (Link, Anchor)):
        return [node.child] if node.child is not None else []
    if isinstance(node, Box):
        return [node.child] if node.child is not None else []
    if isinstance(node, (Col, Row)):
        return list(node.children)
    if isinstance(node, Grid):
        out: list[Node] = []
        for cell in node.cells:
            out.append(cell.child if isinstance(cell, Cell) else cell)
        return out
    return []


def walk(node: Node | None) -> Iterator[Node]:
    if node is None:
        return
    yield node
    for child in children_of(node):
        yield from walk(child)


def collect_anchors(node: Node | None) -> list[str]:
    return [n.id for n in walk(node) if isinstance(n, Anchor)]


def collect_links(node: Node | None) -> list[str]:
    return [n.target_id for n in walk(node) if isinstance(n, Link)]


def pack_cells(items: list[Node | Cell], ncols: int) -> list[Cell]:
    """Row-major pack. Honours colspan/rowspan; fills holes left by spans."""
    occupied: set[tuple[int, int]] = set()
    cells: list[Cell] = []
    r = c = 0

    def advance() -> None:
        nonlocal r, c
        while (r, c) in occupied:
            c += 1
            if c >= ncols:
                c = 0
                r += 1

    for item in items:
        if isinstance(item, Cell) and item.col is not None and item.row is not None:
            cell = item
        else:
            advance()
            if isinstance(item, Cell):
                cell = Cell(
                    child=item.child,
                    col=c,
                    row=r,
                    colspan=item.colspan,
                    rowspan=item.rowspan,
                    align=item.align,
                    fill=item.fill,
                    stroke=item.stroke,
                )
            else:
                cell = Cell(child=item, col=c, row=r)
        assert cell.col is not None and cell.row is not None
        for rr in range(cell.row, cell.row + cell.rowspan):
            for cc in range(cell.col, cell.col + cell.colspan):
                occupied.add((rr, cc))
        cells.append(cell)
        if item is cell or (isinstance(item, Cell) and item.col is not None):
            c = cell.col + cell.colspan
            r = cell.row
            if c >= ncols:
                c = 0
                r += 1
        else:
            c = cell.col + cell.colspan
            r = cell.row
            if c >= ncols:
                c = 0
                r += 1
    return cells


def grid_extent(cells: list[Cell], min_cols: int = 0, min_rows: int = 0) -> tuple[int, int]:
    cols = min_cols
    rows = min_rows
    for cell in cells:
        if cell.col is None or cell.row is None:
            continue
        cols = max(cols, cell.col + cell.colspan)
        rows = max(rows, cell.row + cell.rowspan)
    return cols, rows
