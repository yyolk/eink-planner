from datetime import date
from importlib.resources import files
from pathlib import Path
import tempfile

import pytest

from parch.calendar.day import Day
from parch.calendar.month import Month
from parch.calendar.quarter import Quarter
from parch.calendar.week import Week
from parch.config import StrictDict
from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.services.job_file import emit_job, spec_from_device

_JOB_DIR = Path(tempfile.mkdtemp(prefix="parch-jobs-"))


def base_config(stem: str, *, paper: str = "dotted") -> Path:
    """Materialize the default job for a device id. Lined is paper, not a device."""
    spec = spec_from_device(stem, paper=paper)
    suffix = "" if paper == "dotted" else f"-{paper}"
    path = _JOB_DIR / f"{spec.device_id}{suffix}.toml"
    path.write_text(emit_job(spec), encoding="utf-8")
    return path


def packaged_locale(locale: str = "en") -> Path:
    """Filesystem path to a packaged locale TOML."""
    resource = files("parch.data") / "locales" / f"{locale}.toml"
    if isinstance(resource, Path):
        return resource
    raise RuntimeError("packaged_locale is checkout-only")


def load_default(locale: str = "en") -> I18n:
    return I18n.load_default(locale)


def make_day(date_str: str, weekday_start: str = "monday") -> Day:
    return Day(day=date.fromisoformat(date_str), weekday_start=weekday_start)


def make_week(date_str: str, weekday_start: str = "monday") -> Week:
    return Week(weekday_start=weekday_start, day=make_day(date_str, weekday_start))


def make_month(yyyy_mm: str, weekday_start: str = "monday") -> Month:
    return Month(weekday_start=weekday_start, day=make_day(f"{yyyy_mm}-01", weekday_start))


def make_quarter(date_str: str, weekday_start: str = "monday") -> Quarter:
    return Quarter(weekday_start=weekday_start, day=make_day(date_str, weekday_start))


def make_configurator(
    start_date: str = "2026-01-01",
    end_date: str = "2026-12-31",
    weekday_start: str = "Monday",
    debug: bool = False,
) -> Configurator:
    return Configurator(
        StrictDict(
            {
                "debug": debug,
                "planner": {
                    "params": {
                        "start_date": start_date,
                        "end_date": end_date,
                        "weekday_start": weekday_start,
                    }
                },
            }
        )
    )


@pytest.fixture
def helpers():
    return {
        "make_day": make_day,
        "make_week": make_week,
        "make_month": make_month,
        "make_quarter": make_quarter,
        "make_configurator": make_configurator,
    }
