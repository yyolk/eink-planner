"""Hawk generate: compact sections on every device; none-edge clearance is 0mm."""

from parch.config import load
from parch.devices import DEVICES, TOOLBAR_NONE, get_device
from parch.models.device import device_page_margin, device_scale
from parch.mos.configurator import Configurator
from parch.mos.preamble import Preamble, render_device_typ
from parch.services.generate import Generate
from parch.services.job_file import DEFAULT_SECTIONS
from tests.helpers import base_config, load_default
from tests.toml_fixtures import short_january


def _generate(stem: str) -> str:
    dto = short_january(load(base_config(stem)))
    return Generate(i18n=load_default()).generate(dto)


def test_nomad_keeps_top_toolbar_and_compact_sections():
    dto = load(base_config("supernote-nomad"))
    names = [section["name"] for section in Configurator(dto).enabled_sections()]
    assert names == list(DEFAULT_SECTIONS)
    assert dto["document"]["layout"]["margin"].to_plain() == {
        "top": "8mm",
        "bottom": "0mm",
        "left": "0mm",
        "right": "4mm",
    }
    now = _generate("supernote-nomad")
    assert "page-margin(left)" in now
    assert "toolbar-edge" in now.split("#set page", 1)[0]


def test_scribe_and_158_generate_bodies_match_only_toolbar_changes():
    for stem in ("kindle-scribe", "158x210"):
        dto = load(base_config(stem))
        names = [section["name"] for section in Configurator(dto).enabled_sections()]
        assert names == list(DEFAULT_SECTIONS)
        scale = device_scale(dto["device"])
        assert scale["toolbar_edge"] == "none"
        assert scale["toolbar_clearance"] == "0mm"
        assert dto["document"]["layout"]["margin"].to_plain() == device_page_margin(scale)
        assert dto["document"]["layout"]["margin"]["top"] == "0mm"
        assert dto["document"]["layout"]["margin"]["right"] == scale["writing_clearance"]
        dims = dto["document"]["layout"]["dimensions"].to_plain()
        assert dims["width"] == scale["width"]
        assert dims["height"] == scale["height"]
        now = _generate(stem)
        assert "page-margin(left)" in now
        assert "toolbar-edge" in now.split("#set page", 1)[0]


def test_preamble_still_emits_page_margin_side_only():
    for stem in ("supernote-nomad", "kindle-scribe", "158x210"):
        typst = Preamble(Configurator(load(base_config(stem)))).generate()
        assert "margin: page-margin(left)" in typst
        assert "toolbar-clearance)" not in typst.split("#set page", 1)[1].split("\n", 1)[0]


def test_device_typ_toolbar_edges():
    nomad = render_device_typ(get_device("supernote-nomad"))
    scribe = render_device_typ(get_device("kindle-scribe"))
    paper = render_device_typ(get_device("158x210"))
    assert "toolbar-edge = top" in nomad
    assert "toolbar-clearance = 8mm" in nomad
    assert "toolbar-edge = none" in scribe
    assert "toolbar-clearance = 0mm" in scribe
    assert "toolbar-edge = none" in paper
    assert "toolbar-clearance = 0mm" in paper


def test_manta_generate_succeeds_and_device_typ_binds_x2_chrome():
    device = get_device("manta")
    assert device.id == "supernote-manta"
    assert device.width_px == 1920
    assert device.height_px == 2560
    dto = load(base_config("supernote-manta"))
    names = [section["name"] for section in Configurator(dto).enabled_sections()]
    assert names == list(DEFAULT_SECTIONS)
    assert dto["document"]["layout"]["dimensions"].to_plain() == {
        "width": "162.56mm",
        "height": "216.75mm",
    }
    assert dto["document"]["layout"]["margin"].to_plain() == {
        "top": "8mm",
        "bottom": "0mm",
        "left": "0mm",
        "right": "4mm",
    }
    now = _generate("supernote-manta")
    assert "page-margin(left)" in now
    assert "toolbar-edge" in now.split("#set page", 1)[0]
    typst = Preamble(Configurator(dto)).generate()
    assert "margin: page-margin(left)" in typst
    assert "toolbar-clearance)" not in typst.split("#set page", 1)[1].split("\n", 1)[0]
    manta = render_device_typ(device)
    assert manta == (
        "#let page-width = 162.56mm\n"
        "#let page-height = 216.75mm\n"
        "#let toolbar-edge = top\n"
        "#let toolbar-clearance = 8mm\n"
        "#let writing-clearance = 4mm\n"
        "#let mos-width = 8mm\n"
    )


def test_every_device_generate_binds_record_chrome():
    for device in DEVICES:
        assert get_device(device.id) is device
        dto = load(base_config(device.id))
        names = [section["name"] for section in Configurator(dto).enabled_sections()]
        assert names == list(DEFAULT_SECTIONS)
        scale = device_scale(dto["device"])
        assert scale == device.scale()
        assert dto["document"]["layout"]["dimensions"].to_plain() == {
            "width": device.page_width,
            "height": device.page_height,
        }
        assert dto["document"]["layout"]["margin"].to_plain() == device_page_margin(scale)
        if device.toolbar_edge == TOOLBAR_NONE:
            assert dto["document"]["layout"]["margin"]["top"] == "0mm"
        else:
            assert dto["document"]["layout"]["margin"]["top"] == device.toolbar_clearance
        now = _generate(device.id)
        assert "page-margin(left)" in now
        assert "toolbar-edge" in now.split("#set page", 1)[0]
        typst = Preamble(Configurator(dto)).generate()
        assert "margin: page-margin(left)" in typst
        assert "toolbar-clearance)" not in typst.split("#set page", 1)[1].split("\n", 1)[0]
        assert render_device_typ(device) == (
            f"#let page-width = {device.page_width}\n"
            f"#let page-height = {device.page_height}\n"
            f"#let toolbar-edge = {device.toolbar_edge}\n"
            f"#let toolbar-clearance = {device.toolbar_clearance}\n"
            f"#let writing-clearance = {device.writing_clearance}\n"
            f"#let mos-width = {device.mos_width}\n"
        )
