"""Raw Typst about page (no MOS chrome). Back of the notebook, not a build log."""

from __future__ import annotations

import re
from typing import Any

from parch import __version__
from parch.config import StrictDict, _to_plain
from parch.i18n import I18n
from parch.mos.configurator import Configurator
from parch.mos.contents_mark import body_size_token, heading_height_token, trail_heading
from parch.compose.page_data import HeadingMark, PageData
from parch.sections.annual import Annual

DEFAULT_TITLE = "About this notebook"

# Human names for shipped device slugs. Do not invent a device TOML field.
_DEVICE_NAMES = {
    "supernote-nomad": "SuperNote Nomad",
    "supernote-nomad-mos-right": "SuperNote Nomad",
    "kindle-scribe": "Kindle Scribe",
    "kindle-scribe-mos-right": "Kindle Scribe",
    "158x210-mos-left": "158 × 210",
    "158x210-mos-left-lined": "158 × 210",
    "158x210-mos-right": "158 × 210",
    "158x210-mos-right-lined": "158 × 210",
}

_TABLE_HEADER = re.compile(r"(?m)^[ \t]*\[(\[?)([^\]]+)\](\]?)[ \t]*\r?\n")
_BARE_KEY = r"[A-Za-z0-9_-]+"
_QUOTED_KEY = r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''
_KEY = rf"(?:{_BARE_KEY}|{_QUOTED_KEY})"
_KEY_LINE = re.compile(rf"(?m)^[ \t]*{_KEY}(?:[ \t]*\.[ \t]*{_KEY})*[ \t]*=")


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("#", "\\#")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


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


def drop_empty_tables(text: str) -> str:
    """Drop TOML tables that have no key/value pairs (comments/blank only)."""
    if not text:
        return ""
    matches = list(_TABLE_HEADER.finditer(text))
    if not matches:
        return text
    parts: list[str] = []
    prefix = text[: matches[0].start()]
    if prefix.strip():
        parts.append(prefix.rstrip() + "\n")
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]
        body = block[match.end() - start :]
        if _KEY_LINE.search(body):
            parts.append(block.rstrip() + "\n")
    return "".join(parts).rstrip() + ("\n" if parts else "")


def _human_device(slug: str) -> str:
    if not slug:
        return ""
    if slug in _DEVICE_NAMES:
        return _DEVICE_NAMES[slug]
    return slug.replace("-", " ").replace("_", " ").strip()


# Command / SHA values: Typst raw() (mono) with wrap opportunities. Do not shrink.
_MONO_HELPER = """#let colo-mono(s) = {
  show raw: it => {
    set text(font: "DejaVu Sans Mono")
    set par(justify: false)
    it.text.clusters().join[\\u{200B}]
  }
  raw(s)
}
"""


def _mono_cell(value: str) -> str:
    return f"colo-mono({typst_string(value)})"


