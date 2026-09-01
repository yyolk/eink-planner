import pytest

from parch import ConfigError
from parch.config import StrictDict
from parch.devices import KINDLE_SCRIBE, PAPER_158X210, SUPERNOTE_MANTA, SUPERNOTE_NOMAD, get_device
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
