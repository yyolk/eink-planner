"""Locale loader: KDL only.

Lookup keys follow the KDL shape (``week-name``, ``quarter.short``,
``weekday.letter.monday``), not the old YAML snake_case names.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import ckdl

from eink_planner import ConfigError


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
        if suffix in {".yaml", ".yml"}:
            raise ConfigError(f"{path}: locales must be KDL (device profiles too)")
        if suffix == ".kdl":
            return cls(_load_kdl(path), locale=locale)
        raise ConfigError(f"{path}: unsupported locale suffix {suffix!r} (use .kdl)")

    @classmethod
    def load_default(cls, package_root: Path | None = None, locale: str = "en") -> I18n:
        if package_root is None:
            # src/eink_planner/i18n.py → repo root
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
    return directory / f"{locale}.kdl"


def _plain(value: Any) -> Any:
    if isinstance(value, ckdl.Value):
        if value.type_annotation:
            return f"{value.value}{value.type_annotation}"
        return value.value
    return value


def _load_kdl(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    try:
        doc = ckdl.parse(text, version=2)
    except ckdl.ParseError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    tree = _kdl_nodes_to_tree(list(doc.nodes), source=str(path))
    if "language" not in tree:
        raise ConfigError(f"{path}: missing language")
    return tree


def _kdl_nodes_to_tree(nodes: list[Any], source: str, path: str = "") -> dict[str, Any]:
    tree: dict[str, Any] = {}
    for node in nodes:
        loc = f"{path}.{node.name}" if path else node.name
        if node.name in tree:
            raise ConfigError(f"{source}: duplicate node: {loc}")
        if node.children:
            if node.args:
                raise ConfigError(f"{source}: {loc}: expected children or a string, not both")
            tree[node.name] = _kdl_nodes_to_tree(list(node.children), source, loc)
            continue
        if not node.args:
            raise ConfigError(f"{source}: {loc}: missing argument")
        if len(node.args) != 1:
            raise ConfigError(f"{source}: {loc}: expected one argument")
        tree[node.name] = _plain(node.args[0])
    return tree
