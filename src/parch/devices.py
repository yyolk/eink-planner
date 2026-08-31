"""Named e-ink device presets with 1:1-on-glass page sizes."""

from dataclasses import dataclass

MM_PER_INCH = 25.4
PT_PER_INCH = 72.0


@dataclass(frozen=True)
class Device:
    """Physical e-ink panel used as a page size."""

    name: str
    slug: str
    width_px: int
    height_px: int
    ppi: int = 300

    @property
    def width_mm(self) -> float:
        return round(self.width_px / self.ppi * MM_PER_INCH, 2)

    @property
    def height_mm(self) -> float:
        return round(self.height_px / self.ppi * MM_PER_INCH, 2)

    @property
    def width_pt(self) -> float:
        return round(self.width_px / self.ppi * PT_PER_INCH, 2)

    @property
    def height_pt(self) -> float:
        return round(self.height_px / self.ppi * PT_PER_INCH, 2)

    def page_size_mm(self) -> tuple[str, str]:
        return (f"{self.width_mm}mm", f"{self.height_mm}mm")


# SuperNote Nomad (A6 X2): 1404×1872 @ 300 PPI
# 336.96×449.28 pt = 118.87×158.50 mm, 3:4. DEFAULT.
SUPERNOTE_NOMAD = Device(
    name="SuperNote Nomad",
    slug="supernote-nomad",
    width_px=1404,
    height_px=1872,
    ppi=300,
)

# Kindle Scribe: 1860×2480 @ 300 PPI
# 446.4×595.2 pt = 157.48×209.97 mm (the original 158×210 config).
KINDLE_SCRIBE = Device(
    name="Kindle Scribe",
    slug="kindle-scribe",
    width_px=1860,
    height_px=2480,
    ppi=300,
)

PRESETS: dict[str, Device] = {
    SUPERNOTE_NOMAD.slug: SUPERNOTE_NOMAD,
    KINDLE_SCRIBE.slug: KINDLE_SCRIBE,
    "nomad": SUPERNOTE_NOMAD,
    "scribe": KINDLE_SCRIBE,
}

DEFAULT_DEVICE = SUPERNOTE_NOMAD


def get_device(slug: str) -> Device:
    key = slug.strip().lower()
    if key not in PRESETS:
        known = ", ".join(sorted({d.slug for d in PRESETS.values()}))
        raise KeyError(f"unknown device {slug!r}; known: {known}")
    return PRESETS[key]
