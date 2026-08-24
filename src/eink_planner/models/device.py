"""Device profile models.

TOML keys use underscores; hyphens are OK in filenames only.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    Field,
    PrivateAttr,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

from eink_planner.models.base import StrictModel

KNOWN_SECTIONS = frozenset(
    {
        "cover",
        "annual",
        "quarterly",
        "monthly",
        "weekly",
        "daily",
        "daily_notes",
        "projects",
        "colophon",
    }
)

_PATTERNS = frozenset({"dotted", "lined"})
_DAILY_COMPONENTS = ("schedule", "little_calendar", "priorities", "notes")


def _require_pattern(value: Any) -> str:
    text = str(value)
    if text not in _PATTERNS:
        raise ValueError(f"unknown {text!r}")
    return text


class Device(StrictModel):
    name: str
    width: str
    height: str
    ppi: StrictInt


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
    scratch_pad: str | None = None
    heading: Heading | None = None
    little_calendar: LittleCalendar | None = None

    @field_validator("scratch_pad")
    @classmethod
    def _scratch_pad(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_pattern(value)


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
    pattern: str | None = None
    show_month_name: StrictBool | None = None
    little_calendar: LittleCalendar | None = None

    @field_validator("pattern")
    @classmethod
    def _pattern(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_pattern(value)


class MonthlySection(StrictModel):
    week_placement: str
    week_label_rotation: str
    daily_cell_height: str
    pattern: str | None = None

    @field_validator("pattern")
    @classmethod
    def _pattern(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_pattern(value)


class WeeklySection(StrictModel):
    column_gutter: str
    pattern: str | None = None

    @field_validator("pattern")
    @classmethod
    def _pattern(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_pattern(value)


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
    pattern: str | None = None
    title_height: str
    height: str | None = None

    @field_validator("pattern")
    @classmethod
    def _pattern(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_pattern(value)


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
        if not any((self.schedule, self.little_calendar, self.priorities, self.notes)):
            raise ValueError("each of left / right must have at least one component")
        return self

    def component_keys(self) -> list[str]:
        if self._component_order:
            return list(self._component_order)
        return [key for key in _DAILY_COMPONENTS if getattr(self, key) is not None]


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
    pattern: str | None = None

    @field_validator("pattern")
    @classmethod
    def _pattern(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _require_pattern(value)


class ProjectsSection(StrictModel):
    pages: StrictInt = 20
    card_rows: StrictInt = 8


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
        if "daily_notes" in names and tables.daily_notes is None:
            raise ValueError("daily_notes is listed in sections but [section.daily_notes] is missing")
        if "daily" in names:
            if tables.daily is None:
                raise ValueError("daily is listed in sections but [section.daily] is missing")
            if tables.daily.left is None or tables.daily.right is None:
                raise ValueError("section.daily must have both left and right tracks")
        if "projects" in names and tables.projects is None:
            tables.projects = ProjectsSection()
        return self


def load_device_profile(path: Path) -> DeviceProfile:
    with path.open("rb") as f:
        return DeviceProfile.model_validate(tomllib.load(f))
