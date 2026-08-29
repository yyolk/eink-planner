import pytest

from parch import ConfigError
from parch.config import load
from parch.mos.chase import CHASES, MosChase
from parch.mos.coordinator import Coordinator
from parch.services.generate import Generate
from tests.helpers import base_config, load_default
from tests.toml_fixtures import short_january


def test_chases_mos_is_moschase():
    assert CHASES["mos"] is MosChase


def test_generate_mos_template_presses():
    dto = short_january(load(base_config("supernote-nomad")))
    typst = Generate(i18n=load_default()).generate(dto)
    assert "#pagebreak()" in typst


def test_generate_missing_template_presses():
    dto = short_january(load(base_config("supernote-nomad"))).to_plain()
    dto.pop("template", None)
    typst = Generate(i18n=load_default()).generate(dto)
    assert "#pagebreak()" in typst


def test_generate_unknown_chase():
    dto = short_january(load(base_config("supernote-nomad"))).to_plain()
    dto["template"] = "nope"
    with pytest.raises(ConfigError, match=r"unknown chase: nope"):
        Generate(i18n=load_default()).generate(dto)


def test_coordinator_unknown_chase():
    dto = short_january(load(base_config("supernote-nomad")))
    with pytest.raises(ConfigError, match=r"unknown chase: nope"):
        Coordinator(dto, i18n=load_default(), chase_name="nope")
