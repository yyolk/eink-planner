import pytest

from parch import ConfigError
from parch.config import load
from parch.mos.chase import CHASES, MosChase
from parch.compose.coordinator import Coordinator
from parch.services.generate import Generate
from tests.helpers import base_config, load_default
from tests.toml_fixtures import short_january


def test_chases_mos_is_moschase():
    assert CHASES["mos"] is MosChase


def test_generate_mos_chase_presses():
    dto = short_january(load(base_config("supernote-nomad")))
    typst = Generate(i18n=load_default()).generate(dto)
    assert "#pagebreak()" in typst


def test_generate_missing_chase_presses():
    dto = short_january(load(base_config("supernote-nomad"))).to_plain()
    dto.pop("chase", None)
    typst = Generate(i18n=load_default()).generate(dto)
    assert "#pagebreak()" in typst


def test_generate_unknown_chase():
    dto = short_january(load(base_config("supernote-nomad"))).to_plain()
    dto["chase"] = "nope"
    with pytest.raises(ConfigError, match=r"unknown chase: nope"):
        Generate(i18n=load_default()).generate(dto)


@pytest.mark.parametrize("chase", ["", ["mos"]])
def test_generate_empty_or_nonstring_chase_is_config_error(chase):
    dto = short_january(load(base_config("supernote-nomad"))).to_plain()
    dto["chase"] = chase
    with pytest.raises(ConfigError, match=r"unknown chase:"):
        Generate(i18n=load_default()).generate(dto)


def test_coordinator_unknown_chase():
    dto = short_january(load(base_config("supernote-nomad")))
    with pytest.raises(ConfigError, match=r"unknown chase: nope"):
        Coordinator(dto, i18n=load_default(), chase_name="nope")
