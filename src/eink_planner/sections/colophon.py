"""Raw Typst about / provenance page (no MOS chrome). Wired through the MOS coordinator via PageData."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from eink_planner.config import StrictDict, _to_plain
from eink_planner.mos.page_data import PageData

DEFAULT_TITLE = "About this notebook"
_UNKNOWN = "unknown"
_ASSETS = Path(__file__).resolve().parent.parent / "assets"

# Used when the vendored files are absent from a slim wheel.
_TOML_SYNTAX_FALLBACK = '%YAML 1.2\n---\nname: TOML\nfile_extensions:\n  - toml\nscope: source.toml\ncontexts:\n  main:\n    - match: \'#.*\'\n      scope: comment.line.number-sign.toml\n    - match: \'"""\'\n      push: multiline_basic\n    - match: "\'\'\'"\n      push: multiline_literal\n    - match: \'"\'\n      push: string\n    - match: "\'"\n      push: literal\n    - match: \'\\b(?:true|false)\\b\'\n      scope: constant.language.toml\n    - match: \'-?(?:0x[0-9A-Fa-f_]+|0o[0-7_]+|0b[01_]+|\\d(?:_?\\d)*(?:\\.\\d(?:_?\\d)*)?(?:[eE][+-]?\\d+)?)\'\n      scope: constant.numeric.toml\n    - match: \'[\\[\\]{}.=,]\'\n      scope: punctuation.toml\n    - match: \'[A-Za-z_][A-Za-z0-9_-]*\'\n      scope: entity.name.tag.toml\n  string:\n    - meta_include_prototype: false\n    - meta_scope: string.quoted.double.toml\n    - match: \'\\\\.\'\n      scope: constant.character.escape.toml\n    - match: \'"\'\n      pop: true\n  literal:\n    - meta_include_prototype: false\n    - meta_scope: string.quoted.single.toml\n    - match: "\'"\n      pop: true\n  multiline_basic:\n    - meta_include_prototype: false\n    - meta_scope: string.quoted.double.toml\n    - match: \'\\\\.\'\n      scope: constant.character.escape.toml\n    - match: \'"""\'\n      pop: true\n  multiline_literal:\n    - meta_include_prototype: false\n    - meta_scope: string.quoted.single.toml\n    - match: "\'\'\'"\n      pop: true\n'
_EINK_THEME_FALLBACK = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0">\n<dict>\n  <key>name</key>\n  <string>E-ink luma color</string>\n  <key>settings</key>\n  <array>\n    <dict>\n      <key>settings</key>\n      <dict>\n        <key>background</key>\n        <string>#FFFFFF</string>\n        <key>foreground</key>\n        <string>#111111</string>\n      </dict>\n    </dict>\n    <dict>\n      <key>name</key>\n      <string>Comment</string>\n      <key>scope</key>\n      <string>comment</string>\n      <key>settings</key>\n      <dict>\n        <key>foreground</key>\n        <string>#8FA3B8</string>\n      </dict>\n    </dict>\n    <dict>\n      <key>name</key>\n      <string>Identifier</string>\n      <key>scope</key>\n      <string>entity.name</string>\n      <key>settings</key>\n      <dict>\n        <key>foreground</key>\n        <string>#0B2F6B</string>\n      </dict>\n    </dict>\n    <dict>\n      <key>name</key>\n      <string>String</string>\n      <key>scope</key>\n      <string>string</string>\n      <key>settings</key>\n      <dict>\n        <key>foreground</key>\n        <string>#1F7A3A</string>\n      </dict>\n    </dict>\n    <dict>\n      <key>name</key>\n      <string>Escape</string>\n      <key>scope</key>\n      <string>constant.character.escape</string>\n      <key>settings</key>\n      <dict>\n        <key>foreground</key>\n        <string>#C45C12</string>\n      </dict>\n    </dict>\n    <dict>\n      <key>name</key>\n      <string>Number</string>\n      <key>scope</key>\n      <string>constant.numeric</string>\n      <key>settings</key>\n      <dict>\n        <key>foreground</key>\n        <string>#E07A12</string>\n      </dict>\n    </dict>\n    <dict>\n      <key>name</key>\n      <string>Language constant</string>\n      <key>scope</key>\n      <string>constant.language</string>\n      <key>settings</key>\n      <dict>\n        <key>foreground</key>\n        <string>#8A2F98</string>\n      </dict>\n    </dict>\n    <dict>\n      <key>name</key>\n      <string>Punctuation</string>\n      <key>scope</key>\n      <string>punctuation</string>\n      <key>settings</key>\n      <dict>\n        <key>foreground</key>\n        <string>#6E6E6E</string>\n      </dict>\n    </dict>\n  </array>\n  <key>uuid</key>\n  <string>a1b2c3d4-e5f6-7890-abcd-ef1234567890</string>\n</dict>\n</plist>\n'


