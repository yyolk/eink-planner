"""parch: Python port of kudrykv/LYP yearly e-ink planner."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("parch")
except PackageNotFoundError:
    __version__ = "unknown"


class Error(Exception):
    """Base package error."""


class InternalError(Error):
    """Programming / invariant error."""


class ConfigError(Error):
    """Invalid or incomplete planner configuration."""
