import pytest

from parch import ConfigError
from parch.config import StrictDict
from parch.devices import KINDLE_SCRIBE, SUPERNOTE_NOMAD
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