def _asset_text(name: str, fallback: str) -> str:
    path = _ASSETS / name
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return fallback
    return text if text.strip() else fallback


def toml_syntax_text() -> str:
    return _asset_text("toml.sublime-syntax", _TOML_SYNTAX_FALLBACK)


def eink_theme_text() -> str:
    return _asset_text("eink-luma.tmTheme", _EINK_THEME_FALLBACK)


class Colophon:
    def __init__(
        self,
        section_name: str,
        title: str | None = None,
        configurator: Any = None,
        highlight: bool = True,
        **_rest: Any,
    ) -> None:
        self.section_name = section_name
        self.title = title or DEFAULT_TITLE
        self.configurator = configurator
        self.highlight = highlight

    def register(self, _manifest) -> None:
        return None

    def pages(self, _manifest) -> list[PageData]:
        return [PageData(raw_typst=True, content=self._content())]

    def _content(self) -> str:
        prov = self._provenance()
        fields = [
            ("Command", _field(prov.get("command"))),
            ("Version", _field(prov.get("version"))),
            ("Git commit", _field(prov.get("git_sha"))),
            ("Config", _field(prov.get("config_path"))),
            ("SHA-256", _field(prov.get("config_sha256"))),
        ]
        rows = ",\n  ".join(
            f"[*{label}*], raw({typst_string(value)})" for label, value in fields
        )
        parts = [
            f"#text(size: h1, weight: \"bold\")[#raw({typst_string(self.title)})]",
            "#v(1em)",
            "#grid(",
            "  columns: (auto, 1fr),",
            "  column-gutter: 1em,",
            "  row-gutter: 0.6em,",
            f"  {rows},",
            ")",
        ]
        config_text = prov.get("config_text")
        if config_text:
            parts.append("#v(1em)")
            parts.append(self._config_raw(str(config_text)))
        return "\n".join(parts)

    def _config_raw(self, config_text: str) -> str:
        quoted = typst_string(config_text)
        if not self.highlight:
            return f"#raw(block: true, {quoted})"
        syntax = typst_string(toml_syntax_text())
        theme = typst_string(eink_theme_text())
        return (
            '#raw(block: true, lang: "toml", '
            f"syntaxes: bytes({syntax}), "
            f"theme: bytes({theme}), "
            f"{quoted})"
        )

    def _provenance(self) -> dict[str, Any]:
        cfg = self.configurator
        if cfg is None:
            return {}
        for path in (("planner", "params", "provenance"), ("_provenance",)):
            raw = cfg.dig(*path) if hasattr(cfg, "dig") else None
            if not raw:
                continue
            if isinstance(raw, StrictDict):
                return raw.to_plain()
            if isinstance(raw, dict):
                return _to_plain(raw)
        return {}


def typst_string(text: str) -> str:
    """Quote *text* as a Typst string literal for ``#raw(...)``."""
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _field(value: Any) -> str:
    if value is None or value == "":
        return _UNKNOWN
    return str(value)
