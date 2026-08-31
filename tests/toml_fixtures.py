"""Shared TOML profile fixtures for tests."""

from parch.config import StrictDict


def _minimal(*, enable: list[str] | None = None, **extra: str) -> str:
    """Build a minimal TOML profile.

    extra keys override chunks: device, calendar, style, mos, sections,
    sections_list. Empty strings omit that chunk.
    """
    names = enable
    parts = {
        "device": """[device]
name = "158x210"
ppi = 300""",
        "calendar": """[calendar]
year = 2026
week_starts = "Monday\"""",
        "style": """[style.stroke]
regular = "0.3pt"
thick = "0.6pt"

[style.type]
body = "8pt"
h1 = "8mm"

[style.gutter]
column = "8pt\"""",
        "mos": """[mos]
side_menu = "left"
side_menu_width = "8mm"
reverse_months_quarters = true
menu_rotate = "270deg"
column_gutter = "1.5mm"
row_gutter = "1.5mm\"""",
    }
    if "sections" not in extra:
        extra = dict(extra)
        extra["sections"] = """[section.cover]
title = "Hi"
font_size = "12pt\""""
        if names is None:
            names = ["cover"]
    if "sections_list" not in extra:
        extra = dict(extra)
        if names is None:
            names = ["cover"]
        extra["sections_list"] = "sections = [" + ", ".join(f'"{n}"' for n in names) + "]"
    parts.update(extra)
    order = ["sections_list", "device", "calendar", "style", "mos", "sections"]
    chunks = [parts[k] for k in order if k in parts and parts[k]]
    return "\n\n".join(chunks) + "\n"


def omit_toml_sections(text: str, kinds: list[str] | tuple[str, ...]) -> str:
    """Drop names from the top-level ``sections = [...]`` array."""
    want = set(kinds)
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    in_sections = False
    for line in lines:
        stripped = line.strip()
        if not in_sections and stripped.startswith("sections"):
            in_sections = True
            if stripped.endswith("]") and "[" in stripped:
                # single-line array
                inner = stripped[stripped.index("[") + 1 : stripped.rindex("]")]
                kept = []
                for part in inner.split(","):
                    name = part.strip().strip('"').strip("'")
                    if name and name not in want:
                        kept.append(f'"{name}"')
                indent = line[: len(line) - len(line.lstrip())]
                out.append(f"{indent}sections = [{', '.join(kept)}]\n" if line.endswith("\n") else f"{indent}sections = [{', '.join(kept)}]")
                in_sections = False
                continue
            out.append(line)
            continue
        if in_sections:
            name = stripped.rstrip(",").strip('"').strip("'")
            if name in want:
                continue
            if stripped == "]":
                in_sections = False
            out.append(line)
            continue
        out.append(line)
    return "".join(out)


def add_toml_section(text: str, name: str, body: str = "", *, before: str | None = None, table: bool = True) -> str:
    """Insert ``name`` into ``sections`` and append ``[section.name]``."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    inserted = False
    in_sections = False
    for line in lines:
        stripped = line.strip()
        if not in_sections and stripped.startswith("sections"):
            in_sections = True
            if stripped.endswith("]") and "[" in stripped:
                inner = stripped[stripped.index("[") + 1 : stripped.rindex("]")]
                items = [part.strip().strip('"').strip("'") for part in inner.split(",") if part.strip()]
                if name not in items:
                    if before and before in items:
                        items.insert(items.index(before), name)
                    else:
                        items.append(name)
                indent = line[: len(line) - len(line.lstrip())]
                quoted = ", ".join(f'"{item}"' for item in items)
                nl = "\n" if line.endswith("\n") else ""
                out.append(f"{indent}sections = [{quoted}]{nl}")
                in_sections = False
                inserted = True
                continue
            out.append(line)
            continue
        if in_sections:
            raw = stripped.rstrip(",").strip('"').strip("'")
            if before and raw == before and not inserted:
                indent = line[: len(line) - len(line.lstrip())]
                out.append(f'{indent}"{name}",\n')
                inserted = True
            if stripped == "]" and not inserted:
                indent = line[: len(line) - len(line.lstrip())]
                # previous line may need a comma; add the name before ]
                if out and out[-1].rstrip().endswith('"'):
                    prev = out[-1]
                    if not prev.rstrip().endswith(","):
                        out[-1] = prev.rstrip("\n") + ",\n"
                out.append(f'{indent}"{name}",\n')
                inserted = True
            out.append(line)
            if stripped == "]":
                in_sections = False
            continue
        out.append(line)
    if not table:
        return "".join(out)
    block = f"\n[section.{name}]\n"
    if body:
        block += body.rstrip() + "\n"
    return "".join(out).rstrip() + "\n" + block


def short_january(dto: StrictDict) -> StrictDict:
    data = dto.to_plain()
    data["planner"]["params"]["start_date"] = "2026-01-01"
    data["planner"]["params"]["end_date"] = "2026-01-14"
    return StrictDict(data)
