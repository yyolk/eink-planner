"""Assemble preamble + section pages; chase and compose share render() for one manifest."""

from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.mos.navigation import NavLink, Navigation
from parch.compose.page_data import HeadingMark, PageData
from parch.mos.contents_mark import body_size_token, lead_title, trail_heading
from parch.mos.preamble import Preamble


class Builder:
    def __init__(self, i18n: I18n, configurator: Configurator, manifest: Manifest) -> None:
        self.configurator = configurator
        self.manifest = manifest
        self.pages: list[str] = []
        self.preamble = Preamble(configurator)
        self.navigation = Navigation(i18n=i18n, manifest=manifest, configurator=configurator)
        self.mos_layout = configurator.dig_bang("planner", "params", "mos_layout")
        self.heading = configurator.dig_bang("planner", "params", "heading")

    def generate(self) -> str:
        body = "\n#pagebreak()\n".join(self.pages)
        return f"{self.preamble.generate()}\n{self._mos_strip_bind()}\n{body}"

    def _mos_strip_bind(self) -> str:
        months = self.navigation.year_month_items()
        quarters = self.navigation.year_quarter_items()
        reverse = "true" if _v(self.mos_layout, "reverse_months_quarters") else "false"
        return (
            "#let mos_strip = mos_strip.with("
            f"months: {months}, quarters: {quarters}, reverse: {reverse})"
        )

    def render(self, page: PageData) -> str:
        if page.raw_typst:
            return page.content
        return self._layout_page(page)

    def add(self, page_spec: PageData) -> str:
        typst = self.render(page_spec)
        self.pages.append(typst)
        return typst

    def _layout_page(self, page_spec: PageData) -> str:
        side = _v(self.mos_layout, "side_menu_position")
        mos = self.navigation.side_menu_cell(
            highlight_months=page_spec.highlight_months,
            highlight_quarters=page_spec.highlight_quarters,
            month_link_id=page_spec.month_link_id,
            show_quarters=page_spec.show_quarters,
        )
        heading = self._heading_stack(
            page_spec.page_id,
            page_spec.title,
            page_spec.nav_links,
            page_spec.heading_mark,
        )
        return f"""#mos_frame(
  {side},
  {mos},
  well_frame(
    {heading or "[]"},
    {page_spec.content},
  ),
)"""

    def _heading_stack(
        self,
        page_id: str | None,
        title: str | None,
        nav_links: list[tuple[str, str] | NavLink] | None = None,
        heading_mark: HeadingMark = HeadingMark.LEAD,
    ) -> str:
        chip = self.navigation.heading_menu_grid(page_id=page_id, nav_links=nav_links)
        height = _v(self.heading, "height")
        body = body_size_token(self.configurator)
        if chip:
            return trail_heading(
                self.manifest, height, title, body,
                chip=chip, edge=HeadingMark.TRAIL,
            )
        match heading_mark:
            case HeadingMark.FOLLOW:
                return trail_heading(
                    self.manifest, height, title, body,
                    edge=HeadingMark.FOLLOW,
                )
            case HeadingMark.TRAIL:
                return trail_heading(
                    self.manifest, height, title, body,
                    edge=HeadingMark.TRAIL,
                )
            case HeadingMark.LEAD:
                return lead_title(self.manifest, height, title, body) if title else ""
            case _:
                raise ValueError(f"heading_mark must be FOLLOW, TRAIL, or LEAD, not {heading_mark!r}")


def _v(mapping, key: str):
    return mapping[key]
