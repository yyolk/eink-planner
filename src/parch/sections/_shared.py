"""Shared layout tokens used by more than one MOS section."""

import re

_LENGTH = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))(mm|cm|pt)$")
# Review week field only — do not touch global `#let lined` (luma grey).
_REVIEW_LINED = """place(
  line(
    start: (0%, regular_height - 0.15mm),
    end: (100%, regular_height - 0.15mm),
    stroke: regular_stroke + black
  )
)"""


def _length_mm(token: str) -> float:
    """Parse a Typst length token (`mm` / `cm` / `pt`) into millimetres."""
    text = str(token).strip()
    match = _LENGTH.fullmatch(text)
    if match is None:
        raise ValueError(f"unrecognized length token: {token!r}")
    value = float(match.group(1))
    unit = match.group(2)
    if unit == "mm":
        return value
    if unit == "cm":
        return value * 10.0
    return value * 25.4 / 72.0
