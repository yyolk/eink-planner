"""Device frame SVGs: #screen is identity with the Typst page."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from parch.device_frame import FRAME_DEVICE_IDS, frame_svg
from parch.devices import DEVICES, TOOLBAR_NONE, TOOLBAR_TOP, get_device

_SNAPSHOTS = Path(__file__).resolve().parent / "__snapshots__" / "device_frames"

_FRAME_IDS = (
    "supernote-nomad",
    "supernote-manta",
    "kindle-scribe",
    "158x210",
)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse(svg: str) -> ET.Element:
    return ET.fromstring(svg)


def _by_id(root: ET.Element, element_id: str) -> ET.Element | None:
    for el in root.iter():
        if el.get("id") == element_id:
            return el
    return None


def _length_pt(value: str) -> float:
    assert value.endswith("pt"), value
    return float(value[:-2])


def _viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    raw = root.get("viewBox")
    assert raw is not None
    x, y, w, h = (float(part) for part in raw.split())
    return x, y, w, h


def _rect_box(el: ET.Element) -> tuple[float, float, float, float]:
    return (
        float(el.get("x") or 0.0),
        float(el.get("y") or 0.0),
        float(el.get("width") or 0.0),
        float(el.get("height") or 0.0),
    )


@pytest.mark.parametrize("device_id", _FRAME_IDS)
def test_screen_matches_device_page(device_id):
    device = get_device(device_id)
    root = _parse(frame_svg(device))
    screen = _by_id(root, "screen")
    assert screen is not None
    assert _local(screen.tag) == "rect"
    width = float(screen.get("width"))
    height = float(screen.get("height"))
    assert width == pytest.approx(device.width_pt)
    assert height == pytest.approx(device.height_pt)


@pytest.mark.parametrize("device_id", _FRAME_IDS)
def test_screen_sits_inside_viewbox(device_id):
    device = get_device(device_id)
    root = _parse(frame_svg(device))
    screen = _by_id(root, "screen")
    assert screen is not None
    sx, sy, sw, sh = _rect_box(screen)
    vx, vy, vw, vh = _viewbox(root)
    assert sx >= vx
    assert sy >= vy
    assert sx + sw <= vx + vw
    assert sy + sh <= vy + vh


@pytest.mark.parametrize("device_id", _FRAME_IDS)
def test_root_sized_in_pt(device_id):
    device = get_device(device_id)
    root = _parse(frame_svg(device))
    width = _length_pt(root.get("width") or "")
    height = _length_pt(root.get("height") or "")
    vx, vy, vw, vh = _viewbox(root)
    assert vx == pytest.approx(0.0)
    assert vy == pytest.approx(0.0)
    assert width == pytest.approx(vw)
    assert height == pytest.approx(vh)


@pytest.mark.parametrize("device_id", _FRAME_IDS)
def test_page_overlay_is_identity_scale(device_id):
    device = get_device(device_id)
    root = _parse(frame_svg(device))
    screen = _by_id(root, "screen")
    assert screen is not None
    sx, sy, sw, sh = _rect_box(screen)
    page_w = device.width_pt
    page_h = device.height_pt
    assert sw / page_w == pytest.approx(1.0)
    assert sh / page_h == pytest.approx(1.0)
    # Overlay is translate(sx, sy) only — no extra scale.
    placed_w, placed_h = page_w, page_h
    assert placed_w == pytest.approx(sw)
    assert placed_h == pytest.approx(sh)
    vx, vy, vw, vh = _viewbox(root)
    assert sx + placed_w <= vx + vw
    assert sy + placed_h <= vy + vh


@pytest.mark.parametrize("device_id", _FRAME_IDS)
def test_bezel_is_uniform_and_not_toolbar_clearance(device_id):
    device = get_device(device_id)
    root = _parse(frame_svg(device))
    screen = _by_id(root, "screen")
    assert screen is not None
    sx, sy, sw, sh = _rect_box(screen)
    vx, vy, vw, vh = _viewbox(root)
    left = sx - vx
    top = sy - vy
    right = (vx + vw) - (sx + sw)
    bottom = (vy + vh) - (sy + sh)
    assert left == pytest.approx(top)
    assert top == pytest.approx(right)
    assert right == pytest.approx(bottom)
    assert sw == pytest.approx(device.width_pt)
    assert sh == pytest.approx(device.height_pt)


@pytest.mark.parametrize("device_id", _FRAME_IDS)
def test_toolbar_mark_only_in_top_bezel(device_id):
    device = get_device(device_id)
    root = _parse(frame_svg(device))
    screen = _by_id(root, "screen")
    toolbar = _by_id(root, "toolbar")
    assert screen is not None
    sx, sy, sw, _sh = _rect_box(screen)
    if device.toolbar_edge == TOOLBAR_TOP:
        assert toolbar is not None
        tx, ty, tw, th = _rect_box(toolbar)
        assert ty + th <= sy
        assert tx >= sx
        assert tx + tw <= sx + sw
        assert ty >= 0.0
    else:
        assert device.toolbar_edge == TOOLBAR_NONE
        assert toolbar is None


@pytest.mark.parametrize("device_id", _FRAME_IDS)
def test_frame_svg_snapshot(device_id):
    path = _SNAPSHOTS / f"{device_id}.svg"
    assert frame_svg(get_device(device_id)) == path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "device",
    [d for d in DEVICES if d.id not in FRAME_DEVICE_IDS],
    ids=lambda d: d.id,
)
def test_unknown_registry_ids_raise(device):
    with pytest.raises(ValueError, match="no device frame"):
        frame_svg(device)
