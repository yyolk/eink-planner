"""Device profile models.

TOML keys use underscores; hyphens are OK in filenames only.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    Field,
    PrivateAttr,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

from eink_planner.models.base import StrictModel

_PATTERNS = frozenset({"dotted", "lined"})


def _require_pattern(value: Any) -> str:
    text = str(value)
    if text not in _PATTERNS:
        raise ValueError(f"unknown {text!r}")
    return text


def _optional_pattern(value: str | None) -> str | None:
    if value is None:
        return None
    return _require_pattern(value)


def _scratch_pad_value(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    return _require_pattern(value)


OptionalPattern = Annotated[str | None, AfterValidator(_optional_pattern)]
ScratchPad = Annotated[str | None, AfterValidator(_scratch_pad_value)]


class Device(StrictModel):
    name: str
    width: str
    height: str
    ppi: StrictInt | None = None


class Calendar(StrictModel):
    year: StrictInt
    week_starts: str


class Stroke(StrictModel):
    regular: str
    thick: str


class TypeStyle(StrictModel):
    body: str
    h1: str


class Margin(StrictModel):
    top: str
    bottom: str
    left: str
    right: str


class Gutter(StrictModel):
    column: str
    row: str | None = None  # optional; adapter ignores it


class Heading(StrictModel):
    height: str | None = None
    align: str | None = None


class LittleCalendar(StrictModel):
    week_placement: str | None = None
    inset: str | None = None
    show_month_name: StrictBool | None = None


class Style(StrictModel):
    stroke: Stroke
    type: TypeStyle
    margin: Margin
    gutter: Gutter
    regular_height: str | None = None
    link_padding: str | None = None
    scratch_pad: ScratchPad = None
    heading: Heading | None = None
    little_calendar: LittleCalendar | None = None


class Layout(StrictModel):
    name: Literal["mos"]
    side_menu: str
    side_menu_width: str
    reverse_months_quarters: StrictBool
    menu_rotate: str
    column_gutter: str
    row_gutter: str
    reverse_months_quarters_items: StrictBool | None = None

    @field_validator("side_menu", mode="before")
    @classmethod
    def _side_menu(cls, value: Any) -> str:
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in {"left", "right"}:
                return lowered
        raise ValueError("expected left or right")


class CoverSection(StrictModel):
    title: str
    font_size: str


class AnnualSection(StrictModel):
    row_gutter: str | None = None
    show_month_name: StrictBool | None = None
    little_calendar: LittleCalendar | None = None


class QuarterlySection(StrictModel):
    months_column: str
    pattern: OptionalPattern = None
    show_month_name: StrictBool | None = None
    little_calendar: LittleCalendar | None = None


class MonthlySection(StrictModel):
    week_placement: str
    week_label_rotation: str
    daily_cell_height: str
    pattern: OptionalPattern = None


class WeeklySection(StrictModel):
    column_gutter: str
    pattern: OptionalPattern = None


class Schedule(StrictModel):
    hour_from: StrictInt
    hour_to: StrictInt
    time_format: str | None = None
    trailing_half_hour: StrictBool = True

    @model_validator(mode="after")
    def _hour_range(self) -> Schedule:
        if self.hour_from >= self.hour_to:
            raise ValueError("hour_from must be < hour_to")
        return self


class Priorities(StrictModel):
    count: StrictInt


class Notes(StrictModel):
    pattern: OptionalPattern = None
    title_height: str
    height: str | None = None


class DailyTrack(StrictModel):
    schedule: Schedule | None = None
    little_calendar: LittleCalendar | None = None
    priorities: Priorities | None = None
    notes: Notes | None = None
    _component_order: list[str] = PrivateAttr(default_factory=list)

    @model_validator(mode="wrap")
    @classmethod
    def _capture_order(cls, data: Any, handler: Any) -> DailyTrack:
        order: list[str] = []
        if isinstance(data, dict):
            order = [key for key in data if key in _DAILY_COMPONENTS]
        inst = handler(data)
        if order:
            object.__setattr__(inst, "_component_order", order)
        return inst

    @model_validator(mode="after")
    def _at_least_one(self) -> DailyTrack:
        if not any(getattr(self, key) is not None for key in DailyTrack.model_fields):
            raise ValueError("each of left / right must have at least one component")
        return self

    def component_keys(self) -> list[str]:
        if self._component_order:
            return list(self._component_order)
        return [key for key in _DAILY_COMPONENTS if getattr(self, key) is not None]


_DAILY_COMPONENTS = tuple(DailyTrack.model_fields)


class DailySection(StrictModel):
    columns: list[str]
    item_spacing: str
    left: DailyTrack | None = None
    right: DailyTrack | None = None

    @field_validator("columns")
    @classmethod
    def _two_columns(cls, value: list[str]) -> list[str]:
        if len(value) != 2:
            raise ValueError("columns length must be 2")
        return value


class DailyNotesSection(StrictModel):
    pages: StrictInt
    pattern: OptionalPattern = None


class ProjectsSection(StrictModel):
    pages: StrictInt = 20
    card_rows: StrictInt = 8


class ReviewSection(StrictModel):
    weeks_per_page: StrictInt = 13

    @model_validator(mode="after")
    def _weeks_per_page_positive(self) -> ReviewSection:
        if self.weeks_per_page < 1:
            raise ValueError("weeks_per_page must be at least 1")
        return self


class HabitsSection(StrictModel):
    habit_columns: StrictInt = 6
    names: list[str] = []

    @model_validator(mode="after")
    def _names_fit_columns(self) -> HabitsSection:
        if len(self.names) > self.habit_columns:
            raise ValueError(
                f"names has {len(self.names)} entries but habit_columns is {self.habit_columns}"
            )
        return self


class ColophonSection(StrictModel):
    title: str | None = None
    highlight: StrictBool | None = None


class SectionTables(StrictModel):
    cover: CoverSection | None = None
    annual: AnnualSection | None = None
    quarterly: QuarterlySection | None = None
    monthly: MonthlySection | None = None
    weekly: WeeklySection | None = None
    daily: DailySection | None = None
    daily_notes: DailyNotesSection | None = None
    projects: ProjectsSection | None = None
    habits: HabitsSection | None = None
    review: ReviewSection | None = None
    colophon: ColophonSection | list[ColophonSection] | None = None

    @field_validator("colophon", mode="before")
    @classmethod
    def _colophon_shape(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, dict):
                    raise ValueError("expected a table")
            return value
        if not isinstance(value, dict):
            raise ValueError("expected a table")
        return value


KNOWN_SECTIONS = frozenset(SectionTables.model_fields)


class DeviceProfile(StrictModel):
    """Validated device profile.

    Orphan [section.*] tables are ALLOWED and ignored at generate time.
    Disabling a section = remove/comment its name in `sections` only.
    Generator must iterate profile.sections, not every key under section.
    Unknown section TABLE names (typos like section.proejcts) are still
    forbidden via extra="forbid".
    """

    device: Device
    calendar: Calendar
    style: Style
    layout: Layout
    sections: list[str]
    section: SectionTables = Field(default_factory=SectionTables)

    @model_validator(mode="before")
    @classmethod
    def _reject_debug(cls, data: Any) -> Any:
        if isinstance(data, dict) and "debug" in data:
            raise ValueError("debug does not belong in the config; use `lyp generate --debug`")
        return data

    @field_validator("sections")
    @classmethod
    def _check_sections(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("sections must be non-empty")
        seen: set[str] = set()
        for name in value:
            if name not in KNOWN_SECTIONS:
                raise ValueError(f"unknown section: {name}")
            if name in seen and name != "colophon":
                raise ValueError(f"duplicate section: {name}")
            seen.add(name)
        return value

    @model_validator(mode="after")
    def _nested_section_rules(self) -> DeviceProfile:
        names = set(self.sections)
        tables = self.section
        if "cover" in names and tables.cover is None:
            raise ValueError("cover is listed in sections but [section.cover] is missing")
        if "quarterly" in names and tables.quarterly is None:
            raise ValueError("quarterly is listed in sections but [section.quarterly] is missing")
        if "monthly" in names and tables.monthly is None:
            raise ValueError("monthly is listed in sections but [section.monthly] is missing")
        if "weekly" in names and tables.weekly is None:
            raise ValueError("weekly is listed in sections but [section.weekly] is missing")
        if "daily_notes" in names and tables.daily_notes is None:
            raise ValueError("daily_notes is listed in sections but [section.daily_notes] is missing")
        if "daily" in names:
            if tables.daily is None:
                raise ValueError("daily is listed in sections but [section.daily] is missing")
            if tables.daily.left is None or tables.daily.right is None:
                raise ValueError("section.daily must have both left and right tracks")
        if "projects" in names and tables.projects is None:
            tables.projects = ProjectsSection()
        if "habits" in names and tables.habits is None:
            tables.habits = HabitsSection()
        if "review" in names and tables.review is None:
            tables.review = ReviewSection()
        return self


def load_device_profile(path: Path) -> DeviceProfile:
    with path.open("rb") as f:
        return DeviceProfile.model_validate(tomllib.load(f))
