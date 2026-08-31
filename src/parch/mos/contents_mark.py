"""Contents back-link mark: five house-stroke bars, sibling-cap stack."""

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
    glyph = f"contents_bars(size: {type_size})"
    if link_padding is None:
        return f"padded_link(<{INDEX_ID}>, {glyph})"
    return f"padded_link(padding: {link_padding}, <{INDEX_ID}>, {glyph})"


def lead_title(
    manifest: Manifest | None,
    heading_height: str,
    title: str,
    body_size: str = "8pt",
) -> str:
    """Glue the Contents mark to the left of *title* (house stack pair)."""
    mark = contents_mark(manifest, heading_height, body_size, face="h1")
    if not mark:
        return title
    return f"lead_pair({mark}, {title})"


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
        return f"lead_pair({mark}, {chip})"
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
    match edge:
        case HeadingMark.FOLLOW:
            spacing = "0.5em"
        case HeadingMark.TRAIL:
            spacing = "1fr"
        case _:
            raise ValueError(f"trail_heading edge must be TRAIL or FOLLOW, not {edge!r}")
    return f"trail_heading({title}, {mark}, spacing: {spacing}, direction: {direction})"
