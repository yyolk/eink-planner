"""Device frame SVGs: #screen is identity with the Typst page."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from parch.device_frame import FRAME_DEVICE_IDS, HATCH_ID, HATCH_STRIPE, frame_svg
from parch.devices import DEVICES, MM_PER_INCH, PT_PER_INCH, TOOLBAR_NONE, TOOLBAR_TOP, get_device

_SNAPSHOTS = Path(__file__).resolve().parent / "__snapshots__" / "device_frames"

_FRAME_IDS = (
    "supernote-nomad",
    "supernote-manta",
    "kindle-scribe",
    "remarkable-1",
    "remarkable-2",
    "158x210",
)
_SUPERNOTE = ("supernote-nomad", "supernote-manta")
_SCRIBE_PACK = ("kindle-scribe", "remarkable-1", "remarkable-2")
_NO_TOOLBAR = (*_SCRIBE_PACK, "158x210")


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


def _has_pattern(root: ET.Element) -> bool:
    return any(_local(el.tag) == "pattern" for el in root.iter())


@pytest.mark.parametrize("device_id", _FRAME_IDS)
def test_screen_matches_device_page(device_id):
    device = get_device(device_id)
    root = _parse(frame_svg(device))
    screen = _by_id(root, "screen")
    assert screen is not None
    assert _local(screen.tag) == "rect"
    assert screen.get("fill") == "none"
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
    placed_w, placed_h = page_w, page_h
    assert placed_w == pytest.approx(sw)
    assert placed_h == pytest.approx(sh)
    vx, vy, vw, vh = _viewbox(root)
    assert sx + placed_w <= vx + vw
    assert sy + placed_h <= vy + vh


@pytest.mark.parametrize("device_id", _FRAME_IDS)
def test_screen_not_inset_by_toolbar_clearance(device_id):
    device = get_device(device_id)
    root = _parse(frame_svg(device))
    screen = _by_id(root, "screen")
    body = _by_id(root, "body")
    assert screen is not None
    assert body is not None
    sx, sy, sw, sh = _rect_box(screen)
    bx, by, bw, bh = _rect_box(body)
    left = sx - bx
    top = sy - by
    right = (bx + bw) - (sx + sw)
    bottom = (by + bh) - (sy + sh)
    assert left == pytest.approx(right)
    assert top == pytest.approx(bottom)
    assert sw == pytest.approx(device.width_pt)
    assert sh == pytest.approx(device.height_pt)


@pytest.mark.parametrize("device_id", _NO_TOOLBAR)
def test_even_bezel_on_scribe_and_paper(device_id):
    device = get_device(device_id)
    root = _parse(frame_svg(device))
    screen = _by_id(root, "screen")
    body = _by_id(root, "body")
    assert screen is not None and body is not None
    sx, sy, sw, sh = _rect_box(screen)
    bx, by, bw, bh = _rect_box(body)
    left = sx - bx
    top = sy - by
    right = (bx + bw) - (sx + sw)
    bottom = (by + bh) - (sy + sh)
    assert left == pytest.approx(top)
    assert top == pytest.approx(right)
    assert right == pytest.approx(bottom)


@pytest.mark.parametrize("device_id", _FRAME_IDS)
def test_toolbar_band_or_absent(device_id):
    device = get_device(device_id)
    svg = frame_svg(device)
    root = _parse(svg)
    screen = _by_id(root, "screen")
    toolbar = _by_id(root, "toolbar")
    assert screen is not None
    sx, sy, sw, _sh = _rect_box(screen)
    if device.toolbar_edge == TOOLBAR_TOP:
        assert toolbar is not None
        tx, ty, tw, th = _rect_box(toolbar)
        assert tw == pytest.approx(sw)
        assert tx == pytest.approx(sx)
        assert ty == pytest.approx(sy)
        mm = float(device.toolbar_clearance.removesuffix("mm"))
        assert th == pytest.approx(round(mm / MM_PER_INCH * PT_PER_INCH, 2))
        assert toolbar.get("fill") == f"url(#{HATCH_ID})"
        assert _has_pattern(root)
        assert HATCH_STRIPE == "#ccc"
        assert any(
            el.get("fill") == "#ccc"
            for el in root.iter()
            if _local(el.tag) == "rect" and el.get("id") is None
        )
        labels = [
            el
            for el in root.iter()
            if _local(el.tag) == "text" and (el.text or "").strip() == "toolbar"
        ]
        assert len(labels) == 1
        label = labels[0]
        assert label.get("text-anchor") == "middle"
        assert label.get("dominant-baseline") == "middle"
        assert label.get("fill") == "#000"
        assert float(label.get("x")) == pytest.approx(tx + tw / 2)
        assert float(label.get("y")) == pytest.approx(ty + th / 2)
        size = float((label.get("font-size") or "").removesuffix("pt"))
        assert 8.0 <= size <= 10.0
        assert size < th
    else:
        assert device.toolbar_edge == TOOLBAR_NONE
        assert toolbar is None
        assert not _has_pattern(root)
        assert not any(_local(el.tag) == "text" for el in root.iter())


@pytest.mark.parametrize("device_id", _SUPERNOTE)
def test_supernote_chrome(device_id):
    root = _parse(frame_svg(get_device(device_id)))
    body = _by_id(root, "body")
    assert body is not None
    assert float(body.get("rx") or 0) > 0
    assert _by_id(root, "power") is not None
    assert _by_id(root, "sensor") is None
    lines = [el for el in root.iter() if _local(el.tag) == "line"]
    assert len(lines) == 2


@pytest.mark.parametrize("device_id", _SCRIBE_PACK)
def test_scribe_is_not_supernote_chrome(device_id):
    root = _parse(frame_svg(get_device(device_id)))
    body = _by_id(root, "body")
    assert body is not None
    assert float(body.get("rx") or 0) > 0
    assert _by_id(root, "toolbar") is None
    assert _by_id(root, "sensor") is None
    assert not any(_local(el.tag) == "line" for el in root.iter())
    assert not _has_pattern(root)
    assert not any(_local(el.tag) == "text" for el in root.iter())
    assert _by_id(root, "power") is not None


def test_frame_device_ids_include_remarkable():
    assert "remarkable-1" in FRAME_DEVICE_IDS
    assert "remarkable-2" in FRAME_DEVICE_IDS
    assert FRAME_DEVICE_IDS == frozenset(_FRAME_IDS)


def test_paper_is_generic_two_rect():
    root = _parse(frame_svg(get_device("158x210")))
    body = _by_id(root, "body")
    assert body is not None
    assert body.get("rx") is None
    assert _by_id(root, "toolbar") is None
    assert _by_id(root, "sensor") is None
    assert _by_id(root, "power") is None
    assert not any(_local(el.tag) == "line" for el in root.iter())


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
