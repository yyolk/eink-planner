"""Pydantic models and tomllib loaders for device/locale TOML configs.

TOML keys use underscores; hyphens are OK in filenames only.
"""

from eink_planner.models.base import StrictModel, format_validation_error
from eink_planner.models.device import (
    DeviceProfile,
    KNOWN_SECTIONS,
    load_device_profile,
)
from eink_planner.models.locale import Locale, load_locale

__all__ = [
    "DeviceProfile",
    "KNOWN_SECTIONS",
    "Locale",
    "StrictModel",
    "format_validation_error",
    "load_device_profile",
    "load_locale",
]
