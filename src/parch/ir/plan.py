"""PlannerDoc: page size, margins, styles, and the page list."""

from __future__ import annotations

from dataclasses import dataclass

from parch.ir.nodes import Length, Page
from parch.ir.units import parse
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest


@dataclass(frozen=True)
class Styles:
    text_size: Length
    h1: Length
    regular_stroke: Length
    thick_stroke: Length
    regular_height: Length
    regular_column_gutter: Length
    link_padding: Length
    scratch_pad: str
    side_menu_width: Length
    side_menu_position: str
    column_gutter: Length
    row_gutter: Length
    heading_height: Length
    heading_align: str
    menu_rotate: float
    reverse_mq: bool
    reverse_mq_items: bool

    @classmethod
    def from_configurator(cls, cfg: Configurator) -> Styles:
        p = cfg.dig_bang("planner", "params")
        mos = cfg.dig_bang("planner", "params", "mos_layout")
        heading = cfg.dig_bang("planner", "params", "heading")
        rotate_raw = str(mos["menu_rotate"]).lower().replace("deg", "").strip()
        try:
            rotate = float(rotate_raw)
        except ValueError:
            rotate = 270.0
        return cls(
            text_size=parse(cfg.dig_bang("document", "text", "size")),
            h1=parse(cfg.dig_bang("document", "text", "h1")),
            regular_stroke=parse(p["regular_stroke"]),
            thick_stroke=parse(p["thick_stroke"]),
            regular_height=parse(p["regular_height"]),
            regular_column_gutter=parse(p["regular_column_gutter"]),
            link_padding=parse(p["link_padding"]),
            scratch_pad=str(p["scratch_pad"]),
            side_menu_width=parse(mos["side_menu_width"]),
            side_menu_position=str(mos["side_menu_position"]).lower(),
            column_gutter=parse(mos["column_gutter"]),
            row_gutter=parse(mos["row_gutter"]),
            heading_height=parse(heading["height"]),
            heading_align=str(heading.get("align", "horizon")),
            menu_rotate=rotate,
            reverse_mq=bool(mos["reverse_months_quarters"]),
            reverse_mq_items=bool(mos["reverse_months_quarters_items"]),
        )


@dataclass
class PlannerDoc:
    page_w: Length
    page_h: Length
    margin_top: Length
    margin_right: Length
    margin_bottom: Length
    margin_left: Length
    styles: Styles
    pages: list[Page]
    manifest: Manifest

    @classmethod
    def from_configurator(cls, cfg: Configurator, pages: list[Page], manifest: Manifest) -> PlannerDoc:
        d = cfg.dig_bang("document", "layout", "dimensions")
        m = cfg.dig_bang("document", "layout", "margin")
        return cls(
            page_w=parse(d["width"]),
            page_h=parse(d["height"]),
            margin_top=parse(m["top"]),
            margin_right=parse(m["right"]),
            margin_bottom=parse(m["bottom"]),
            margin_left=parse(m["left"]),
            styles=Styles.from_configurator(cfg),
            pages=pages,
            manifest=manifest,
        )

    def page_ids(self) -> list[str | None]:
        return [p.id for p in self.pages]
