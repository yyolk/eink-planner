"""Specimen catalog: compose at #screen, identity scale; unknown ids raise."""

from xml.etree import ElementTree as ET

import pytest

from parch.cli import build_parser, main, specimen_cmd
from parch.device_frame import FRAME_DEVICE_IDS, frame_svg
from parch.devices import DEVICES, get_device
from parch.services.preview_svg import SAMPLE_STEMS
from parch.services.specimen import (
    catalog_dest,
    catalog_index_html,
    compose_specimen,
    framed_specimen,
    listed_catalog_devices,
    specimen_index_html,
    specimens_dest,
    write_catalog_index,
    write_specimens,
)

_FRAME_IDS = (
    "supernote-nomad",
    "supernote-manta",
    "kindle-scribe",
    "158x210",
)
_SUPERNOTE = ("supernote-nomad", "supernote-manta")
_NO_TOOLBAR = ("kindle-scribe", "158x210")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _by_id(root: ET.Element, element_id: str) -> ET.Element | None:
    for el in root.iter():
        if el.get("id") == element_id:
            return el
    return None


def _dummy_page(device) -> str:
    w = device.width_pt
    h = device.height_pt
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}pt" height="{h}pt"'
        f' viewBox="0 0 {w} {h}">'
        f'<rect id="page" width="{w}" height="{h}" fill="#eee"/>'
        f"</svg>"
    )


def _nested_svg(composed: str) -> ET.Element:
    root = ET.fromstring(composed)
    nested = [
        el
        for el in root
        if _local(el.tag) == "svg" and el.get("x") is not None
    ]
    assert len(nested) == 1
    return nested[0]


@pytest.mark.parametrize("device_id", _FRAME_IDS)
def test_compose_dummy_page_is_identity_scale(device_id):
    device = get_device(device_id)
    frame = frame_svg(device)
    page = _dummy_page(device)
    out = compose_specimen(frame, page)
    assert 'preserveAspectRatio="none"' not in out
    screen = _by_id(ET.fromstring(frame), "screen")
    assert screen is not None
    nested = _nested_svg(out)
    assert float(nested.get("x")) == pytest.approx(float(screen.get("x")))
    assert float(nested.get("y")) == pytest.approx(float(screen.get("y")))
    assert float(nested.get("width")) == pytest.approx(device.width_pt)
    assert float(nested.get("height")) == pytest.approx(device.height_pt)
    assert float(nested.get("width")) == pytest.approx(float(screen.get("width")))
    assert float(nested.get("height")) == pytest.approx(float(screen.get("height")))
    vb = (nested.get("viewBox") or "").split()
    assert len(vb) == 4
    page_w, page_h = float(vb[2]), float(vb[3])
    assert float(nested.get("width")) / page_w == pytest.approx(1.0)
    assert float(nested.get("height")) / page_h == pytest.approx(1.0)
    assert _by_id(ET.fromstring(out), "page") is not None
    assert _by_id(ET.fromstring(out), "screen") is not None


@pytest.mark.parametrize("device_id", _SUPERNOTE)
def test_compose_nests_page_before_toolbar(device_id):
    device = get_device(device_id)
    frame = frame_svg(device)
    out = compose_specimen(frame, _dummy_page(device))
    root = ET.fromstring(out)
    screen = _by_id(root, "screen")
    toolbar = _by_id(root, "toolbar")
    nested = _nested_svg(out)
    assert screen is not None and toolbar is not None
    assert float(nested.get("x")) == pytest.approx(float(screen.get("x")))
    assert float(nested.get("y")) == pytest.approx(float(screen.get("y")))
    order = []
    for el in root:
        if _local(el.tag) == "svg" and el.get("x") is not None:
            order.append("page")
        elif el.get("id") == "toolbar":
            order.append("toolbar")
        elif _local(el.tag) == "text" and (el.text or "").strip() == "toolbar":
            order.append("label")
    assert order == ["page", "toolbar", "label"]
    assert out.find("<svg x=") < out.find('id="toolbar"')


