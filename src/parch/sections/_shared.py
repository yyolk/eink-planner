"""Shared layout tokens used by more than one MOS section."""

import re

_LENGTH = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))(mm|cm|pt)$")


def _side_menu_position(configurator) -> str:
    """MOS side token for mos_frame / daily_well / month_grid."""
    mos = configurator.dig("planner", "params", "mos_layout")
    if mos is None:
        return "left"
    return mos["side_menu_position"] if "side_menu_position" in mos else "left"


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
