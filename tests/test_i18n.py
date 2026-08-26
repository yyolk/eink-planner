from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.config import load
from eink_planner.i18n import I18n
from eink_planner.services.generate import Generate

REPO = Path(__file__).resolve().parents[1]


def test_load_en_toml_representative_keys():
    i18n = I18n.load(REPO / "locales" / "en.toml", locale="en")
    assert i18n.locale == "en"
    assert i18n.t("week_name") == "Week"
    assert i18n.t("top_priorities") == "Top priorities"
    assert i18n.t("quarter.short") == "Q"
    assert i18n.t("months.full.january") == "January"
    assert i18n.t("weekday.letter.monday") == "M"
    assert i18n.t("weekday.full.friday") == "Friday"
    assert i18n.t("projects") == "Projects"
    assert i18n.t("meetings") == "Meetings"
    assert i18n.t("habits") == "Habits"
    assert i18n.t("review") == "Review"
    assert i18n.t("topics") == "Topics"
    assert i18n.t("action_items") == "Action items"
    assert i18n.t("weekday.short.monday") == "Mon"
    assert i18n.t("weekday.short.sunday") == "Sun"
    assert i18n.t("todo") == "To do"
    assert i18n.t("doing") == "Doing"
    assert i18n.t("done") == "Done"
    assert i18n.t("title") == "TITLE"
    assert i18n.t("date") == "DATE"


def test_load_default_prefers_toml():
    i18n = I18n.load_default(REPO, "en")
    assert i18n.t("week_name") == "Week"
    assert (REPO / "locales" / "en.toml").exists()
    assert not (REPO / "locales" / "en.yaml").exists()
    assert not (REPO / "locales" / "en.kdl").exists()


def test_missing_key_is_config_error():
    i18n = I18n.load_default(REPO, "en")
    with pytest.raises(ConfigError, match="missing translation: no.such.key"):
        i18n.t("no.such.key")


@pytest.mark.parametrize("name", ["custom.yaml", "custom.yml", "custom.kdl"])
def test_yaml_or_kdl_file_path_is_config_error(tmp_path, name):
    path = tmp_path / name
    path.write_text("week_name = \"Week\"\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="(?i)locale") as exc:
        I18n.load(path, locale="en")
    assert "TOML" in str(exc.value)


def test_directory_yaml_only_is_config_error(tmp_path):
    (tmp_path / "en.yaml").write_text("language = \"en\"\nweek_name = \"YAML-Week\"\n", encoding="utf-8")
    with pytest.raises(ConfigError, match=r"locale file not found: .*en\.toml"):
        I18n.load(tmp_path, locale="en")


def test_generate_english_strings_match_previous_meanings():
    dto = load(REPO / "configs" / "supernote-nomad.toml")
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
        "Review",
    ):
        assert label in typst
    assert "Q1" in typst
    assert "[W], [M], [T], [W], [T], [F], [S], [S]" in typst


def test_path_like_locale_code_is_config_error():
    locale = "../configs/supernote-nomad"
    with pytest.raises(ConfigError, match="locale: expected a code like en") as exc:
        I18n.load_default(REPO, locale)
    assert repr(locale) in str(exc.value)


def test_load_explicit_toml_file_still_works():
    i18n = I18n.load(REPO / "locales" / "en.toml")
    assert i18n.t("week_name") == "Week"


def test_load_invalid_utf8_is_config_error(tmp_path):
    path = tmp_path / "bad.toml"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(ConfigError) as exc:
        I18n.load(path, locale="en")
    assert str(path) in str(exc.value)
