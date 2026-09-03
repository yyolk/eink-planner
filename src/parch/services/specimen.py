"""Frame Typst sample pages in a device line-drawing catalog."""

import re
from collections.abc import Sequence
from pathlib import Path
from xml.etree import ElementTree as ET

from parch.device_frame import FRAME_DEVICE_IDS, frame_svg
from parch.devices import Device
from parch.services.preview_svg import SAMPLE_STEMS, _root_open_tag, _split_length

_ATTR = re.compile(r'\b([:\w]+)="([^"]*)"')
_XML10_C0 = dict.fromkeys(range(0x00, 0x20))
del _XML10_C0[0x09]
del _XML10_C0[0x0A]
del _XML10_C0[0x0D]

SPECIMEN_PAPERS = ("lined", "dotted")
SPECIMEN_HANDS = ("left", "right")
PERMUTATIONS = tuple(
    f"{paper}-{hand}" for paper in SPECIMEN_PAPERS for hand in SPECIMEN_HANDS
)


def _xml10_svg(svg: str) -> str:
    """Drop C0 controls other than tab, LF, and CR so the SVG is XML 1.0."""
    return svg.translate(_XML10_C0)


def catalog_dest(workdir: str | Path) -> Path:
    """Catalog root: ``<workdir>/specimens/``."""
    return Path(workdir) / "specimens"


def specimens_dest(
    workdir: str | Path, device_id: str, perm_id: str | None = None
) -> Path:
    """Per-device or per-perm dir: ``<workdir>/specimens/<device-id>/[<perm-id>/]``."""
    dest = catalog_dest(workdir) / device_id
    if perm_id is not None:
        return dest / perm_id
    return dest


def perm_parts(perm_id: str) -> tuple[str, str]:
    """Split ``{paper}-{hand}`` into paper and hand."""
    paper, _, hand = perm_id.partition("-")
    return paper, hand


def listed_catalog_devices(root: Path) -> list[str]:
    """Device folders under the catalog root that have an index.html."""
    if not root.is_dir():
        return []
    found = {p.name for p in root.iterdir() if p.is_dir() and (p / "index.html").is_file()}
    preferred = [d for d in sorted(FRAME_DEVICE_IDS) if d in found]
    extras = sorted(found - FRAME_DEVICE_IDS)
    return preferred + extras


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


def _insert_nested(frame: str, nested: str) -> str:
    """Place the page under #toolbar when present; otherwise before </svg>."""
    mark = frame.find('id="toolbar"')
    if mark >= 0:
        insert = frame.rfind("<", 0, mark)
    else:
        insert = frame.rfind("</svg>")
    if insert < 0:
        raise ValueError("frame is not an SVG document")
    return frame[:insert] + nested + "\n" + frame[insert:]


def compose_specimen(frame: str, page: str) -> str:
    """Nest a page SVG at #screen; sizes already match, so do not stretch."""
    page = _xml10_svg(page)
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
    return _insert_nested(frame, nested)


def framed_specimen(device: Device, page: str) -> str:
    """Compose a page into ``frame_svg(device)``; unknown ids raise."""
    return compose_specimen(frame_svg(device), page)


def _catalog_style() -> str:
    return (
        "<style>figure{display:inline-block;margin:1rem;vertical-align:top}"
        "img{width:16rem;height:auto}</style>\n"
    )


def _perm_nav_list(device_ids: Sequence[str]) -> str:
    """Nested paper → hand → device links. No JS."""
    lines = ["<ul>"]
    for paper in SPECIMEN_PAPERS:
        lines.append(f"<li>{paper}")
        lines.append("<ul>")
        for hand in SPECIMEN_HANDS:
            lines.append(f"<li>{hand}")
            lines.append("<ul>")
            perm = f"{paper}-{hand}"
            for device_id in device_ids:
                lines.append(f'<li><a href="{device_id}/#{perm}">{device_id}</a></li>')
            lines.append("</ul></li>")
        lines.append("</ul></li>")
    lines.append("</ul>")
    return "\n".join(lines)


def specimen_index_html(device_id: str, stems: Sequence[str] = SAMPLE_STEMS) -> str:
    """Dumb device page: perm TOC, then four perm galleries."""
    toc = (
        "<nav>\n"
        + "\n".join(f'<a href="#{perm}">{perm}</a>' for perm in PERMUTATIONS)
        + "\n</nav>\n"
    )
    sections: list[str] = []
    for perm in PERMUTATIONS:
        figures = [
            f'<figure><img src="{perm}/{stem}.svg" alt="{stem}">'
            f"<figcaption>{stem}</figcaption></figure>"
            for stem in stems
        ]
        sections.append(
            f'<section id="{perm}">\n' + "\n".join(figures) + "</section>"
        )
    return (
        "<!DOCTYPE html>\n"
        f"<title>parch specimens — {device_id}</title>\n"
        + _catalog_style()
        + '<p><a href="../">specimens</a></p>\n'
        + toc
        + "\n".join(sections)
        + "\n"
    )


def catalog_index_html(device_ids: Sequence[str]) -> str:
    """Dumb catalog root: nested paper → hand → device list. No galleries."""
    return (
        "<!DOCTYPE html>\n"
        "<title>parch specimens</title>\n"
        + _catalog_style()
        + _perm_nav_list(device_ids)
        + "\n"
    )


def write_catalog_index(root: Path, device_ids: Sequence[str]) -> Path:
    """Write the catalog root index.html listing *device_ids*."""
    root.mkdir(parents=True, exist_ok=True)
    index = root / "index.html"
    index.write_text(catalog_index_html(device_ids), encoding="utf-8")
    return index


def write_device_index(
    dest: Path,
    device_id: str,
    *,
    stems: Sequence[str] = SAMPLE_STEMS,
) -> Path:
    """Write the per-device index.html with four perm sections."""
    dest.mkdir(parents=True, exist_ok=True)
    index = dest / "index.html"
    index.write_text(specimen_index_html(device_id, stems), encoding="utf-8")
    return index


def write_specimens(
    dest: Path,
    device: Device,
    pages: dict[str, str],
    *,
    stems: Sequence[str] = SAMPLE_STEMS,
) -> Path:
    """Write framed sample SVGs under *dest* (a perm dir)."""
    dest.mkdir(parents=True, exist_ok=True)
    chrome = frame_svg(device)
    for stem in stems:
        (dest / f"{stem}.svg").write_text(
            compose_specimen(chrome, pages[stem]),
            encoding="utf-8",
        )
    return dest
