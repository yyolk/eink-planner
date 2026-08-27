"""Contents back-link mark: four filled bars, header-tall tap."""

from __future__ import annotations

from typing import Any

from parch.mos.manifest import Manifest

INDEX_ID = "index"


def heading_height_token(configurator: Any) -> str:
    """House heading height, or the Typst ``h1`` token."""
    heading = None
    if configurator is not None and hasattr(configurator, "dig"):
        heading = configurator.dig("planner", "params", "heading")
    if heading is not None and hasattr(heading, "get"):
        height = heading.get("height")
        if height:
            return str(height)
    if configurator is not None and hasattr(configurator, "dig"):
        h1 = configurator.dig("document", "text", "h1")
        if h1:
            return str(h1)
    return "h1"


def body_size_token(configurator: Any) -> str:
    """House body size so mark em is a body cap, not h1."""
    if configurator is not None and hasattr(configurator, "dig"):
        size = configurator.dig("document", "text", "size")
        if size:
            return str(size)
    return "8pt"


def contents_mark(
    manifest: Manifest | None,
    heading_height: str,
    body_size: str = "8pt",
) -> str:
    """Four filled bars linking to Contents, or empty when index is off."""
    if manifest is None or not manifest.source(INDEX_ID):
        return ""
    bar = "rect(width: 1.2em, height: 0.7mm, fill: black)"
    glyph = f"""text(size: {body_size}, box(
  width: 1.2em,
  height: {heading_height},
  align(horizon + left, stack(
    dir: ttb,
    spacing: 0.35mm,
    {bar},
    {bar},
    {bar},
    {bar},
  ))
))"""
    return f"padded_link(<{INDEX_ID}>, {glyph})"


def lead_title(
    manifest: Manifest | None,
    heading_height: str,
    title: str,
    body_size: str = "8pt",
) -> str:
    """Glue the Contents mark to the left of *title* (two-column grid)."""
    mark = contents_mark(manifest, heading_height, body_size)
    if not mark:
        return title
    return (
        "grid(\n"
        "  columns: (auto, auto),\n"
        "  column-gutter: 6pt,\n"
        "  align: horizon,\n"
        f"  {mark},\n"
        f"  {title}\n"
        ")"
    )


def trail_strip(
    manifest: Manifest | None,
    heading_height: str,
    body_size: str = "8pt",
    chip: str | None = None,
) -> str | None:
    """Mark immediately left of *chip*, flush to the MOS strip."""
    mark = contents_mark(manifest, heading_height, body_size)
    if mark and chip:
        return (
            "grid(\n"
            "  columns: (auto, auto),\n"
            "  column-gutter: 6pt,\n"
            "  align: horizon,\n"
            f"  {mark},\n"
            f"  {chip}\n"
            ")"
        )
    return mark or chip

