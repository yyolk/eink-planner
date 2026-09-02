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
BODY_FILL = "#c8c8c8"
CORNER_MM = 4.0
NUB_LEN_MM = 3.5
NUB_THICK_MM = 1.1
SENSOR_W_MM = 4.0
SENSOR_H_MM = 1.4
HATCH_ID = "hatch"


def _mm_to_pt(mm: float) -> float:
    return round(mm / MM_PER_INCH * PT_PER_INCH, 2)


def _pt(value: float) -> str:
    return f"{round(value, 2):.2f}"


def _mm_token(token: str) -> float:
    text = token.strip()
    if text.endswith("mm"):
        text = text[:-2]
    return float(text)


def _rect_d(x: float, y: float, w: float, h: float) -> str:
    return (
        f"M {_pt(x)} {_pt(y)} H {_pt(x + w)} V {_pt(y + h)} H {_pt(x)} Z"
    )


def _rounded_rect_d(x: float, y: float, w: float, h: float, rx: float) -> str:
    r = min(rx, w / 2, h / 2)
    if r <= 0:
        return _rect_d(x, y, w, h)
    x2, y2 = x + w, y + h
    return (
        f"M {_pt(x + r)} {_pt(y)} "
        f"H {_pt(x2 - r)} "
        f"A {_pt(r)} {_pt(r)} 0 0 1 {_pt(x2)} {_pt(y + r)} "
        f"V {_pt(y2 - r)} "
        f"A {_pt(r)} {_pt(r)} 0 0 1 {_pt(x2 - r)} {_pt(y2)} "
        f"H {_pt(x + r)} "
        f"A {_pt(r)} {_pt(r)} 0 0 1 {_pt(x)} {_pt(y2 - r)} "
        f"V {_pt(y + r)} "
        f"A {_pt(r)} {_pt(r)} 0 0 1 {_pt(x + r)} {_pt(y)} Z"
    )


def _hatch_defs() -> list[str]:
    return [
        "  <defs>",
        f'    <pattern id="{HATCH_ID}" patternUnits="userSpaceOnUse"'
        ' width="6" height="6" patternTransform="rotate(45)">',
        '      <rect width="6" height="6" fill="#fff"/>',
        '      <rect width="3" height="6" fill="#000"/>',
        "    </pattern>",
        "  </defs>",
    ]


def _bezel_path(
    x: float, y: float, w: float, h: float, rx: float,
    sx: float, sy: float, sw: float, sh: float,
) -> str:
    d = f"{_rounded_rect_d(x, y, w, h, rx)} {_rect_d(sx, sy, sw, sh)}"
    return f'  <path fill="{BODY_FILL}" fill-rule="evenodd" d="{d}"/>'


def _body_rect(x: float, y: float, w: float, h: float, rx: float) -> str:
    extra = f' rx="{_pt(rx)}" ry="{_pt(rx)}"' if rx > 0 else ""
    return (
        f'  <rect id="body" x="{_pt(x)}" y="{_pt(y)}" width="{_pt(w)}"'
        f' height="{_pt(h)}"{extra} fill="none" stroke="#000" stroke-width="1"/>'
    )


def _screen_rect(x: float, y: float, w: float, h: float) -> str:
    return (
        f'  <rect id="screen" x="{_pt(x)}" y="{_pt(y)}" width="{_pt(w)}"'
        f' height="{_pt(h)}" fill="none" stroke="#000" stroke-width="1"/>'
    )


def _svg(width: float, height: float, inner: list[str]) -> str:
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_pt(width)}pt"'
        f' height="{_pt(height)}pt" viewBox="0 0 {_pt(width)} {_pt(height)}">'
    )
    return "\n".join([head, *inner, "</svg>"]) + "\n"


def _paper_frame(device: Device) -> str:
    bezel = _mm_to_pt(BEZEL_MM)
    sw, sh = device.width_pt, device.height_pt
    sx = sy = bezel
    bw = round(sw + 2 * bezel, 2)
    bh = round(sh + 2 * bezel, 2)
    return _svg(
        bw,
        bh,
        [
            _bezel_path(0, 0, bw, bh, 0, sx, sy, sw, sh),
            _body_rect(0, 0, bw, bh, 0),
            _screen_rect(sx, sy, sw, sh),
        ],
    )


