"""Typst document preamble (page size, strokes, paper tiles, padded_link)."""

import re
from importlib.resources import files
from pathlib import Path

from parch import ConfigError
from parch.mos.configurator import Configurator

HOUSE_TYP = "house.typ"

DEVICE_TYP_PREFIXES = (
    ("supernote-nomad", "supernote-nomad.typ"),
    ("kindle-scribe", "kindle-scribe.typ"),
    ("158x210", "158x210.typ"),
)

DEVICE_TYP_BY_SIZE = {
    ("118.87mm", "158.5mm"): "supernote-nomad.typ",
    ("157.48mm", "209.97mm"): "kindle-scribe.typ",
    ("158mm", "210mm"): "158x210.typ",
}

KNOWN_DEVICE_TYP = frozenset(name for _prefix, name in DEVICE_TYP_PREFIXES)

_DEVICE_IMPORT = re.compile(
    r'#import\s+"(supernote-nomad|kindle-scribe|158x210)\.typ"'
)


def house_typ_resource():
    """Packaged house.typ (functions of tokens)."""
    return files("parch.data") / "typst" / HOUSE_TYP


def device_typ_resource(filename: str):
    """Packaged physical-device .typ (page size and page-margin)."""
    if filename not in KNOWN_DEVICE_TYP:
        raise ConfigError(f"unknown device typ: {filename}")
    return files("parch.data") / "typst" / filename


def device_typ_filename(configurator: Configurator) -> str:
    """One physical-device file: Nomad, Scribe, or 158×210. Not a MOS sibling."""
    name = configurator.dig("device")
    if name:
        filename = _filename_for_device_name(str(name))
        if filename:
            return filename
    width = configurator.dig("document", "layout", "dimensions", "width")
    height = configurator.dig("document", "layout", "dimensions", "height")
    if width and height:
        key = (_norm_len(str(width)), _norm_len(str(height)))
        if key in DEVICE_TYP_BY_SIZE:
            return DEVICE_TYP_BY_SIZE[key]
    raise ConfigError(
        "unknown physical device; expected supernote-nomad, kindle-scribe, or 158x210"
    )


def copy_device_typ(workdir: Path, filename: str) -> Path:
    """Copy one physical-device .typ next to index.typst for relative #import."""
    dest = Path(workdir) / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(device_typ_resource(filename).read_bytes())
    return dest


def copy_house_typ(workdir: Path, device_typ: str | None = None) -> Path:
    """Copy house.typ next to index.typst for relative #import.

    When *device_typ* is given, or index.typst imports a packaged device file,
    that file is copied beside house.typ.
    """
    dest = Path(workdir) / HOUSE_TYP
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(house_typ_resource().read_bytes())
    name = device_typ or _imported_device_typ(Path(workdir) / "index.typst")
    if name:
        copy_device_typ(workdir, name)
    return dest


class Preamble:
    def __init__(self, configurator: Configurator) -> None:
        self.configurator = configurator
        self.planner_params = configurator.dig_bang("planner", "params")

    def generate(self) -> str:
        p = self.planner_params
        text_size = self.configurator.dig_bang("document", "text", "size")
        h1 = self.configurator.dig_bang("document", "text", "h1")
        device_typ = device_typ_filename(self.configurator)
        mos_layout = _v(p, "mos_layout")
        heading = _v(p, "heading")
        side = _v(mos_layout, "side_menu_position")
        return f"""#import "{device_typ}": page-width, page-height, page-margin
#set page(width: page-width, height: page-height, margin: page-margin({side}))

#set text(
  size: {text_size}
)

#let regular_stroke = {_v(p, 'regular_stroke')}
#let thick_stroke = {_v(p, 'thick_stroke')}
#let regular_height = {_v(p, 'regular_height')}
#let regular_column_gutter = {_v(p, 'regular_column_gutter')}

#let h1 = {h1}
#let link_padding = {_v(p, 'link_padding')}

#import "house.typ": dotted, lined, rect_pattern, dotted_centered, rect_pattern_centered, padded_link, contents_bars, lead_pair, trail_heading, mos_frame, well_frame, month_grid, week_matrix, lined_well

#let dotted = dotted(regular_height: regular_height)
#let lined = lined(regular_height: regular_height, regular_stroke: regular_stroke)
#let rect_pattern = rect_pattern.with(regular_height: regular_height)
#let dotted_centered = dotted_centered(regular_height: regular_height)
#let rect_pattern_centered = rect_pattern_centered.with(regular_height: regular_height)
#let scratch_pad = rect_pattern({_v(p, 'scratch_pad')})
#let padded_link = padded_link.with(padding: link_padding)
#let contents_bars = contents_bars.with(thick_stroke: thick_stroke)
#let mos_frame = mos_frame.with(mos-width: {_v(mos_layout, 'side_menu_width')}, column-gutter: {_v(mos_layout, 'column_gutter')})
#let well_frame = well_frame.with(heading-height: {_v(heading, 'height')}, row-gutter: {_v(mos_layout, 'row_gutter')})
#let month_grid = month_grid.with(week-rows: 6, hline-stroke: regular_stroke + black)
#let week_matrix = week_matrix.with(regular-height: regular_height)
#let lined_well = lined_well.with(regular-height: regular_height)"""


def _v(mapping, key: str):
    if hasattr(mapping, "dig_bang"):
        return mapping[key] if key in mapping else mapping.dig_bang(key)
    return mapping[key]


def _filename_for_device_name(name: str) -> str | None:
    lowered = name.strip().lower()
    for prefix, filename in DEVICE_TYP_PREFIXES:
        if lowered == prefix or lowered.startswith(prefix + "-"):
            return filename
    return None


def _norm_len(token: str) -> str:
    return token.strip().replace(" ", "")


def _imported_device_typ(index: Path) -> str | None:
    if not index.is_file():
        return None
    match = _DEVICE_IMPORT.search(index.read_text(encoding="utf-8"))
    return f"{match.group(1)}.typ" if match else None
