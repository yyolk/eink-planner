"""Specimen catalog: compose at #screen, identity scale; unknown ids raise."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

import tomllib

from parch.cli import _set_job_paper, build_parser, main, samples_dest, specimen_cmd
from parch.config import load
from parch.device_frame import FRAME_DEVICE_IDS, frame_svg
from parch.devices import DEVICES, get_device
from parch.services.config_file import open_resolved
from parch.services.job_file import (
    CANONICAL_SECTIONS,
    DEFAULT_SECTIONS,
    emit_job,
    spec_from_device,
)
from parch.services.preview_svg import SAMPLE_STEMS
from parch.toml_config import apply_hand
from parch.services.specimen import (
    PERMUTATIONS,
    catalog_dest,
    catalog_index_html,
    compose_specimen,
    framed_specimen,
    listed_catalog_devices,
    perm_parts,
    specimen_index_html,
    specimens_dest,
    write_catalog_index,
    write_device_index,
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
    assert "--paper" not in out
    assert "specimen" in out


def test_specimen_rejects_unknown_device_before_press(tmp_path, capsys):
    code = main(["specimen", "remarkable-1", "-w", str(tmp_path)])
    assert code == 1
    assert "no device frame" in capsys.readouterr().err
    assert not (tmp_path / "index.typst").exists()
    assert not (tmp_path / "specimens").exists()


def test_permutation_order():
    assert PERMUTATIONS == ("lined-left", "lined-right", "dotted-left", "dotted-right")
    assert [perm_parts(perm) for perm in PERMUTATIONS] == [
        ("lined", "left"),
        ("lined", "right"),
        ("dotted", "left"),
        ("dotted", "right"),
    ]


def test_catalog_dest_is_specimens_root(tmp_path):
    assert catalog_dest(tmp_path) == tmp_path / "specimens"
    assert specimens_dest(tmp_path, "158x210") == tmp_path / "specimens" / "158x210"
    assert specimens_dest(tmp_path, "158x210", "lined-left") == (
        tmp_path / "specimens" / "158x210" / "lined-left"
    )
    assert specimens_dest(tmp_path, "supernote-nomad", "dotted-right") == (
        tmp_path / "specimens" / "supernote-nomad" / "dotted-right"
    )


def test_write_specimens_strips_nul_from_page_href(tmp_path):
    device = get_device("158x210")
    page = (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'
        f' width="{device.width_pt}pt" height="{device.height_pt}pt"'
        f' viewBox="0 0 {device.width_pt} {device.height_pt}">'
        f'<use xlink:href="#\x00deadbeef"/>'
        f"</svg>"
    )
    dest = specimens_dest(tmp_path, device.id, "lined-left")
    write_specimens(dest, device, {"cover": page}, stems=("cover",))
    raw = (dest / "cover.svg").read_bytes()
    assert b"\x00" not in raw
    text = raw.decode("utf-8")
    assert 'xlink:href="#deadbeef"' in text
    ET.fromstring(text)


def test_write_specimens_catalog(tmp_path):
    device = get_device("158x210")
    pages = {stem: _dummy_page(device) for stem in SAMPLE_STEMS}
    device_dir = specimens_dest(tmp_path, device.id)
    for perm in PERMUTATIONS:
        write_specimens(specimens_dest(tmp_path, device.id, perm), device, pages)
    index = write_device_index(device_dir, device.id)
    assert index == device_dir / "index.html"
    html = index.read_text(encoding="utf-8")
    for perm in PERMUTATIONS:
        assert f'<section id="{perm}">' in html
        assert f'href="#{perm}"' in html
        for stem in SAMPLE_STEMS:
            assert (device_dir / perm / f"{stem}.svg").is_file()
            assert f'src="{perm}/{stem}.svg"' in html
            assert 'preserveAspectRatio="none"' not in (
                device_dir / perm / f"{stem}.svg"
            ).read_text()
    assert "annual.svg" in html
    assert html.count("<figure>") == len(SAMPLE_STEMS) * len(PERMUTATIONS)
    assert html.count("<section") == 4
    assert 'href="../"' in html
    for stem in (
        "projects",
        "project-1",
        "habits",
        "habits-jan",
        "review",
        "review-w01",
        "tasks",
        "tasks-w01",
        "meetings",
        "meeting-1",
    ):
        assert f'src="lined-left/{stem}.svg"' in html


def test_write_catalog_index_root(tmp_path):
    device = get_device("158x210")
    pages = {stem: _dummy_page(device) for stem in SAMPLE_STEMS}
    device_dir = specimens_dest(tmp_path, device.id)
    write_specimens(specimens_dest(tmp_path, device.id, "lined-left"), device, pages)
    write_device_index(device_dir, device.id)
    root = catalog_dest(tmp_path)
    index = write_catalog_index(root, listed_catalog_devices(root))
    assert index == root / "index.html"
    html = index.read_text(encoding="utf-8")
    assert 'href="158x210/"' in html
    assert 'href="158x210/#dotted-right"' in html
    assert "<figure>" not in html
    assert 'src="158x210/cover.svg"' not in html
    assert "<script" not in html
    assert listed_catalog_devices(root) == ["158x210"]
    assert 'href="#158x210"' in html
    assert 'id="158x210"' in html


def test_catalog_index_html_is_dumb():
    ids = ["158x210", "supernote-nomad"]
    html = catalog_index_html(ids)
    assert 'href="158x210/"' in html
    assert 'href="supernote-nomad/#dotted-right"' in html
    assert "<figure>" not in html
    assert ".svg" not in html
    assert "<script" not in html
    assert html.count("<section") == 2
    assert html.index("<ul>") < html.index("<nav>")
    assert html.rindex("</ul>") < html.index("<nav>")
    assert html.index("<li>lined") < html.index("<li>dotted")
    assert html.index("<li>left") < html.index("<li>right")
    assert html.index("lined-left") < html.index("lined-right")
    assert html.index("lined-right") < html.index("dotted-left")
    nav = html[html.index("<nav>") : html.index("</nav>")]
    assert html.index("<nav>") < html.index("<section")
    for device_id in ids:
        assert f'href="#{device_id}"' in nav
        assert f'<section id="{device_id}">' in html
        assert f'<h2><a href="{device_id}/">{device_id}</a></h2>' in html
        for perm in PERMUTATIONS:
            assert f'href="{device_id}/#{perm}"' in html
    assert nav.index('href="#158x210"') < nav.index('href="#supernote-nomad"')


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
    assert 'href="../"' in html
    assert html.count("<section") == 4
    for perm in PERMUTATIONS:
        assert f'<section id="{perm}">' in html
        assert f'href="#{perm}"' in html
    toc = html[html.index("<nav>") : html.index("</nav>")]
    assert toc.index('href="#lined-left"') < toc.index('href="#dotted-right"')
    for stem in SAMPLE_STEMS:
        assert f"lined-left/{stem}.svg" in html
    for stem in (
        "projects",
        "project-1",
        "habits",
        "habits-jan",
        "review",
        "review-w01",
        "tasks",
        "tasks-w01",
        "meetings",
        "meeting-1",
    ):
        assert f"dotted-right/{stem}.svg" in html


def test_proof_samples_dest_is_not_four_times_catalog():
    dest = samples_dest(Path("/tmp/out"), "158x210")
    assert dest == Path("/tmp/out/158x210")
    assert dest.name == "158x210"
    assert "lined-left" not in dest.parts
    assert "specimens" not in dest.parts
    assert len(SAMPLE_STEMS) == len(set(SAMPLE_STEMS))
    assert all(perm not in SAMPLE_STEMS for perm in PERMUTATIONS)
    args = build_parser().parse_args(["proof", "158x210", "--samples"])
    assert args.samples is True
    assert not hasattr(args, "paper")


def test_set_job_paper_overlays_scratch_pad(tmp_path):
    path = tmp_path / "job.toml"
    path.write_text(emit_job(spec_from_device("158x210")), encoding="utf-8")
    assert load(path)["planner"]["params"]["scratch_pad"] == "dotted"
    _set_job_paper(path, "lined")
    dto = apply_hand(load(path), "right")
    assert dto["planner"]["params"]["scratch_pad"] == "lined"
    assert dto["planner"]["params"]["mos_layout"]["side_menu_position"] == "right"


def test_specimen_job_uses_canonical_sections():
    with open_resolved("158x210") as path:
        default = tomllib.loads(path.read_text(encoding="utf-8"))
    with open_resolved("kindle-scribe", sections=CANONICAL_SECTIONS) as path:
        scribe = tomllib.loads(path.read_text(encoding="utf-8"))
    with open_resolved("supernote-nomad", sections=CANONICAL_SECTIONS) as path:
        nomad = tomllib.loads(path.read_text(encoding="utf-8"))
    assert default["sections"] == list(DEFAULT_SECTIONS)
    assert "projects" not in default["sections"]
    for extra in ("projects", "habits", "review", "tasks", "meetings"):
        assert extra in CANONICAL_SECTIONS
        assert extra in scribe["sections"]
        assert extra in nomad["sections"]
    assert scribe["sections"] == list(CANONICAL_SECTIONS)
    assert nomad["sections"] == list(CANONICAL_SECTIONS)
