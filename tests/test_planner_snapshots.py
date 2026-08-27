"""Syrupy snapshots of the planner page tree and a short January cut."""

import pytest

from parch import __version__
from parch.config import load
from parch.mos.builder import Builder
from parch.mos.coordinator import Coordinator
from tests.helpers import base_config, load_default
from tests.toml_fixtures import short_january

_PROFILES = ("supernote-nomad", "158x210-mos-left")
_CRITICAL = ("annual", "monthly", "weekly", "daily", "colophon")


def _coordinator(dto):
    return Coordinator(dto, i18n=load_default())


def _tree(pairs):
    return [{"name": section, "pages": len(pages)} for section, pages in pairs]


def _critical_pages(coord, pairs):
    builder = Builder(
        i18n=coord.i18n,
        configurator=coord.configurator,
        manifest=coord.manifest,
    )
    by_name = dict(pairs)
    sample = {"preamble": builder.preamble.generate()}
    for section in _CRITICAL:
        page = by_name[section][0]
        text = page.content if page.raw_typst else builder._layout_page(page)
        if section == "colophon":
            text = text.replace(__version__, "VERSION")
        sample[section] = text
    return sample


@pytest.mark.parametrize("name", _PROFILES)
def test_shipped_planner_page_tree(snapshot, name):
    dto = load(base_config(name))
    pairs = _coordinator(dto).section_pages()
    assert _tree(pairs) == snapshot


@pytest.mark.parametrize("name", _PROFILES)
def test_short_january_critical_pages(snapshot, name):
    dto = short_january(load(base_config(name)))
    coord = _coordinator(dto)
    pairs = coord.section_pages()
    assert _critical_pages(coord, pairs) == snapshot
