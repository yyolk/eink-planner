"""Typed access to the planner YAML (port of LYP::Planners::MOS::Configurator)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from parch import ConfigError
from parch.calendar.day import WEEKDAYS, Day, normalize_weekday
from parch.config import StrictDict


class Configurator:
    ALLOWED_WEEKDAYS = WEEKDAYS

    def __init__(self, dto: StrictDict | dict[str, Any]) -> None:
        self.dto = dto if isinstance(dto, StrictDict) else StrictDict(dto)

    def debug(self) -> bool:
        return bool(self.dto.get("debug", False))

    def enabled_sections(self) -> list[Any]:
        sections = self.dto.dig_bang("planner", "sections")
        if sections is None or sections == []:
            raise ConfigError("No `planner.sections` found")
        enabled = []
        for section in sections:
            flag = section.get("enabled") if isinstance(section, StrictDict) else section.get("enabled")
            if flag:
                enabled.append(section)
        if not enabled:
            raise ConfigError("No enabled planner sections")
        return enabled

    def weekday_start(self) -> str:
        start = self.dto.dig_bang("planner", "params", "weekday_start")
        if start is None or start == "":
            raise ConfigError("No `planner.params.weekday_start` found")
        try:
            return normalize_weekday(str(start))
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc

    def start_date(self) -> Day:
        try:
            raw = self.dto.dig_bang("planner", "params", "start_date")
            return Day(weekday_start=self.weekday_start(), day=_parse_date(raw))
        except ConfigError:
            raise
        except Exception as exc:
            raise ConfigError(f"planner.params.start_date: invalid: {exc}") from exc

    def end_date(self) -> Day:
        try:
            raw = self.dto.dig_bang("planner", "params", "end_date")
            return Day(weekday_start=self.weekday_start(), day=_parse_date(raw))
        except ConfigError:
            raise
        except Exception as exc:
            raise ConfigError(f"planner.params.end_date: invalid: {exc}") from exc

    def dig_bang(self, *path: Any) -> Any:
        return self.dto.dig_bang(*path)

    def dig(self, *path: Any) -> Any:
        return self.dto.dig(*path)


def _parse_date(raw: Any) -> date:
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    return date.fromisoformat(str(raw))