def _scribe_frame(device: Device) -> str:
    bezel = _mm_to_pt(BEZEL_MM)
    rx = _mm_to_pt(CORNER_MM)
    nub_w = _mm_to_pt(NUB_THICK_MM)
    nub_h = _mm_to_pt(NUB_LEN_MM)
    sw, sh = device.width_pt, device.height_pt
    sx = sy = bezel
    bw = round(sw + 2 * bezel, 2)
    bh = round(sh + 2 * bezel, 2)
    nub_x = bw
    nub_y = round(bh * 0.18, 2)
    return _svg(
        round(bw + nub_w, 2),
        bh,
        [
            _bezel_path(0, 0, bw, bh, rx, sx, sy, sw, sh),
            _body_rect(0, 0, bw, bh, rx),
            (
                f'  <rect id="power" x="{_pt(nub_x)}" y="{_pt(nub_y)}"'
                f' width="{_pt(nub_w)}" height="{_pt(nub_h)}"'
                f' fill="{BODY_FILL}" stroke="#000" stroke-width="1"/>'
            ),
            _screen_rect(sx, sy, sw, sh),
        ],
    )


def _supernote_frame(device: Device) -> str:
    bezel = _mm_to_pt(BEZEL_MM)
    rx = _mm_to_pt(CORNER_MM)
    nub_w = _mm_to_pt(NUB_LEN_MM)
    nub_h = _mm_to_pt(NUB_THICK_MM)
    sw, sh = device.width_pt, device.height_pt
    bw = round(sw + 2 * bezel, 2)
    bh = round(sh + 2 * bezel, 2)
    bx, by = 0.0, nub_h
    sx, sy = bezel, round(nub_h + bezel, 2)
    toolbar_h = _mm_to_pt(_mm_token(device.toolbar_clearance))
    toolbar_y = round(sy - toolbar_h, 2)
    slider_h = round(sh * 2 / 3, 2)
    slider_y = round(sy + (sh - slider_h) / 2, 2)
    left_x = round(bx + bezel / 2, 2)
    right_x = round(sx + sw + bezel / 2, 2)
    nub_x = round(bx + bw * 0.78, 2)
    pill_w = _mm_to_pt(SENSOR_W_MM)
    pill_h = _mm_to_pt(SENSOR_H_MM)
    pill_x = round(sx + _mm_to_pt(2.0), 2)
    pill_y = round(by + (toolbar_y - by - pill_h) / 2, 2)
    inner = [
        *_hatch_defs(),
        _bezel_path(bx, by, bw, bh, rx, sx, sy, sw, sh),
        _body_rect(bx, by, bw, bh, rx),
        (
            f'  <rect id="power" x="{_pt(nub_x)}" y="0" width="{_pt(nub_w)}"'
            f' height="{_pt(nub_h)}" fill="{BODY_FILL}" stroke="#000"'
            f' stroke-width="1"/>'
        ),
        (
            f'  <rect id="sensor" x="{_pt(pill_x)}" y="{_pt(pill_y)}"'
            f' width="{_pt(pill_w)}" height="{_pt(pill_h)}"'
            f' rx="{_pt(pill_h / 2)}" ry="{_pt(pill_h / 2)}"'
            f' fill="none" stroke="#000" stroke-width="1"/>'
        ),
        (
            f'  <line x1="{_pt(left_x)}" y1="{_pt(slider_y)}" x2="{_pt(left_x)}"'
            f' y2="{_pt(slider_y + slider_h)}" stroke="#000" stroke-width="1"/>'
        ),
        (
            f'  <line x1="{_pt(right_x)}" y1="{_pt(slider_y)}" x2="{_pt(right_x)}"'
            f' y2="{_pt(slider_y + slider_h)}" stroke="#000" stroke-width="1"/>'
        ),
        (
            f'  <rect id="toolbar" x="{_pt(sx)}" y="{_pt(toolbar_y)}"'
            f' width="{_pt(sw)}" height="{_pt(toolbar_h)}"'
            f' fill="url(#{HATCH_ID})" stroke="#000" stroke-width="1"/>'
        ),
        _screen_rect(sx, sy, sw, sh),
    ]
    return _svg(bw, round(bh + nub_h, 2), inner)


def frame_svg(device: Device) -> str:
    """Emit a line-drawing whose #screen is 1:1 with a Typst page."""
    if device.id not in FRAME_DEVICE_IDS:
        known = ", ".join(sorted(FRAME_DEVICE_IDS))
        raise ValueError(f"no device frame for {device.id!r}; this slice: {known}")
    if device.id == "158x210":
        return _paper_frame(device)
    if device.id == "kindle-scribe":
        return _scribe_frame(device)
    if device.toolbar_edge != TOOLBAR_TOP:
        raise ValueError(f"no SuperNote chrome for {device.id!r}")
    return _supernote_frame(device)
