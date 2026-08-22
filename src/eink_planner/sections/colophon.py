"""Generic provenance / about page. Layout-agnostic raw Typst (no MOS chrome)."""

from __future__ import annotations

from typing import Any

from eink_planner.config import StrictDict, _to_plain
from eink_planner.mos.page_data import PageData

DEFAULT_TITLE = "About this notebook"
_UNKNOWN = "unknown"


class Colophon:
    def __init__(
        self,
        section_name: str,
        title: str | None = None,
        configurator: Any = None,
        **_rest: Any,
    ) -> None:
        self.section_name = section_name
        self.title = title or DEFAULT_TITLE
        self.configurator = configurator

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
            parts.append(f"#raw(block: true, {typst_string(str(config_text))})")
        return "\n".join(parts)

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
