"""Device profile models. TOML keys use underscores; hyphens are OK in filenames only."""

# Locked scale + config ownership (Gridwright). Do not reinterpret.
#
# Pin: reverse_months_quarters stays MOS-strip overlay — not dead TOML, not a
# well-track knob. It packs the rotated strip (1fr/3fr quarters|months,
# cols.reverse() + item order). True on every shipped device independent of
# side, so do not fold it into side this slice. reverse_months_quarters_items
# stays Python item order. Well helpers still take side only. Python still
# data + side. Do not derive reverse_months_quarters from side.
#
# Device .typ (physical, not per-section): page-width / page-height,
# toolbar-clearance, writing-clearance, page-margin(side), and mos-width.
# MOS is not toolbar — Nomad 8mm vs Scribe 10mm. Do not alias mos-width
# to toolbar-clearance.
#
# House: tracks from side only (mos_frame, daily_well 3/5, quarter_well 2/3,
# week rail, trail_heading ltr). No new length knobs.
#
# Preamble book: regular_stroke / thick_stroke, regular_height,
# regular_column_gutter, type (size, h1), link_padding, heading-height, MOS
# column/row gutter. week_matrix header-stroke lives here so week_cell can
# read .thickness.
#
# Section overlay (default or sealed): monthly daily_cell_height, notes
# title_height, paper pattern, week_placement: none only, counts/pages/hours,
# week_label_rotation, little-cal inset, cover type. Not tracks.
#
# Dead TOML: [style.margin], [device] width/height (keep name, ppi if
# colophon needs them), months_column, week_placement left|right,
# section.daily.columns 3fr/5fr, side_menu_width. Do not drop
# reverse_months_quarters.
# --hand / later --paper stay overlays until parch new writes the file.

import tomllib
from pathlib import Path
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    Field,
    PrivateAttr,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

from parch.models.base import StrictModel

_PATTERNS = frozenset({"dotted", "lined"})

# Physical tokens copied from device .typ. Not TOML. MOS is not toolbar.
DEVICE_SCALE = {
    "supernote-nomad": {
        "width": "118.87mm",
        "height": "158.5mm",
        "toolbar_clearance": "8mm",
        "writing_clearance": "4mm",
        "mos_width": "8mm",
    },
    "kindle-scribe": {
        "width": "157.48mm",
        "height": "209.97mm",
        "toolbar_clearance": "5mm",
        "writing_clearance": "5mm",
        "mos_width": "10mm",
    },
    "158x210": {
        "width": "158mm",
        "height": "210mm",
        "toolbar_clearance": "5mm",
        "writing_clearance": "5mm",
        "mos_width": "10mm",
    },
}


def device_scale(name: str) -> dict[str, str]:
    """Physical-device tokens for *name* (prefix match, including -lined)."""
    lowered = name.strip().lower()
    for prefix, scale in DEVICE_SCALE.items():
        if lowered == prefix or lowered.startswith(prefix + "-"):
            return scale
    raise ValueError(
        "unknown physical device; expected supernote-nomad, kindle-scribe, or 158x210"
    )


def device_page_margin(scale: dict[str, str]) -> dict[str, str]:
    """MOS-left page-margin copy. page-margin(side) owns the writing-edge flip."""
    return {
        "top": scale["toolbar_clearance"],
        "bottom": "0mm",
        "left": "0mm",
        "right": scale["writing_clearance"],
    }


def _week_placement_none(value: Any) -> str:
    text = str(value).lstrip(":").lower()
    if text == "none":
        return text
    raise ValueError("week_placement: none only")


WeekPlacementNone = Annotated[str, AfterValidator(_week_placement_none)]


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


class Gutter(StrictModel):
    column: str
    row: str | None = None  # optional; adapter ignores it


class Heading(StrictModel):
    height: str | None = None
    align: str | None = None


class LittleCalendar(StrictModel):
    week_placement: WeekPlacementNone | None = None
    inset: str | None = None
    show_month_name: StrictBool | None = None


class Style(StrictModel):
    stroke: Stroke
    type: TypeStyle
    gutter: Gutter
    regular_height: str | None = None
    link_padding: str | None = None
    scratch_pad: ScratchPad = None
    heading: Heading | None = None
    little_calendar: LittleCalendar | None = None


