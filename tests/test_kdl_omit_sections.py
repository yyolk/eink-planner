"""Omit MOS sections from KDL and still compile a PDF.

Presence of a top-level ``section X { ... }`` node enables that section.
Dropping or commenting the node disables it. Generate must not crash;
Typst must write a PDF. Missing-label / missing-ref warnings that still
produce a PDF are recorded (implicit link graph) but are not failures.

Code-level implicit deps (Python already omits the ``padded_link`` when
the target is unregistered; the remaining text must still be valid Typst):

- annual: heading "Calendar" link (Navigation) — skipped if unregistered
- quarterly: side-menu quarter cells — text only if unregistered
- monthly: side-menu month cells — text only if unregistered
- weekly: daily / daily-notes titles and little-calendar / monthly week
  labels — content fallback if unregistered
- daily: little-calendar / monthly / weekly day cells — content fallback
- daily-notes: daily page "more notes" link — omitted if unregistered
- cover: nothing links to it (and the cover does not link to annual)

Hard dependency: at least one ``section`` node. Empty
``enabled_sections()`` raises ``ConfigError``.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.config import StrictDict, load
from eink_planner.i18n import I18n
from eink_planner.kdl_config import parse_kdl
from eink_planner.mos.configurator import Configurator
from eink_planner.services.compile import ensure_typst
from eink_planner.services.generate import Generate

REPO = Path(__file__).resolve().parents[1]
NOMAD = REPO / "configs/supernote-nomad.kdl"

SECTIONS = (
    "cover",
    "annual",
    "quarterly",
    "monthly",
    "weekly",
    "daily",
    "daily-notes",
    "projects",
)

# Typst 0.15: "label `<foo>` does not exist in the document"
_MISSING_LABEL = re.compile(
    r"(?:label|reference)\s+`?<([^>`]+)>`?|(?:unknown label)\s+`?<([^>`]+)>`?",
    re.IGNORECASE,
)
_PADDED_LINK = re.compile(r"padded_link\(<([^>]+)>")
_LABEL_DEF = re.compile(r"(?<!padded_link\()<([A-Za-z0-9._:-]+)>")


def _section_name(line: str) -> str | None:
    stripped = line.lstrip()
    if not stripped.startswith("section "):
        return None
    rest = stripped[len("section ") :].strip()
    name = rest.split("{", 1)[0].strip().split()[0] if rest else ""
    return name or None


def omit_kdl_sections(text: str, kinds: list[str] | tuple[str, ...]) -> str:
    """Drop whole ``section KIND { ... }`` nodes. ``daily`` does not eat ``daily-notes``."""
    want = set(kinds)
    out: list[str] = []
    skipping = False
    depth = 0
    for line in text.splitlines(keepends=True):
        if not skipping:
            name = _section_name(line)
            if name in want:
                skipping = True
                depth = line.count("{") - line.count("}")
                if depth <= 0:
                    skipping = False
                continue
        if skipping:
            depth += line.count("{") - line.count("}")
            if depth <= 0:
                skipping = False
            continue
        out.append(line)
    return "".join(out)


def _short_january(dto: StrictDict) -> StrictDict:
    data = dto.to_plain()
    data["planner"]["params"]["start_date"] = "2026-01-01"
    data["planner"]["params"]["end_date"] = "2026-01-14"
    return StrictDict(data)


def _dto_omitting(*kinds: str, short: bool = True) -> StrictDict:
    text = omit_kdl_sections(NOMAD.read_text(encoding="utf-8"), kinds)
    dto = parse_kdl(text, source="omit.kdl")
    return _short_january(dto) if short else dto


def _enabled_names(dto: StrictDict) -> list[str]:
    return [section["name"] for section in Configurator(dto).enabled_sections()]


def _generate(dto: StrictDict) -> str:
    return Generate(i18n=I18n.load_default(REPO, "en")).generate(dto)


def classify_label(label: str) -> str:
    if label == "annual":
        return "annual"
    if label.startswith("quarter-"):
        return "quarterly"
    if label.startswith("month-"):
        return "monthly"
    if re.fullmatch(r"\d{4}W\d{2}", label):
        return "weekly"
    if label.startswith("daily-note-"):
        return "daily-notes"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", label):
        return "daily"
    return "other"


def missing_ref_kinds(stderr: str) -> frozenset[str]:
    kinds: set[str] = set()
    for line in stderr.splitlines():
        match = _MISSING_LABEL.search(line)
        if not match:
            continue
        label = match.group(1) or match.group(2)
        if label:
            kinds.add(classify_label(label))
    return frozenset(kinds)


def compile_pdf(typst_src: str, workdir: Path) -> tuple[Path, str]:
    """Compile Typst. A PDF on disk is success; stderr warnings are returned."""
    workdir.mkdir(parents=True, exist_ok=True)
    src = workdir / "index.typst"
    pdf = workdir / "index.pdf"
    src.write_text(typst_src, encoding="utf-8")
    typst = ensure_typst(tools_dir=REPO / ".tools")
    result = subprocess.run(
        [str(typst), "compile", str(src), str(pdf)],
        capture_output=True,
        text=True,
    )
    return pdf, (result.stderr or "") + (result.stdout or "")


def _assert_pdf(typst_src: str, workdir: Path) -> frozenset[str]:
    pdf, stderr = compile_pdf(typst_src, workdir)
    assert pdf.is_file() and pdf.stat().st_size > 0, (
        f"typst did not write a PDF\n{stderr}"
    )
    return missing_ref_kinds(stderr)


def test_omit_daily_does_not_drop_daily_notes():
    text = omit_kdl_sections(NOMAD.read_text(encoding="utf-8"), ["daily"])
    dto = parse_kdl(text, source="omit-daily.kdl")
    names = _enabled_names(dto)
    assert "daily" not in names
    assert "daily_notes" in names


@pytest.mark.parametrize("kind", SECTIONS)
def test_omit_one_section_compiles_pdf(kind, tmp_path):
    dto = _dto_omitting(kind)
    names = _enabled_names(dto)
    kdl_to_name = {s: s.replace("-", "_") for s in SECTIONS}
    assert kdl_to_name[kind] not in names
    typst_src = _generate(dto)
    links = set(_PADDED_LINK.findall(typst_src))
    labels = set(_LABEL_DEF.findall(typst_src))
    assert links <= labels
    kinds = _assert_pdf(typst_src, tmp_path / kind)
    # Python already drops padded_link to unregistered pages, so Typst
    # missing-ref kinds stay empty. Pin that so new unguarded links show up.
    assert kinds == frozenset()


@pytest.mark.parametrize(
    "omit,remain",
    [
        (("annual", "quarterly"), ("cover", "monthly", "weekly", "daily", "daily_notes", "projects")),
        (("weekly",), ("cover", "annual", "quarterly", "monthly", "daily", "daily_notes", "projects")),
        (("monthly",), ("cover", "annual", "quarterly", "weekly", "daily", "daily_notes", "projects")),
        (("daily",), ("cover", "annual", "quarterly", "monthly", "weekly", "daily_notes", "projects")),
        (("daily-notes",), ("cover", "annual", "quarterly", "monthly", "weekly", "daily", "projects")),
        (
            ("cover", "annual", "quarterly", "monthly", "weekly", "daily-notes"),
            ("daily", "projects"),
        ),
        (
            ("annual", "quarterly", "monthly", "weekly", "daily", "daily-notes"),
            ("cover", "projects"),
        ),
    ],
    ids=[
        "no-annual-quarterly",
        "no-weekly",
        "no-monthly",
        "notes-without-daily",
        "no-daily-notes",
        "daily-only",
        "cover-only",
    ],
)
def test_omit_combinations_compile_pdf(omit, remain, tmp_path):
    dto = _dto_omitting(*omit)
    assert tuple(_enabled_names(dto)) == remain
    typst_src = _generate(dto)
    links = set(_PADDED_LINK.findall(typst_src))
    labels = set(_LABEL_DEF.findall(typst_src))
    assert links <= labels
    kinds = _assert_pdf(typst_src, tmp_path)
    assert kinds == frozenset()


def test_empty_sections_raises_config_error():
    text = omit_kdl_sections(NOMAD.read_text(encoding="utf-8"), SECTIONS)
    dto = parse_kdl(text, source="empty.kdl")
    assert dto["planner"]["sections"] == []
    with pytest.raises(ConfigError, match=r"planner\.sections"):
        Configurator(dto).enabled_sections()


def test_all_disabled_sections_raises_config_error():
    data = load(NOMAD).to_plain()
    for section in data["planner"]["sections"]:
        section["enabled"] = False
    with pytest.raises(ConfigError, match="No enabled planner sections"):
        Configurator(StrictDict(data)).enabled_sections()


def test_commented_cover_still_generates():
    text = NOMAD.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    out = []
    commenting = False
    depth = 0
    for line in lines:
        if not commenting and _section_name(line) == "cover":
            commenting = True
        if commenting:
            out.append("// " + line if not line.startswith("//") else line)
            depth += line.count("{") - line.count("}")
            if depth <= 0:
                commenting = False
            continue
        out.append(line)
    dto = _short_january(parse_kdl("".join(out), source="commented-cover.kdl"))
    assert "cover" not in _enabled_names(dto)
    typst_src = _generate(dto)
    assert typst_src


def test_label_def_ignores_padded_link_targets():
    only_link = "padded_link(<2026-01-01>)[1]"
    assert _LABEL_DEF.findall(only_link) == []
    defined = "text(size: h1)[1 <2026-01-01>]"
    assert _LABEL_DEF.findall(defined) == ["2026-01-01"]
    mixed = "padded_link(<2026-01-01>)[1]\n" + defined
    assert _LABEL_DEF.findall(mixed) == ["2026-01-01"]

