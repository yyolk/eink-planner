"""Pydantic device/locale models: happy path and nested validation."""

import tomllib

import pytest
from pydantic import ValidationError

from parch.models import DeviceProfile, load_device_profile, load_locale
from tests.toml_fixtures import _minimal
from tests.helpers import base_config, packaged_locale

PAPER_158 = base_config("158x210")
LOCALE = packaged_locale()


def test_happy_path_mos_left():
    profile = load_device_profile(PAPER_158)
    assert profile.device.name == "158x210"
    assert profile.mos.side_menu == "left"
    assert profile.sections[-1] == "colophon"
    assert profile.section.daily is not None
    assert profile.section.daily.left is not None
    assert profile.section.daily.right is not None
    assert profile.section.daily.columns == ["3fr", "5fr"]


def test_happy_path_side_menu_right_keeps_ltr_well():
    text = _minimal(
        enable=["daily"],
        mos="""[mos]
side_menu = "right"
side_menu_width = "10mm"
reverse_months_quarters = true
menu_rotate = "270deg"
column_gutter = "1.5mm"
row_gutter = "1.5mm"
""",
        sections="""[section.daily]
columns = ["3fr", "5fr"]
item_spacing = "5mm"

[section.daily.left.schedule]
hour_from = 8
hour_to = 20

[section.daily.right.priorities]
count = 5
""",
    )
    profile = DeviceProfile.model_validate(tomllib.loads(text))
    assert profile.mos.side_menu == "right"
    assert profile.section.daily is not None
    assert profile.section.daily.columns == ["3fr", "5fr"]
    assert profile.section.daily.left is not None
    assert profile.section.daily.right is not None
    assert profile.section.daily.left.schedule is not None
    assert profile.section.daily.right.priorities is not None


def test_happy_path_locale():
    locale = load_locale(LOCALE)
    assert locale.week_name == "Week"
    assert locale.projects == "Projects"
    assert locale.meetings == "Meetings"
    assert locale.habits == "Habits"
    assert locale.review == "Review"
    assert locale.topics == "Topics"
    assert locale.action_items == "Action items"
    assert locale.weekday.short.monday == "Mon"
    assert locale.quarter.short == "Q"


def test_unknown_key_is_validation_error():
    data = tomllib.loads(_minimal())
    data["foo"] = 1
    with pytest.raises(ValidationError):
        DeviceProfile.model_validate(data)


def test_unknown_section_name_is_validation_error():
    data = tomllib.loads(_minimal(enable=["mystery"], sections=""))
    with pytest.raises(ValidationError):
        DeviceProfile.model_validate(data)


def test_daily_listed_but_table_missing_is_validation_error():
    data = tomllib.loads(_minimal(enable=["daily"], sections=""))
    with pytest.raises(ValidationError):
        DeviceProfile.model_validate(data)


@pytest.mark.parametrize("kind", ["quarterly", "monthly", "weekly"])
def test_calendar_section_listed_but_table_missing_is_validation_error(kind):
    data = tomllib.loads(_minimal(enable=[kind], sections=""))
    with pytest.raises(ValidationError, match=f"{kind} is listed in sections but"):
        DeviceProfile.model_validate(data)


def test_schedule_hour_from_not_less_than_hour_to():
    text = _minimal(
        enable=["daily"],
        sections="""[section.daily]
columns = ["3fr", "5fr"]
item_spacing = "1mm"

[section.daily.left.schedule]
hour_from = 20
hour_to = 8

[section.daily.right.priorities]
count = 1
""",
    )
    with pytest.raises(ValidationError):
        DeviceProfile.model_validate(tomllib.loads(text))


def test_daily_columns_length_not_two():
    text = _minimal(
        enable=["daily"],
        sections="""[section.daily]
columns = ["3fr"]
item_spacing = "1mm"

[section.daily.left.schedule]
hour_from = 8
hour_to = 20

[section.daily.right.priorities]
count = 1
""",
    )
    with pytest.raises(ValidationError):
        DeviceProfile.model_validate(tomllib.loads(text))


def test_device_profile_json_schema_is_dict():
    schema = DeviceProfile.model_json_schema()
    assert isinstance(schema, dict)
    assert "properties" in schema


def test_string_field_rejects_integer():
    data = tomllib.loads(_minimal())
    data["calendar"]["week_starts"] = 1
    with pytest.raises(ValidationError):
        DeviceProfile.model_validate(data)


def test_device_ppi_is_optional():
    text = _minimal(
        device="""[device]
name = "x"
width = "100mm"
height = "120mm"
""",
    )
    assert "ppi" not in text
    profile = DeviceProfile.model_validate(tomllib.loads(text))
    assert profile.device.ppi is None


def test_known_sections_match_section_tables():
    from parch.models import KNOWN_SECTIONS
    from parch.models.device import SectionTables
    assert KNOWN_SECTIONS == frozenset(SectionTables.model_fields)
    assert {"cover", "daily", "daily_notes", "projects", "meetings", "habits", "review", "tasks", "colophon"} <= KNOWN_SECTIONS


def test_daily_components_match_daily_track_fields():
    from parch.models.device import DailyTrack, _DAILY_COMPONENTS
    assert tuple(DailyTrack.model_fields) == _DAILY_COMPONENTS
    assert set(_DAILY_COMPONENTS) == {"schedule", "little_calendar", "priorities", "notes"}


def test_unknown_grid_pattern_on_notes_is_validation_error():
    from parch.models.device import DailyNotesSection, Notes
    with pytest.raises(ValidationError):
        DailyNotesSection(pages=1, pattern="grid")
    with pytest.raises(ValidationError):
        Notes(pattern="grid", title_height="4mm")


def test_habits_section_defaults_and_names_length():
    from parch.models.device import HabitsSection

    section = HabitsSection()
    assert section.habit_columns == 4
    assert section.names == []
    ok = HabitsSection(habit_columns=2, names=["A", "B"])
    assert ok.names == ["A", "B"]
    with pytest.raises(ValidationError, match="habit_columns"):
        HabitsSection(habit_columns=2, names=["A", "B", "C"])


def test_review_section_defaults_and_weeks_per_page():
    from parch.models.device import ReviewSection

    section = ReviewSection()
    assert section.weeks_per_page == 13
    assert section.pattern == "lined"
    assert ReviewSection(weeks_per_page=12).weeks_per_page == 12
    assert ReviewSection(pattern="dotted").pattern == "dotted"
    with pytest.raises(ValidationError, match="weeks_per_page"):
        ReviewSection(weeks_per_page=0)
    with pytest.raises(ValidationError, match="unknown"):
        ReviewSection(pattern="grid")



def test_projects_section_defaults():
    from parch.models.device import ProjectsSection

    section = ProjectsSection()
    assert section.pages == 16
    assert section.card_rows == 5
    assert ProjectsSection(pages=20, card_rows=8).pages == 20


def test_meetings_section_defaults_and_index_pages():
    from parch.models.device import MeetingsSection

    section = MeetingsSection()
    assert section.index_pages == 1
    assert MeetingsSection(index_pages=2).index_pages == 2
    with pytest.raises(ValidationError, match="index_pages"):
        MeetingsSection(index_pages=0)
    with pytest.raises(ValidationError):
        MeetingsSection(pages=16)