@pytest.mark.parametrize("device_id", _NO_TOOLBAR)
def test_compose_without_toolbar_inserts_before_close(device_id):
    device = get_device(device_id)
    frame = frame_svg(device)
    out = compose_specimen(frame, _dummy_page(device))
    assert 'id="toolbar"' not in out
    last = list(ET.fromstring(out))[-1]
    assert _local(last.tag) == "svg"
    assert last.get("x") is not None
    close = out.rfind("</svg>")
    assert close > 0
    assert out[close:].strip() == "</svg>"


@pytest.mark.parametrize(
    "device",
    [d for d in DEVICES if d.id not in FRAME_DEVICE_IDS],
    ids=lambda d: d.id,
)
def test_unknown_device_raises(device):
    with pytest.raises(ValueError, match="no device frame"):
        framed_specimen(device, _dummy_page(device))


def test_specimen_cli_help_lists_verb():
    help_text = build_parser().format_help()
    assert "specimen" in help_text
    parser = build_parser()
    args = parser.parse_args(["specimen", "supernote-nomad"])
    assert args.command == "specimen"
    assert args.run is specimen_cmd
    assert args.hand is None
    assert args.workdir == "./out"
    assert not hasattr(args, "scale")
    assert not hasattr(args, "samples")


def test_specimen_help_has_hand(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["specimen", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--hand" in out
    assert "specimen" in out


def test_specimen_rejects_unknown_device_before_press(tmp_path, capsys):
    code = main(["specimen", "remarkable-1", "-w", str(tmp_path)])
    assert code == 1
    assert "no device frame" in capsys.readouterr().err
    assert not (tmp_path / "index.typst").exists()
    assert not (tmp_path / "specimens").exists()


def test_catalog_dest_is_specimens_root(tmp_path):
    assert catalog_dest(tmp_path) == tmp_path / "specimens"
    assert specimens_dest(tmp_path, "158x210") == tmp_path / "specimens" / "158x210"


def test_write_specimens_catalog(tmp_path):
    device = get_device("158x210")
    pages = {stem: _dummy_page(device) for stem in SAMPLE_STEMS}
    dest = specimens_dest(tmp_path, device.id)
    index = write_specimens(dest, device, pages)
    assert index == dest / "index.html"
    html = index.read_text(encoding="utf-8")
    for stem in SAMPLE_STEMS:
        assert (dest / f"{stem}.svg").is_file()
        assert f'src="{stem}.svg"' in html
        assert 'preserveAspectRatio="none"' not in (dest / f"{stem}.svg").read_text()
    assert "annual.svg" in html
    assert html.count("<figure>") == len(SAMPLE_STEMS)


def test_write_catalog_index_root(tmp_path):
    device = get_device("158x210")
    pages = {stem: _dummy_page(device) for stem in SAMPLE_STEMS}
    dest = specimens_dest(tmp_path, device.id)
    write_specimens(dest, device, pages)
    root = catalog_dest(tmp_path)
    index = write_catalog_index(root, listed_catalog_devices(root))
    assert index == root / "index.html"
    html = index.read_text(encoding="utf-8")
    assert 'href="158x210/"' in html
    assert 'src="158x210/cover.svg"' in html
    assert "<script" not in html
    assert listed_catalog_devices(root) == ["158x210"]


def test_catalog_index_html_is_dumb():
    html = catalog_index_html(["158x210", "supernote-nomad"])
    assert 'href="158x210/"' in html
    assert 'src="supernote-nomad/cover.svg"' in html
    assert "<script" not in html
    assert html.count("<section>") == 2


def test_listed_catalog_devices_prefers_frame_ids(tmp_path):
    root = catalog_dest(tmp_path)
    for device_id in ("158x210", "supernote-nomad", "extra-device"):
        dest = root / device_id
        dest.mkdir(parents=True)
        (dest / "index.html").write_text("<title>x</title>\n", encoding="utf-8")
    assert listed_catalog_devices(root) == [
        "158x210",
        "supernote-nomad",
        "extra-device",
    ]
    assert listed_catalog_devices(tmp_path / "missing") == []


def test_specimen_index_html_is_dumb():
    html = specimen_index_html("supernote-nomad")
    assert "supernote-nomad" in html
    assert "<script" not in html
    for stem in SAMPLE_STEMS:
        assert f"{stem}.svg" in html
