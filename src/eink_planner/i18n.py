"""Minimal YAML locale loader (same keys as LYP locales/en.yaml)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from eink_planner import ConfigError


class I18n:
    def __init__(self, data: dict[str, Any], locale: str = "en") -> None:
        if locale in data and isinstance(data[locale], dict):
            self._tree = data[locale]
        else:
            self._tree = data
        self.locale = locale

    def t(self, key: str) -> str:
        node: Any = self._tree
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                raise ConfigError(f"missing translation: {key}")
            node = node[part]
        if node is None:
            raise ConfigError(f"missing translation: {key}")
        return str(node)

    @classmethod
    def load(cls, locale_path: str | Path, locale: str = "en") -> I18n:
        path = Path(locale_path)
        if path.is_dir():
            candidate = path / f"{locale}.yaml"
            if not candidate.exists():
                candidate = path / f"{locale}.yml"
            path = candidate
        if not path.exists():
            raise ConfigError(f"locale file not found: {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ConfigError(f"{path}: locale root must be a mapping")
        return cls(data, locale=locale)

    @classmethod
    def load_default(cls, package_root: Path | None = None, locale: str = "en") -> I18n:
        if package_root is None:
            # src/eink_planner/i18n.py → repo root
            package_root = Path(__file__).resolve().parents[2]
        locales_dir = package_root / "locales"
        return cls.load(locales_dir, locale=locale)
