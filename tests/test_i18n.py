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


def test_directory_prefers_kdl_when_both_exist(tmp_path):
    (tmp_path / "en.yaml").write_text("en:\n  week-name: YAML-Week\n", encoding="utf-8")
    (tmp_path / "en.kdl").write_text(
        "language en\nweek-name \"KDL-Week\"\n",
        encoding="utf-8",
    )
    i18n = I18n.load(tmp_path, locale="en")
    assert i18n.t("week-name") == "KDL-Week"


def test_yaml_fallback_file_path(tmp_path):
    path = tmp_path / "custom.yaml"
    path.write_text(
        "en:\n  week-name: Week\n  top-priorities: Top priorities\n  quarter:\n    short: Q\n",
        encoding="utf-8",
    )
    i18n = I18n.load(path, locale="en")
    assert i18n.t("week-name") == "Week"
    assert i18n.t("top-priorities") == "Top priorities"
    assert i18n.t("quarter.short") == "Q"


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