class Mos(StrictModel):
    side_menu: str
    # MOS-strip overlay. True on every shipped device; not derived from side.
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


class IndexSection(StrictModel):
    """Optional Contents page. No required fields."""


class AnnualSection(StrictModel):
    row_gutter: str | None = None
    show_month_name: StrictBool | None = None
    little_calendar: LittleCalendar | None = None


class QuarterlySection(StrictModel):
    pattern: OptionalPattern = None
    show_month_name: StrictBool | None = None
    little_calendar: LittleCalendar | None = None


class MonthlySection(StrictModel):
    week_placement: WeekPlacementNone | None = None
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
    item_spacing: str
    left: DailyTrack | None = None
    right: DailyTrack | None = None


class DailyNotesSection(StrictModel):
    pages: StrictInt
    pattern: OptionalPattern = None


class ProjectsSection(StrictModel):
    pages: StrictInt = 16
    card_rows: StrictInt = 5


class MeetingsSection(StrictModel):
    index_pages: StrictInt = 1

    @model_validator(mode="after")
    def _index_pages_positive(self) -> MeetingsSection:
        if self.index_pages < 1:
            raise ValueError("index_pages must be at least 1")
        return self


class ReviewSection(StrictModel):
    weeks_per_page: StrictInt = 13
    pattern: OptionalPattern = "lined"

    @model_validator(mode="after")
    def _weeks_per_page_positive(self) -> ReviewSection:
        if self.weeks_per_page < 1:
            raise ValueError("weeks_per_page must be at least 1")
        return self


class TasksSection(StrictModel):
    weeks_per_page: StrictInt = 13

    @model_validator(mode="after")
    def _weeks_per_page_positive(self) -> TasksSection:
        if self.weeks_per_page < 1:
            raise ValueError("weeks_per_page must be at least 1")
        return self


class HabitsSection(StrictModel):
    habit_columns: StrictInt = 4
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
    dump: StrictBool | None = None
    command: StrictBool | None = None
    sha: StrictBool | None = None


class SectionTables(StrictModel):
    cover: CoverSection | None = None
    index: IndexSection | None = None
    annual: AnnualSection | None = None
    quarterly: QuarterlySection | None = None
    monthly: MonthlySection | None = None
    weekly: WeeklySection | None = None
    daily: DailySection | None = None
    daily_notes: DailyNotesSection | None = None
    projects: ProjectsSection | None = None
    meetings: MeetingsSection | None = None
    habits: HabitsSection | None = None
    review: ReviewSection | None = None
    tasks: TasksSection | None = None
    colophon: ColophonSection | None = None

    @field_validator("colophon", mode="before")
    @classmethod
    def _colophon_table(cls, value: Any) -> Any:
        if isinstance(value, list):
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
    mos: Mos
    sections: list[str]
    section: SectionTables = Field(default_factory=SectionTables)

    @model_validator(mode="before")
    @classmethod
    def _reject_debug(cls, data: Any) -> Any:
        if isinstance(data, dict) and "debug" in data:
            raise ValueError("debug does not belong in the config; use `parch press --debug`")
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
            if name in seen:
                raise ValueError(f"duplicate section: {name}")
            seen.add(name)
        return value

    @model_validator(mode="after")
    def _nested_section_rules(self) -> DeviceProfile:
        names = set(self.sections)
        tables = self.section
        if "cover" in names and tables.cover is None:
            raise ValueError("cover is listed in sections but [section.cover] is missing")
        if "index" in names and tables.index is None:
            tables.index = IndexSection()
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
        if "meetings" in names and tables.meetings is None:
            tables.meetings = MeetingsSection()
        if "habits" in names and tables.habits is None:
            tables.habits = HabitsSection()
        if "review" in names and tables.review is None:
            tables.review = ReviewSection()
        if "tasks" in names and tables.tasks is None:
            tables.tasks = TasksSection()
        return self


def load_device_profile(path: Path) -> DeviceProfile:
    with path.open("rb") as f:
        return DeviceProfile.model_validate(tomllib.load(f))
