"""Hawk generate against current output: Nomad matches; Scribe/158 drop the 5mm top."""

from pathlib import Path

from parch.config import load
from parch.devices import get_device
from parch.i18n import I18n
from parch.models.device import device_page_margin, device_scale
from parch.mos.configurator import Configurator
from parch.mos.preamble import Preamble, render_device_typ
from parch.services.generate import Generate
from tests.helpers import base_config
from tests.toml_fixtures import short_january

_BASELINE = Path("/tmp/parch-hawk-baseline")
_PREAMBLE_MARKERS = (
    '#import "device.typ"',
    '#import "supernote-nomad.typ"',
    '#import "kindle-scribe.typ"',
    '#import "158x210.typ"',
)


def _generate(stem: str) -> str:
    dto = short_january(load(base_config(stem)))
    return Generate(i18n=I18n.load_default("en")).generate(dto)


def _strip_preamble(typst: str) -> str:
    lines = typst.splitlines(keepends=True)
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("#let quarter_well"):
            start = i + 1
            break
    return "".join(lines[start:])


def test_nomad_generate_matches_current_body():
    dto = load(base_config("supernote-nomad"))
    assert dto["document"]["layout"]["margin"].to_plain() == {
        "top": "8mm",
        "bottom": "0mm",
        "left": "0mm",
        "right": "4mm",
    }
    now = _generate("supernote-nomad")
    baseline_path = _BASELINE / "supernote-nomad-jan.typst"
    if baseline_path.is_file():
        baseline = baseline_path.read_text(encoding="utf-8")
        assert _strip_preamble(now) == _strip_preamble(baseline)


def test_scribe_and_158_generate_bodies_match_only_toolbar_changes():
    for stem in ("kindle-scribe", "158x210"):
        dto = load(base_config(stem))
        scale = device_scale(dto["device"])
        assert scale["toolbar_edge"] == "none"
        assert dto["document"]["layout"]["margin"].to_plain() == device_page_margin(scale)
        assert dto["document"]["layout"]["margin"]["top"] == "0mm"
        assert dto["document"]["layout"]["margin"]["right"] == scale["writing_clearance"]
        dims = dto["document"]["layout"]["dimensions"].to_plain()
        assert dims["width"] == scale["width"]
        assert dims["height"] == scale["height"]
        now = _generate(stem)
        baseline_path = _BASELINE / f"{stem}-jan.typst"
        if baseline_path.is_file():
            baseline = baseline_path.read_text(encoding="utf-8")
            assert _strip_preamble(now) == _strip_preamble(baseline)


def test_preamble_still_emits_page_margin_side_only():
    for stem in ("supernote-nomad", "kindle-scribe", "158x210"):
        typst = Preamble(Configurator(load(base_config(stem)))).generate()
        assert "margin: page-margin(left)" in typst
        assert "toolbar-clearance)" not in typst.split("#set page", 1)[1].split("\n", 1)[0]


def test_device_typ_toolbar_edges():
    assert "toolbar-edge = top" in render_device_typ(get_device("supernote-nomad"))
    assert "toolbar-clearance = 8mm" in render_device_typ(get_device("supernote-nomad"))
    assert "toolbar-edge = none" in render_device_typ(get_device("kindle-scribe"))
    assert "toolbar-edge = none" in render_device_typ(get_device("158x210"))