class Colophon:
    ID = "colophon"

    def __init__(
        self,
        section_name: str,
        i18n: I18n,
        configurator: Configurator,
        title: str | None = None,
        dump: bool | None = None,
        command: bool | None = None,
        sha: bool | None = None,
    ) -> None:
        self.section_name = section_name
        self.configurator = configurator
        self.title = title or DEFAULT_TITLE
        self.dump = bool(dump)
        self.command = bool(command)
        self.sha = bool(sha)

    def register(self, manifest) -> None:
        if manifest is not None:
            manifest.register_source(self.ID)

    def pages(self, manifest) -> list[PageData]:
        return [PageData(raw_typst=True, content=self._content(manifest))]

    def _heading(self, manifest) -> str:
        """FOLLOW seat: five-bar then the name at 0.5em, own hit."""
        title = _escape(self.title)
        return trail_heading(
            manifest,
            heading_height_token(self.configurator),
            f'text(size: h1, weight: "bold")[{title} <colophon>]',
            body_size_token(self.configurator),
            direction="rtl",
            edge=HeadingMark.FOLLOW,
        )

    def _content(self, manifest=None) -> str:
        device = _escape(self._device_label())
        year_cell = self._year_cell(manifest)
        version = _escape(__version__)
        dumped = drop_empty_tables(self._config_text()) if self.dump else ""
        parts: list[str] = []
        titled = self._heading(manifest)
        if dumped.strip():
            # Page setup first so Typst does not break between the list and the dump.
            parts.append(self._dump_pagination(manifest))
        if self.command or self.sha:
            parts.append(_MONO_HELPER)
        parts.append(self._facts_block(titled, device, year_cell, version))
        if dumped.strip():
            parts.append("#v(1em)")
            parts.append(f"#raw(block: true, {typst_string(dumped)})")
            parts.append(f"#[] <{self._dump_end_label()}>")
        return "\n".join(parts)

    def _enabled_width_labels(self) -> list[str]:
        labels = ["Version"]
        if self.command:
            labels.append("Command")
        if self.sha:
            labels.append("SHA-256")
        return labels

    def _label_column(self) -> str:
        if self.command or self.sha:
            return "colo-label-width"
        return 'measure(text(weight: "bold")[Version]).width'

    def _label_width_let(self) -> str | None:
        labels = self._enabled_width_labels()
        if len(labels) == 1:
            return None
        measures = ",\n      ".join(
            f'measure(text(weight: "bold")[{label}]).width' for label in labels
        )
        return (
            "    let colo-label-width = calc.max(\n"
            f"      {measures},\n"
            "    )"
        )

    def _facts_block(self, titled: str, device: str, year_cell: str, version: str) -> str:
        rows = [
            f"      [*Device*], [{device}],",
            f"      [*Year*], {year_cell},",
            f"      [*Version*], [{version}],",
        ]
        if self.command:
            rows.append(f"      [*Command*], {_mono_cell(self._prov_field('command'))},")
        if self.sha:
            rows.append(f"      [*SHA-256*], {_mono_cell(self._prov_field('config_sha256'))},")
        grid = [
            f"    columns: ({self._label_column()}, 1fr),",
            "    column-gutter: regular_column_gutter,",
            "    rows: regular_height,",
            "    align: horizon,",
            *rows,
        ]
        inner = [
            "  #set par(spacing: 0em)",
            f"  #{titled}",
            "  #v(1em)",
        ]
        label_let = self._label_width_let()
        if label_let:
            inner.append("  #context {")
            inner.append(label_let)
            inner.append("    grid(")
            inner.extend(grid)
            inner.append("    )")
            inner.append("  }")
        else:
            inner.append("  #context grid(")
            inner.extend(grid)
            inner.append("  )")
        return "#block[\n" + "\n".join(inner) + "\n]"

    def _device_slug(self) -> str:
        raw = self._lookup("device")
        return str(raw) if raw else ""

    def _device_label(self) -> str:
        return _human_device(self._device_slug())

    def _year(self) -> int | None:
        cfg = self.configurator
        if cfg is None:
            return None
        if hasattr(cfg, "start_date"):
            try:
                return int(cfg.start_date().year)
            except Exception:
                pass
        raw = self._lookup("planner", "params", "start_date")
        if raw is None:
            return None
        try:
            return int(str(raw)[:4])
        except (TypeError, ValueError):
            return None

    def _year_cell(self, manifest) -> str:
        year = self._year()
        text = str(year) if year is not None else ""
        if manifest is not None and hasattr(manifest, "link_or_content") and text:
            return manifest.link_or_content(Annual.ID, text)
        return f"[{text}]"

    def _lookup(self, *path: str) -> Any:
        cfg = self.configurator
        if cfg is None:
            return None
        if hasattr(cfg, "dig"):
            return cfg.dig(*path)
        if hasattr(cfg, "dto") and hasattr(cfg.dto, "dig"):
            return cfg.dto.dig(*path)
        return None

    def _prov_field(self, key: str) -> str:
        raw = self._provenance().get(key)
        if raw is None:
            return ""
        return str(raw)

    def _config_text(self) -> str:
        prov = self._provenance()
        raw = prov.get("config_text")
        return str(raw) if raw else ""

    def _dump_uid(self) -> str:
        return str(id(self))

    def _dump_state_name(self) -> str:
        return f"colophon-start-{self._dump_uid()}"

    def _dump_end_label(self) -> str:
        return f"colophon-end-{self._dump_uid()}"

    def _dump_pagination(self, manifest) -> str:
        # Header is empty on the first dump page (body already has the heading)
        # and after this instance's end label so later MOS pages stay put.
        # Unique state/label per instance so two dump colophons do not share
        # start/end. Continuation uses the same FOLLOW seat as page 1.
        state_name = self._dump_state_name()
        end_label = self._dump_end_label()
        heading = self._heading(manifest)
        return f"""#context {{ state("{state_name}", 0).update(here().page()) }}
#set page(header: context {{
  let start-page = state("{state_name}", 0).final()
  let cur = here().page()
  let hits = query(<{end_label}>)
  let last = if hits.len() > 0 {{ hits.first().location().page() }} else {{ cur }}
  if last > start-page and cur > start-page and cur <= last {{
    {heading}
  }}
}})"""

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

