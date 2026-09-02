"""Frame Typst sample pages in a device line-drawing catalog."""

import re
from collections.abc import Sequence
from pathlib import Path
from xml.etree import ElementTree as ET

from parch.device_frame import frame_svg
from parch.devices import Device
from parch.services.preview_svg import SAMPLE_STEMS, _root_open_tag, _split_length

_ATTR = re.compile(r'\b([:\w]+)="([^"]*)"')


def specimens_dest(workdir: str | Path, device_id: str) -> Path:
    """Catalog dir: ``<workdir>/specimens/<device-id>/``."""
    return Path(workdir) / "specimens" / device_id


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _screen_el(frame: str) -> ET.Element:
    root = ET.fromstring(frame)
    for el in root.iter():
        if el.get("id") == "screen":
            return el
    raise ValueError("frame has no #screen")


def _attr(tag: str, name: str) -> str | None:
    match = re.search(rf'\b{re.escape(name)}="([^"]*)"', tag)
    return match.group(1) if match else None


def _xmlns_extras(tag: str) -> str:
    extras: list[str] = []
    for name, value in _ATTR.findall(tag):
        if name.startswith("xmlns:"):
            extras.append(f' {name}="{value}"')
    return "".join(extras)


def compose_specimen(frame: str, page: str) -> str:
    """Nest a page SVG at #screen; sizes already match, so do not stretch."""
    screen = _screen_el(frame)
    sx = screen.get("x") or "0"
    sy = screen.get("y") or "0"
    sw = screen.get("width") or "0"
    sh = screen.get("height") or "0"
    tag, _start, end = _root_open_tag(page)
    close = page.rfind("</svg>")
    if close < 0:
        raise ValueError("page is not an SVG document")
    viewbox = _attr(tag, "viewBox")
    if viewbox is None:
        width = _attr(tag, "width")
        height = _attr(tag, "height")
        if not width or not height:
            raise ValueError("page SVG needs viewBox or width/height")
        vw, _wu = _split_length(width)
        vh, _hu = _split_length(height)
        viewbox = f"0 0 {vw} {vh}"
    nested = (
        f'<svg x="{sx}" y="{sy}" width="{sw}" height="{sh}"'
        f' viewBox="{viewbox}"{_xmlns_extras(tag)}>'
        f"{page[end:close]}"
        f"</svg>"
    )
    insert = frame.rfind("</svg>")
    if insert < 0:
        raise ValueError("frame is not an SVG document")
    return frame[:insert] + nested + "\n" + frame[insert:]


def framed_specimen(device: Device, page: str) -> str:
    """Compose a page into ``frame_svg(device)``; unknown ids raise."""
    return compose_specimen(frame_svg(device), page)


def specimen_index_html(device_id: str, stems: Sequence[str] = SAMPLE_STEMS) -> str:
    """Dumb catalog page that lists each framed sample."""
    figures = [
        f'<figure><img src="{stem}.svg" alt="{stem}"><figcaption>{stem}</figcaption></figure>'
        for stem in stems
    ]
    return (
        "<!DOCTYPE html>\n"
        f"<title>parch specimens — {device_id}</title>\n"
        "<style>figure{display:inline-block;margin:1rem;vertical-align:top}"
        "img{width:16rem;height:auto}</style>\n"
        + "\n".join(figures)
        + "\n"
    )


def write_specimens(
    dest: Path,
    device: Device,
    pages: dict[str, str],
    *,
    stems: Sequence[str] = SAMPLE_STEMS,
) -> Path:
    """Write framed sample SVGs and index.html under *dest*."""
    dest.mkdir(parents=True, exist_ok=True)
    chrome = frame_svg(device)
    for stem in stems:
        (dest / f"{stem}.svg").write_text(
            compose_specimen(chrome, pages[stem]),
            encoding="utf-8",
        )
    index = dest / "index.html"
    index.write_text(specimen_index_html(device.id, stems), encoding="utf-8")
    return index
