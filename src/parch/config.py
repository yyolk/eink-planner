"""Config loading (TOML device profiles) and strict nested-dict access."""

from pathlib import Path
from typing import Any

from parch import ConfigError


def _as_key(key: Any) -> str:
    return key if isinstance(key, str) else str(key)


class StrictDict:
    """Dict wrapper that raises ConfigError with a dotted path on missing keys."""

    def __init__(self, data: dict[str, Any] | None = None, path: str = "") -> None:
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ConfigError(f"{path or '<root>'}: expected mapping, got {type(data).__name__}")
        self._data = data
        self._path = path

    def _join(self, key: Any) -> str:
        name = _as_key(key)
        return f"{self._path}.{name}" if self._path else name

    def _wrap(self, value: Any, path: str) -> Any:
        if isinstance(value, StrictDict):
            return value
        if isinstance(value, dict):
            return StrictDict(value, path)
        if isinstance(value, list):
            return [
                self._wrap(item, f"{path}[{i}]") if isinstance(item, (dict, list)) else item
                for i, item in enumerate(value)
            ]
        return value

    def __contains__(self, key: object) -> bool:
        return _as_key(key) in self._data

    def __getitem__(self, key: Any) -> Any:
        name = _as_key(key)
        if name not in self._data:
            raise ConfigError(f"missing key: {self._join(name)}")
        return self._wrap(self._data[name], self._join(name))

    def get(self, key: Any, default: Any = None) -> Any:
        name = _as_key(key)
        if name not in self._data:
            return default
        return self._wrap(self._data[name], self._join(name))

    def dig(self, *path: Any) -> Any:
        current: Any = self._data
        built = self._path
        for key in path:
            name = _as_key(key)
            built = f"{built}.{name}" if built else name
            if not isinstance(current, dict) or name not in current:
                return None
            current = current[name]
        return self._wrap(current, built)

    def dig_bang(self, *path: Any) -> Any:
        """Strict nested lookup (Ruby ``dig!``). Missing keys raise ConfigError."""
        current: Any = self
        for key in path:
            if isinstance(current, StrictDict):
                current = current[key]
            elif isinstance(current, dict):
                name = _as_key(key)
                if name not in current:
                    raise ConfigError(f"missing key: {self._join(name) if not self._path else self._path + '.' + name}")
                current = current[name]
            else:
                raise ConfigError(f"missing key: {self._join(key)}")
        return current

    # Ruby-style alias used throughout the port
    def __getattr__(self, name: str) -> Any:
        if name == "dig!":
            return self.dig_bang
        raise AttributeError(name)

    def keys(self):
        return self._data.keys()

    def items(self):
        for key, value in self._data.items():
            yield key, self._wrap(value, self._join(key))

    def to_plain(self) -> dict[str, Any]:
        return {k: _to_plain(v) for k, v in self._data.items()}

    def __repr__(self) -> str:
        return f"StrictDict({self._data!r}, path={self._path!r})"


def _to_plain(value: Any) -> Any:
    if isinstance(value, StrictDict):
        return value.to_plain()
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    return value


def load(path: str | Path) -> StrictDict:
    """Load a planner device profile. Only ``.toml`` is accepted."""
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix in {".yaml", ".yml", ".kdl"}:
        raise ConfigError(
            f"{source}: leftover {suffix} is not accepted; device profiles must be TOML (locales too)"
        )
    if suffix == ".toml":
        from parch.toml_config import load_toml

        return load_toml(source)
    raise ConfigError(f"{source}: unsupported config suffix {suffix!r} (use .toml)")
