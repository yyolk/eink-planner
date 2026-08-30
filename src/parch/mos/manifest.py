from typing import Any

__all__ = ["Manifest"]


def __getattr__(name: str) -> Any:
    if name == "Manifest":
        from parch.compose.manifest import Manifest

        return Manifest
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
