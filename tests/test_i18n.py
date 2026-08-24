from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.config import load
from eink_planner.i18n import I18n
from eink_planner.services.generate import Generate

REPO = Path(__file__).resolve().parents[1]


def test_load_en_kdl_representative_keys():
    i18n = I18n.load(REPO / "locales" / "en.kdl", locale="en")
    assert i18n.locale == "en"
    assert i18n.t("week-name") == "Week"
    assert i18n.t("top-priorities") == "Top priorities"
    assert i18n.t("quarter.short") == "Q"
    assert i18n.t("months.full.january") == "January"
    assert i18n.t("weekday.letter.monday") == "M"
    assert i18n.t("weekday.full.friday") == "Friday"


def test_load_default_prefers_kdl():
    i18n = I18n.load_default(REPO, "en")
    assert i18n.t("week-name") == "Week"
    assert (REPO / "locales" / "en.kdl").exists()
    assert not (REPO / "locales" / "en.yaml").exists()


def test_missing_key_is_config_error():
    i18n = I18n.load_default(REPO, "en")
    with pytest.raises(ConfigError, match="missing translation: no.such.key"):
        i18n.t("no.such.key")


@pytest.mark.parametrize("name", ["custom.yaml", "custom.yml"])
def test_yaml_file_path_is_config_error(tmp_path, name):
    path = tmp_path / name
    path.write_text(
        "en:\n  week-name: Week\n  top-priorities: Top priorities\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="(?i)locale") as exc:
        I18n.load(path, locale="en")
    assert "KDL" in str(exc.value)


def test_directory_yaml_only_is_config_error(tmp_path):
    (tmp_path / "en.yaml").write_text("en:\n  week-name: YAML-Week\n", encoding="utf-8")
    with pytest.raises(ConfigError, match=r"locale file not found: .*en\.kdl"):
        I18n.load(tmp_path, locale="en")


def test_generate_english_strings_match_previous_meanings():
    dto = load(REPO / "configs" / "supernote-nomad.kdl")
    data = dto.to_plain()
    data["planner"]["params"]["end_date"] = "2026-01-07"
    typst = Generate(i18n=I18n.load_default(REPO, "en")).generate(data)
    for label in (
        "Week",
        "Schedule",
        "Top priorities",
        "Notes",
        "More",
        "Quarter",
        "Jan",
        "Monday",
    ):
        assert label in typst
    assert "Q1" in typst
    assert "[W], [M], [T], [W], [T], [F], [S], [S]" in typst


def test_path_like_locale_code_is_config_error():
    locale = "../configs/supernote-nomad"
    with pytest.raises(ConfigError, match="locale: expected a code like en") as exc:
        I18n.load_default(REPO, locale)
    assert repr(locale) in str(exc.value)


def test_load_explicit_kdl_file_still_works():
    i18n = I18n.load(REPO / "locales" / "en.kdl")
    assert i18n.t("week-name") == "Week"

