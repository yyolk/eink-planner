import pytest

from parch import ConfigError
from parch.config import StrictDict
from parch.devices import (
    DEVICES,
    KINDLE_SCRIBE,
    KINDLE_SCRIBE_11,
    KINDLE_SCRIBE_COLORSOFT,
    PAPER_158X210,
    REMARKABLE_1,
    REMARKABLE_2,
    REMARKABLE_PAPER_PRO,
    REMARKABLE_PAPER_PRO_MOVE,
    REMARKABLE_PAPER_PURE,
    SUPERNOTE_A5,
    SUPERNOTE_A5X,
    SUPERNOTE_A6,
    SUPERNOTE_A6X,
    SUPERNOTE_MANTA,
    SUPERNOTE_NOMAD,
    TOOLBAR_NONE,
    TOOLBAR_TOP,
    get_device,
    known_device_ids,
)
from parch.services.job_file import COMPACT_STYLE, DEFAULT_SECTIONS, JOB_DEFAULTS, NOMAD_STYLE
from parch.mos.configurator import Configurator
from parch.mos.preamble import Preamble


def test_strict_dict_dotted_path():
    dto = StrictDict({"document": {"text": {"h1": "10mm"}}})
    with pytest.raises(ConfigError, match=r"document\.text\.size"):
        dto.dig_bang("document", "text", "size")


def test_preamble_raises_on_missing_text_size():
    dto = StrictDict(
        {
            "device": "158x210",
            "document": {
                "layout": {
                    "dimensions": {"width": "158mm", "height": "210mm"},
                    "margin": {"top": "10mm", "right": "5mm", "bottom": "0mm", "left": "0mm"},
                },
                "text": {"h1": "10mm"},
            },
            "planner": {
                "params": {
                    "regular_stroke": "0.4pt",
                    "thick_stroke": "0.8pt",
                    "regular_height": "5mm",
                    "regular_column_gutter": "10pt",
                    "scratch_pad": "dotted",
                    "link_padding": "8pt",
                }
            },
        }
    )
    with pytest.raises(ConfigError, match=r"document\.text\.size"):
        Preamble(Configurator(dto)).generate()


def test_device_presets_match_glass():
    assert SUPERNOTE_NOMAD.width_mm == 118.87
    assert SUPERNOTE_NOMAD.height_mm == 158.5
    assert SUPERNOTE_NOMAD.width_pt == 336.96
    assert SUPERNOTE_NOMAD.height_pt == 449.28
    assert KINDLE_SCRIBE.width_mm == 157.48
    assert KINDLE_SCRIBE.height_mm == 209.97
    assert KINDLE_SCRIBE.width_pt == 446.4
    assert KINDLE_SCRIBE.height_pt == 595.2
    assert SUPERNOTE_NOMAD.toolbar_edge == "top"
    assert KINDLE_SCRIBE.toolbar_edge == "none"
    assert PAPER_158X210.id == "158x210"
    assert PAPER_158X210.page_width == "158mm"
    assert PAPER_158X210.page_height == "210mm"
    assert PAPER_158X210.toolbar_edge == "none"
    assert PAPER_158X210.width_mm == 158.0
    assert PAPER_158X210.height_mm == 210.0
    assert SUPERNOTE_MANTA.width_mm == 162.56
    assert SUPERNOTE_MANTA.height_mm == 216.75
    assert SUPERNOTE_MANTA.width_pt == 460.8
    assert SUPERNOTE_MANTA.height_pt == 614.4
    assert SUPERNOTE_MANTA.toolbar_edge == "top"
    assert SUPERNOTE_MANTA.width_px == 1920
    assert SUPERNOTE_MANTA.height_px == 2560
    assert get_device("manta") is SUPERNOTE_MANTA
    assert get_device("supernote-manta") is SUPERNOTE_MANTA


_REMARKABLE = (
    (REMARKABLE_1, "rm1", 226, 1404, 1872, "157.79mm", "210.39mm", 157.79, 210.39, 447.29, 596.39),
    (REMARKABLE_2, "rm2", 226, 1404, 1872, "157.79mm", "210.39mm", 157.79, 210.39, 447.29, 596.39),
    (
        REMARKABLE_PAPER_PURE,
        "paper-pure",
        226,
        1404,
        1872,
        "157.79mm",
        "210.39mm",
        157.79,
        210.39,
        447.29,
        596.39,
    ),
    (
        REMARKABLE_PAPER_PRO,
        "paper-pro",
        229,
        1620,
        2160,
        "179.69mm",
        "239.58mm",
        179.69,
        239.58,
        509.34,
        679.13,
    ),
    (
        REMARKABLE_PAPER_PRO_MOVE,
        "paper-pro-move",
        264,
        954,
        1696,
        "91.79mm",
        "163.18mm",
        91.79,
        163.18,
        260.18,
        462.55,
    ),
)


@pytest.mark.parametrize(
    "device, alias, ppi, width_px, height_px, page_width, page_height, width_mm, height_mm, width_pt, height_pt",
    _REMARKABLE,
    ids=[row[0].id for row in _REMARKABLE],
)
def test_remarkable_records_match_glass(
    device,
    alias,
    ppi,
    width_px,
    height_px,
    page_width,
    page_height,
    width_mm,
    height_mm,
    width_pt,
    height_pt,
):
    assert device.ppi == ppi
    assert device.width_px == width_px
    assert device.height_px == height_px
    assert device.page_width == page_width
    assert device.page_height == page_height
    assert device.width_mm == width_mm
    assert device.height_mm == height_mm
    assert device.width_pt == width_pt
    assert device.height_pt == height_pt
    assert device.toolbar_edge == TOOLBAR_NONE
    assert device.toolbar_clearance == "0mm"
    assert device.writing_clearance == "5mm"
    assert device.mos_width == "10mm"
    assert get_device(device.id) is device
    assert get_device(alias) is device
    assert get_device(alias).id == device.id
    assert device is not PAPER_158X210
    assert device.page_width != "158mm"
    assert device.ppi != PAPER_158X210.ppi


