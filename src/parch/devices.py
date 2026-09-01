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
    width_px: int | None = None
    height_px: int | None = None

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
        if self.width_px is not None:
            return round(self.width_px / self.ppi * PT_PER_INCH, 2)
        return round(self.width_mm / MM_PER_INCH * PT_PER_INCH, 2)

    @property
    def height_pt(self) -> float:
        if self.height_px is not None:
            return round(self.height_px / self.ppi * PT_PER_INCH, 2)
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
    width_px=1404,
    height_px=1872,
)

# Kindle Scribe: 1860×2480 @ 300 PPI → 157.48×209.97 mm. No toolbar.
KINDLE_SCRIBE = Device(
    id="kindle-scribe",
    name="Kindle Scribe",
    ppi=300,
    page_width="157.48mm",
    page_height="209.97mm",
    toolbar_edge=TOOLBAR_NONE,
    toolbar_clearance="0mm",
    writing_clearance="5mm",
    mos_width="10mm",
    width_px=1860,
    height_px=2480,
)

# 158×210 mm paper size. No toolbar.
PAPER_158X210 = Device(
    id="158x210",
    name="158 × 210",
    ppi=300,
    page_width="158mm",
    page_height="210mm",
    toolbar_edge=TOOLBAR_NONE,
    toolbar_clearance="0mm",
    writing_clearance="5mm",
    mos_width="10mm",
)

# SuperNote Manta (A5 X2): 1920×2560 @ 300 PPI → 162.56×216.75 mm. Toolbar top 8mm.
SUPERNOTE_MANTA = Device(
    id="supernote-manta",
    name="SuperNote Manta",
    ppi=300,
    page_width="162.56mm",
    page_height="216.75mm",
    toolbar_edge=TOOLBAR_TOP,
    toolbar_clearance="8mm",
    writing_clearance="4mm",
    mos_width="8mm",
    width_px=1920,
    height_px=2560,
)

# reMarkable 1: 1404×1872 @ 226 PPI → 157.79×210.39 mm. No toolbar (Scribe pack).
REMARKABLE_1 = Device(
    id="remarkable-1",
    name="reMarkable 1",
    ppi=226,
    page_width="157.79mm",
    page_height="210.39mm",
    toolbar_edge=TOOLBAR_NONE,
    toolbar_clearance="0mm",
    writing_clearance="5mm",
    mos_width="10mm",
    width_px=1404,
    height_px=1872,
)

# reMarkable 2: same canvas as reMarkable 1. Colophon name stays honest.
REMARKABLE_2 = Device(
    id="remarkable-2",
    name="reMarkable 2",
    ppi=226,
    page_width="157.79mm",
    page_height="210.39mm",
    toolbar_edge=TOOLBAR_NONE,
    toolbar_clearance="0mm",
    writing_clearance="5mm",
    mos_width="10mm",
    width_px=1404,
    height_px=1872,
)

# reMarkable Paper Pure: Carta 1300, still 226 PPI, same canvas as reMarkable 1.
REMARKABLE_PAPER_PURE = Device(
    id="remarkable-paper-pure",
    name="reMarkable Paper Pure",
    ppi=226,
    page_width="157.79mm",
    page_height="210.39mm",
    toolbar_edge=TOOLBAR_NONE,
    toolbar_clearance="0mm",
    writing_clearance="5mm",
    mos_width="10mm",
    width_px=1404,
    height_px=1872,
)

# reMarkable Paper Pro: 1620×2160 @ 229 PPI → 179.69×239.58 mm. No toolbar (Scribe pack).
REMARKABLE_PAPER_PRO = Device(
    id="remarkable-paper-pro",
    name="reMarkable Paper Pro",
    ppi=229,
    page_width="179.69mm",
    page_height="239.58mm",
    toolbar_edge=TOOLBAR_NONE,
    toolbar_clearance="0mm",
    writing_clearance="5mm",
    mos_width="10mm",
    width_px=1620,
    height_px=2160,
)

# reMarkable Paper Pro Move: 954×1696 @ 264 PPI → 91.79×163.18 mm. No toolbar (Scribe pack).
REMARKABLE_PAPER_PRO_MOVE = Device(
    id="remarkable-paper-pro-move",
    name="reMarkable Paper Pro Move",
    ppi=264,
    page_width="91.79mm",
    page_height="163.18mm",
    toolbar_edge=TOOLBAR_NONE,
    toolbar_clearance="0mm",
    writing_clearance="5mm",
    mos_width="10mm",
    width_px=954,
    height_px=1696,
)

DEVICES: tuple[Device, ...] = (
    SUPERNOTE_NOMAD,
    KINDLE_SCRIBE,
    PAPER_158X210,
    SUPERNOTE_MANTA,
    REMARKABLE_1,
    REMARKABLE_2,
    REMARKABLE_PAPER_PURE,
    REMARKABLE_PAPER_PRO,
    REMARKABLE_PAPER_PRO_MOVE,
)

PRESETS: dict[str, Device] = {
    SUPERNOTE_NOMAD.id: SUPERNOTE_NOMAD,
    KINDLE_SCRIBE.id: KINDLE_SCRIBE,
    PAPER_158X210.id: PAPER_158X210,
    SUPERNOTE_MANTA.id: SUPERNOTE_MANTA,
    REMARKABLE_1.id: REMARKABLE_1,
    REMARKABLE_2.id: REMARKABLE_2,
    REMARKABLE_PAPER_PURE.id: REMARKABLE_PAPER_PURE,
    REMARKABLE_PAPER_PRO.id: REMARKABLE_PAPER_PRO,
    REMARKABLE_PAPER_PRO_MOVE.id: REMARKABLE_PAPER_PRO_MOVE,
    "nomad": SUPERNOTE_NOMAD,
    "scribe": KINDLE_SCRIBE,
    "manta": SUPERNOTE_MANTA,
    "rm1": REMARKABLE_1,
    "rm2": REMARKABLE_2,
    "paper-pure": REMARKABLE_PAPER_PURE,
    "paper-pro": REMARKABLE_PAPER_PRO,
    "paper-pro-move": REMARKABLE_PAPER_PRO_MOVE,
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
