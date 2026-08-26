"""Locale loader: TOML only.

Lookup keys follow the locale table shape (``week_name``, ``quarter.short``,
``weekday.letter.monday``). Nested lookups stay dotted.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from parch import ConfigError
from parch.models import format_validation_error, load_locale


class I18n:
    def __init__(self, data: dict[str, Any], locale: str = "en") -> None:
        if locale in data and isinstance(data[locale], dict):
            self._tree = data[locale]
        else:
            self._tree = data
        language = self._tree.get("language")
        self.locale = language if isinstance(language, str) else locale

    def t(self, key: str) -> str:
        node: Any = self._tree
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                raise ConfigError(f"missing translation: {key}")
            node = node[part]
        if node is None or isinstance(node, dict):
            raise ConfigError(f"missing translation: {key}")
        return str(node)

    @classmethod
    def load(cls, locale_path: str | Path, locale: str = "en") -> I18n:
        path = Path(locale_path)
        if path.is_dir():
            path = _resolve_locale_file(path, locale)
        if not path.exists():
            raise ConfigError(f"locale file not found: {path}")
        suffix = path.suffix.lower()
        if suffix in {".yaml", ".yml", ".kdl"}:
            raise ConfigError(f"{path}: locales must be TOML (device profiles too)")
        if suffix == ".toml":
            return cls(_load_validated(path), locale=locale)
        raise ConfigError(f"{path}: unsupported locale suffix {suffix!r} (use .toml)")

    @classmethod
    def load_default(cls, package_root: Path | None = None, locale: str = "en") -> I18n:
        if package_root is None:
            # src/parch/i18n.py → repo root
            package_root = Path(__file__).resolve().parents[2]
        return cls.load(package_root / "locales", locale=locale)


def _resolve_locale_file(directory: Path, locale: str) -> Path:
    if (
        not locale
        or locale in {".", ".."}
        or "/" in locale
        or "\\" in locale
        or Path(locale).name != locale
    ):
        raise ConfigError(f"locale: expected a code like en, not {locale!r}")
    return directory / f"{locale}.toml"


def _load_validated(path: Path) -> dict[str, Any]:
    try:
        model = load_locale(path)
    except OSError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    except ValidationError as exc:
        raise ConfigError(f"{path}: {format_validation_error(exc)}") from exc
    return model.model_dump()
