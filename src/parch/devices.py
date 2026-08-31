"""Named e-ink device records: id, ppi, mm lengths, and toolbar-edge."""

from dataclasses import dataclass

MM_PER_INCH = 25.4
PT_PER_INCH = 72.0

TOOLBAR_TOP = "top"
TOOLBAR_NONE = "none"
TOOLBAR_EDGES = frozenset({TOOLBAR_TOP, TOOLBAR_NONE})


def _mm_number(token: str) -> float:
    text = token.strip()
    if text.endswith("mm"):
        text = text[:-2]
    return float(text)


@dataclass(frozen=True)
class Device:
    """Physical page used as a planner size. ppi stays Python-side."""

    id: str
    name: str
    ppi: int
    page_width: str
    page_height: str
    toolbar_edge: str
    toolbar_clearance: str
    writing_clearance: str
    mos_width: str

    def __post_init__(self) -> None:
        if self.toolbar_edge not in TOOLBAR_EDGES:
            raise ValueError("toolbar-edge: top or none")

    @property
    def slug(self) -> str:
        return self.id

    @property
    def width_mm(self) -> float:
        return round(_mm_number(self.page_width), 2)

    @property
    def height_mm(self) -> float:
        return round(_mm_number(self.page_height), 2)

    @property
    def width_pt(self) -> float:
        return round(self.width_mm / MM_PER_INCH * PT_PER_INCH, 2)

    @property
    def height_pt(self) -> float:
        return round(self.height_mm / MM_PER_INCH * PT_PER_INCH, 2)

    def page_size_mm(self) -> tuple[str, str]:
        return (self.page_width, self.page_height)

    def scale(self) -> dict[str, str]:
        return {
            "width": self.page_width,
            "height": self.page_height,
            "toolbar_edge": self.toolbar_edge,
            "toolbar_clearance": self.toolbar_clearance,
            "writing_clearance": self.writing_clearance,
            "mos_width": self.mos_width,
        }


# SuperNote Nomad (A6 X2): 1404×1872 @ 300 PPI → 118.87×158.50 mm. Toolbar top 8mm.
SUPERNOTE_NOMAD = Device(
    id="supernote-nomad",
    name="SuperNote Nomad",
    ppi=300,
    page_width="118.87mm",
    page_height="158.5mm",
    toolbar_edge=TOOLBAR_TOP,
    toolbar_clearance="8mm",
    writing_clearance="4mm",
    mos_width="8mm",
)

# Kindle Scribe: 1860×2480 @ 300 PPI → 157.48×209.97 mm. No toolbar.
KINDLE_SCRIBE = Device(
    id="kindle-scribe",
    name="Kindle Scribe",
    ppi=300,
    page_width="157.48mm",
    page_height="209.97mm",
    toolbar_edge=TOOLBAR_NONE,
    toolbar_clearance="5mm",
    writing_clearance="5mm",
    mos_width="10mm",
)

# 158×210 mm paper size. No toolbar.
PAPER_158X210 = Device(
    id="158x210",
    name="158 × 210",
    ppi=300,
    page_width="158mm",
    page_height="210mm",
    toolbar_edge=TOOLBAR_NONE,
    toolbar_clearance="5mm",
    writing_clearance="5mm",
    mos_width="10mm",
)

DEVICES: tuple[Device, ...] = (SUPERNOTE_NOMAD, KINDLE_SCRIBE, PAPER_158X210)

PRESETS: dict[str, Device] = {
    SUPERNOTE_NOMAD.id: SUPERNOTE_NOMAD,
    KINDLE_SCRIBE.id: KINDLE_SCRIBE,
    PAPER_158X210.id: PAPER_158X210,
    "nomad": SUPERNOTE_NOMAD,
    "scribe": KINDLE_SCRIBE,
}

DEFAULT_DEVICE = SUPERNOTE_NOMAD


def known_device_ids() -> tuple[str, ...]:
    return tuple(d.id for d in DEVICES)


def get_device(spec: str) -> Device:
    key = spec.strip().lower()
    if key not in PRESETS:
        known = ", ".join(known_device_ids())
        raise KeyError(f"unknown device {spec!r}; known: {known}")
    return PRESETS[key]
