import pytest

from parch import ConfigError
from parch.sections import SECTIONS
from parch.mos.coordinator import Coordinator
from tests.helpers import load_default

_OLD_COMPONENTS = {
    "cover_plain",
    "index",
    "annual",
    "quarterly",
    "monthly",
    "weekly",
    "daily",
    "daily_notes",
    "projects",
    "meetings",
    "habits",
    "review",
    "tasks",
    "colophon",
}


def test_sections_keys_match_former_components():
    assert set(SECTIONS) == _OLD_COMPONENTS


def test_unknown_section_class_raises_config_error():
    dto = {
        "planner": {
            "sections": [
                {"class": "not_a_section", "name": "bogus", "enabled": True, "params": {}},
            ]
        }
    }
    with pytest.raises(ConfigError, match=r"unknown section: not_a_section"):
        Coordinator(dto, i18n=load_default()).section_pages()