def test_remarkable_ten_point_three_stay_three_records():
    assert REMARKABLE_1 is not REMARKABLE_2
    assert REMARKABLE_1 is not REMARKABLE_PAPER_PURE
    assert REMARKABLE_2 is not REMARKABLE_PAPER_PURE
    assert {REMARKABLE_1.id, REMARKABLE_2.id, REMARKABLE_PAPER_PURE.id} == {
        "remarkable-1",
        "remarkable-2",
        "remarkable-paper-pure",
    }


def test_job_defaults_cover_every_canonical_id():
    assert set(JOB_DEFAULTS) == set(known_device_ids())
    assert tuple(d.id for d in DEVICES) == known_device_ids()
    for device_id, defaults in JOB_DEFAULTS.items():
        assert defaults.sections == DEFAULT_SECTIONS
        assert defaults.style in (NOMAD_STYLE, COMPACT_STYLE)
        assert get_device(device_id).id == device_id


_LINEAGE = (
    (SUPERNOTE_A5, "a5", 226, 1404, 1872, "157.79mm", "210.39mm", 157.79, 210.39, 447.29, 596.39, TOOLBAR_TOP),
    (SUPERNOTE_A5X, "a5x", 226, 1404, 1872, "157.79mm", "210.39mm", 157.79, 210.39, 447.29, 596.39, TOOLBAR_TOP),
    (SUPERNOTE_A6, "a6", 300, 1404, 1872, "118.87mm", "158.5mm", 118.87, 158.5, 336.96, 449.28, TOOLBAR_TOP),
    (SUPERNOTE_A6X, "a6x", 300, 1404, 1872, "118.87mm", "158.5mm", 118.87, 158.5, 336.96, 449.28, TOOLBAR_TOP),
    (KINDLE_SCRIBE_11, "scribe-11", 300, 1980, 2640, "167.64mm", "223.52mm", 167.64, 223.52, 475.2, 633.6, TOOLBAR_NONE),
    (
        KINDLE_SCRIBE_COLORSOFT,
        "colorsoft",
        300,
        1980,
        2640,
        "167.64mm",
        "223.52mm",
        167.64,
        223.52,
        475.2,
        633.6,
        TOOLBAR_NONE,
    ),
)


@pytest.mark.parametrize(
    "device, alias, ppi, width_px, height_px, page_width, page_height, width_mm, height_mm, width_pt, height_pt, toolbar_edge",
    _LINEAGE,
    ids=[row[0].id for row in _LINEAGE],
)
def test_lineage_records_match_glass(
    device,
    alias,
    ppi,
    width_px,
    height_px,
    page_width,
    page_height,
    width_mm,
    height_mm,
    width_pt,
    height_pt,
    toolbar_edge,
):
    assert device.ppi == ppi
    assert device.width_px == width_px
    assert device.height_px == height_px
    assert device.page_width == page_width
    assert device.page_height == page_height
    assert device.width_mm == width_mm
    assert device.height_mm == height_mm
    assert device.width_pt == width_pt
    assert device.height_pt == height_pt
    assert device.toolbar_edge == toolbar_edge
    if toolbar_edge == TOOLBAR_TOP:
        assert device.toolbar_clearance == "8mm"
        assert device.writing_clearance == "4mm"
        assert device.mos_width == "8mm"
    else:
        assert device.toolbar_clearance == "0mm"
        assert device.writing_clearance == "5mm"
        assert device.mos_width == "10mm"
    assert get_device(device.id) is device
    assert get_device(alias) is device
    assert get_device(alias).id == device.id


def test_lineage_twins_stay_separate_records():
    assert SUPERNOTE_A5 is not SUPERNOTE_A5X
    assert SUPERNOTE_A6 is not SUPERNOTE_A6X
    assert KINDLE_SCRIBE_11 is not KINDLE_SCRIBE_COLORSOFT
    assert KINDLE_SCRIBE is not KINDLE_SCRIBE_11
    assert KINDLE_SCRIBE.width_px == 1860
    assert KINDLE_SCRIBE.height_px == 2480
    assert SUPERNOTE_NOMAD.width_px == 1404
    assert SUPERNOTE_NOMAD.height_px == 1872
    assert SUPERNOTE_NOMAD.ppi == 300
    assert SUPERNOTE_MANTA.width_px == 1920
    assert SUPERNOTE_MANTA.height_px == 2560


def test_every_device_scale_matches_record():
    for device in DEVICES:
        scale = device.scale()
        assert scale["width"] == device.page_width
        assert scale["height"] == device.page_height
        assert scale["toolbar_edge"] == device.toolbar_edge
        assert scale["toolbar_clearance"] == device.toolbar_clearance
        assert scale["writing_clearance"] == device.writing_clearance
        assert scale["mos_width"] == device.mos_width
        assert JOB_DEFAULTS[device.id].sections is not None
        assert get_device(device.id) is device
