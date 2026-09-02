"""Line-drawing device frames generated from the Device record."""

from parch.devices import MM_PER_INCH, PT_PER_INCH, TOOLBAR_TOP, Device

FRAME_DEVICE_IDS = frozenset(
    {
        "supernote-nomad",
        "supernote-manta",
        "kindle-scribe",
        "158x210",
    }
)

# Device chrome around the page. Not toolbar_clearance (on-screen).
BEZEL_MM = 10.0


def _mm_to_pt(mm: float) -> float:
    return round(mm / MM_PER_INCH * PT_PER_INCH, 2)


def _pt(value: float) -> str:
    return f"{round(value, 2):.2f}"


def frame_svg(device: Device) -> str:
    """Emit a line-drawing whose #screen is 1:1 with a Typst page."""
    if device.id not in FRAME_DEVICE_IDS:
        known = ", ".join(sorted(FRAME_DEVICE_IDS))
        raise ValueError(f"no device frame for {device.id!r}; this slice: {known}")

    bezel = _mm_to_pt(BEZEL_MM)
    screen_w = device.width_pt
    screen_h = device.height_pt
    screen_x = bezel
    screen_y = bezel
    outer_w = round(screen_w + 2 * bezel, 2)
    outer_h = round(screen_h + 2 * bezel, 2)

    lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{_pt(outer_w)}pt"'
            f' height="{_pt(outer_h)}pt" viewBox="0 0 {_pt(outer_w)} {_pt(outer_h)}">'
        ),
        (
            f'  <rect x="0" y="0" width="{_pt(outer_w)}" height="{_pt(outer_h)}"'
            f' fill="#fff" stroke="#000" stroke-width="1"/>'
        ),
        (
            f'  <rect id="screen" x="{_pt(screen_x)}" y="{_pt(screen_y)}"'
            f' width="{_pt(screen_w)}" height="{_pt(screen_h)}"'
            f' fill="none" stroke="#000" stroke-width="1"/>'
        ),
    ]
    if device.toolbar_edge == TOOLBAR_TOP:
        mark_w = round(screen_w * 0.2, 2)
        mark_h = round(bezel * 0.4, 2)
        mark_x = round(screen_x + (screen_w - mark_w) / 2, 2)
        mark_y = round((screen_y - mark_h) / 2, 2)
        lines.append(
            f'  <rect id="toolbar" x="{_pt(mark_x)}" y="{_pt(mark_y)}"'
            f' width="{_pt(mark_w)}" height="{_pt(mark_h)}"'
            f' fill="none" stroke="#000" stroke-width="1"/>'
        )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"
