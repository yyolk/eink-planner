"""Shared Pydantic base for TOML config models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, ValidationError


class StrictModel(BaseModel):
    """Reject unknown keys. TOML keys must match field names (underscores)."""

    model_config = ConfigDict(extra="forbid")


def format_validation_error(exc: ValidationError) -> str:
    """Turn the first Pydantic error into a short ConfigError message."""
    err = exc.errors()[0]
    loc = ".".join(str(part) for part in err["loc"])
    typ = err["type"]
    msg = err["msg"]
    if msg.lower().startswith("value error, "):
        msg = msg[13:]

    if typ == "extra_forbidden":
        return f"unknown key: {loc}" if loc else "unknown key"
    if typ == "missing":
        return f"missing key: {loc}" if loc else "missing key"
    if typ in {"int_type", "int_parsing"} or "integer" in msg.lower():
        return f"{loc}: expected integer" if loc else "expected integer"
    if typ in {"bool_type", "bool_parsing"} or "boolean" in msg.lower():
        return f"{loc}: expected boolean" if loc else "expected boolean"
    if loc:
        return f"{loc}: {msg}"
    return msg
