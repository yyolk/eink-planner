"""Omit MOS sections from TOML and still compile a PDF.

Presence of a name in the top-level ``sections = [...]`` list enables that
section. Commenting the name out disables it. Generate must not crash;
Typst must write a PDF.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from eink_planner import ConfigError
from eink_planner.config import StrictDict, load
from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.services.compile import ensure_typst
from eink_planner.services.generate import Generate
from eink_planner.toml_config import parse_toml
from tests.toml_fixtures import omit_toml_sections, short_january

REPO = Path(__file__).resolve().parents[1]
NOMAD = REPO / "configs/supernote-nomad.toml"

SECTIONS = (
    "cover",
    "annual",
    "quarterly",
    "monthly",
    "weekly",
    "daily",
    "daily_notes",
    "projects",
    "habits",
    "review",
    "meetings",
    "colophon",
)

_MISSING_LABEL = re.compile(
    r"(?:label|reference)\s+`?<([^>`]+)>`?|(?:unknown label)\s+`?<([^>`]+)>`?",
    re.IGNORECASE,
)
_PADDED_LINK = re.compile(r"padded_link\(<([^>]+)>")
_LABEL_DEF = re.compile(r"(?<!padded_link\()<([A-Za-z0-9._:-]+)>")


def _dto_omitting(*kinds: str, short: bool = True) -> StrictDict:
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), kinds)
    dto = parse_toml(text, source="omit.toml")
    return short_january(dto) if short else dto


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
    if label == "habits" or label.startswith("habits-"):
        return "habits"
    if label == "review" or label.startswith("review-"):
        return "review"
    if label == "meetings" or label.startswith("meetings-") or label.startswith("meeting-"):
        return "meetings"
    if label.startswith("daily-note-"):
        return "daily_notes"
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
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), ["daily"])
    dto = parse_toml(text, source="omit-daily.toml")
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
    assert kinds == frozenset()


@pytest.mark.parametrize(
    "omit,remain",
    [
        (("annual", "quarterly"), ("cover", "monthly", "weekly", "daily", "daily_notes", "projects", "habits", "review", "meetings", "colophon")),
        (("weekly",), ("cover", "annual", "quarterly", "monthly", "daily", "daily_notes", "projects", "habits", "review", "meetings", "colophon")),
        (("monthly",), ("cover", "annual", "quarterly", "weekly", "daily", "daily_notes", "projects", "habits", "review", "meetings", "colophon")),
        (("daily",), ("cover", "annual", "quarterly", "monthly", "weekly", "daily_notes", "projects", "habits", "review", "meetings", "colophon")),
        (("daily_notes",), ("cover", "annual", "quarterly", "monthly", "weekly", "daily", "projects", "habits", "review", "meetings", "colophon")),
        (
            ("cover", "annual", "quarterly", "monthly", "weekly", "daily_notes"),
            ("daily", "projects", "habits", "review", "meetings", "colophon"),
        ),
        (
            ("annual", "quarterly", "monthly", "weekly", "daily", "daily_notes"),
            ("cover", "projects", "habits", "review", "meetings", "colophon"),
        ),
    ],
    ids=[
        "no-annual-quarterly",
        "no-weekly",
        "no-monthly",
        "notes-without-daily",
        "no-daily_notes",
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
    text = omit_toml_sections(NOMAD.read_text(encoding="utf-8"), SECTIONS)
    with pytest.raises(ConfigError, match="sections"):
        parse_toml(text, source="empty.toml")


def test_all_disabled_sections_raises_config_error():
    data = load(NOMAD).to_plain()
    for section in data["planner"]["sections"]:
        section["enabled"] = False
    with pytest.raises(ConfigError, match="No enabled planner sections"):
        Configurator(StrictDict(data)).enabled_sections()


def test_commented_cover_still_generates():
    dto = short_january(_dto_omitting("cover", short=False))
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
