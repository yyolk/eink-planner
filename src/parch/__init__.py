"""parch: Python port of kudrykv/LYP yearly e-ink planner."""

from __future__ import annotations

__version__ = "0.1.1"


class Error(Exception):
    """Base package error."""


class InternalError(Error):
    """Programming / invariant error."""


class ConfigError(Error):
    """Invalid or incomplete planner configuration."""
