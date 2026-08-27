"""Parse Typst-style lengths and split fr/fixed/auto tracks."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from parch.ir.nodes import Length

PT_TO_MM = 25.4 / 72.0
_TOKEN_RE = re.compile(
    r"(?P<num>[-+]?(?:\d+(?:\.\d*)?|\.\d+))\s*(?P<unit>mm|cm|in|pt|fr)?",
    re.I,
)
_AUTO_RE = re.compile(r"^\s*auto\s*$", re.I)


def pt_to_mm(pt: float) -> float:
    return float(pt) * PT_TO_MM


def mm_to_pt(mm: float) -> float:
    return float(mm) / PT_TO_MM


def parse(value: Any) -> Length:
    """Parse ``10mm`` / ``0.4pt`` / ``1fr`` / ``auto`` / bare mm numbers."""
    if isinstance(value, Length):
        return value
    if isinstance(value, bool):
        raise ValueError(f"invalid length: {value!r}")
    if isinstance(value, (int, float)):
        return Length.mm(float(value))
    text = str(value).strip()
    if not text:
        raise ValueError("empty length")
    if _AUTO_RE.match(text):
        return Length.auto()
    match = _TOKEN_RE.fullmatch(text)
    if not match:
        raise ValueError(f"invalid length: {value!r}")
    num = float(match.group("num"))
    unit = (match.group("unit") or "mm").lower()
    if unit == "cm":
        return Length.mm(num * 10.0)
    if unit == "in":
        return Length.mm(num * 25.4)
    if unit == "pt":
        return Length.pt(num)
    if unit == "fr":
        return Length.fr(num)
    return Length.mm(num)


def to_mm(length: Length) -> float:
    """Convert a physical length to millimetres. ``fr`` / ``auto`` raise."""
    if length.unit == "mm":
        return float(length.value)
    if length.unit == "pt":
        return pt_to_mm(length.value)
    raise ValueError(f"cannot convert {length.unit} to mm")


def parse_tracks(value: Any) -> list[Length]:
    """Parse a Typst track spec like ``(3fr, 5fr)`` or ``10mm, 1fr, auto``."""
    if isinstance(value, (list, tuple)):
        return [parse(v) for v in value]
    if isinstance(value, Length):
        return [value]
    text = str(value).strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        return [Length.fr(1)]
    return [parse(p) for p in parts]


def resolve_tracks(
    tracks: Sequence[Length],
    available_mm: float,
    gap_mm: float = 0.0,
    *,
    autos: Sequence[float] | None = None,
) -> list[float]:
    """One-pass split: fixed first, auto uses ``autos[i]`` (else 0), fr share the rest.

    Negative leftover is clamped to 0 — fr tracks become empty rather than
    shrinking fixed ones. That is the whole solver.
    """
    n = len(tracks)
    if n == 0:
        return []
    leftover = float(available_mm) - float(gap_mm) * max(0, n - 1)
    out: list[float | None] = [None] * n
    fr_total = 0.0
    for i, track in enumerate(tracks):
        if track.unit == "fr":
            fr_total += float(track.value)
            continue
        if track.unit == "auto":
            size = float(autos[i]) if autos is not None else 0.0
        else:
            size = to_mm(track)
        out[i] = size
        leftover -= size
    leftover = max(0.0, leftover)
    resolved: list[float] = []
    for i, track in enumerate(tracks):
        if out[i] is not None:
            resolved.append(float(out[i]))
        elif fr_total > 0:
            resolved.append(leftover * (float(track.value) / fr_total))
        else:
            resolved.append(0.0)
    return resolved
