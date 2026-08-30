"""Contents back-link mark: five house-stroke bars, sibling-cap stack."""

from __future__ import annotations

from typing import Any

from parch.compose.page_data import HeadingMark
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
    """House body size for raw pages whose sibling type is body."""
    if configurator is not None and hasattr(configurator, "dig"):
        size = configurator.dig("document", "text", "size")
        if size:
            return str(size)
    return "8pt"


def contents_mark(
    manifest: Manifest | None,
    heading_height: str | None,
    body_size: str = "8pt",
    face: str | None = None,
    link_padding: str | None = None,
) -> str:
    """Five house-stroke bars linking to Contents, or empty when index is off."""
    if manifest is None or not manifest.source(INDEX_ID):
        return ""
    type_size = face or "h1"
    bar = "line(length: 0.844em, stroke: thick_stroke + black)"
    glyph = f"""text(size: {type_size}, context {{
  let cap = 0.7em.to-absolute()
  let gap = (cap - 5 * thick_stroke) / 4
  box(
    width: 0.844em,
    height: cap,
    align(horizon + left, stack(
      dir: ttb,
      spacing: gap,
      {bar},
      {bar},
      {bar},
      {bar},
      {bar},
    ))
  )
}})"""
    if link_padding is None:
        return f"padded_link(<{INDEX_ID}>, {glyph})"
    return f"padded_link(padding: {link_padding}, <{INDEX_ID}>, {glyph})"


def lead_title(
    manifest: Manifest | None,
    heading_height: str,
    title: str,
    body_size: str = "8pt",
) -> str:
    """Glue the Contents mark to the left of *title* (two-column grid)."""
    mark = contents_mark(manifest, heading_height, body_size, face="h1")
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
    # Flush to the MOS strip: do not let padded_link inset paint on Q1.
    mark = contents_mark(
        manifest, heading_height, body_size, face="h1",
        link_padding=None if chip else "0pt",
    )
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
    if mark and not chip:
        return f"pad(right: 3mm, {mark})"
    return mark or chip


def trail_heading(
    manifest: Manifest | None,
    heading_height: str,
    title: str | None,
    body_size: str = "8pt",
    *,
    direction: str = "ltr",
    chip: str | None = None,
    edge: HeadingMark = HeadingMark.TRAIL,
) -> str:
    """TRAIL is 1fr opposite-ends; FOLLOW is 0.5em after the mark, own hits."""
    mark = trail_strip(manifest, heading_height, body_size, chip)
    if not title:
        return mark or ""
    if not mark:
        return title
    if edge is HeadingMark.FOLLOW:
        spacing = "0.5em"
    elif edge is HeadingMark.TRAIL:
        spacing = "1fr"
    else:
        raise ValueError(f"trail_heading edge must be TRAIL or FOLLOW, not {edge!r}")
    return f"""context {{
  let seated_title = {title}
  let seated_mark = {mark}
  let band = calc.max(measure(seated_title).height, measure(seated_mark).height)
  stack(
    dir: {direction},
    spacing: {spacing},
    box(height: band, align(horizon + left, seated_title)),
    box(height: band, align(horizon + left, seated_mark)),
  )
}}"""
