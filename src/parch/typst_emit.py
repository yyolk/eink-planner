"""typst_emit — join a t-string as raw Typst."""

from __future__ import annotations

from string.templatelib import Interpolation, Template


def typst_emit(template: Template) -> str:
    """Walk a t-string; literals pass through and interpolations use ``str(value)``."""
    parts: list[str] = []
    for item in template:
        match item:
            case str():
                parts.append(item)
            case Interpolation(value=value, format_spec=""):
                parts.append(str(value))
            case Interpolation(format_spec=spec):
                raise ValueError(f"typst_emit does not support format_spec={spec!r}")
    return "".join(parts)
