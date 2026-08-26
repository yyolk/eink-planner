"""Regenerate docs/samples/158x210-mos-left from Typst (half-scale SVGs)."""

from __future__ import annotations

from pathlib import Path

from eink_planner.config import load
from eink_planner.i18n import I18n
from eink_planner.mos.configurator import Configurator
from eink_planner.provenance import apply_provenance, collect_provenance
from eink_planner.services.compile import Compile
from eink_planner.services.generate import Generate
from eink_planner.services.preview_svg import (
    DEFAULT_SCALE,
    preview_svg,
    sample_page_numbers,
)
from eink_planner.toml_config import apply_debug, apply_year

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "configs" / "158x210-mos-left.toml"
DEST = REPO / "docs" / "samples" / "158x210-mos-left"


def _jan1(year: int) -> str:
    return f"{year:04d}-01-01"


def main(argv: list[str] | None = None) -> int:
    del argv
    i18n = I18n.load_default(REPO, "en")
    dto = apply_debug(load(CONFIG), debug=False)
    dto = apply_year(dto, None)
    dto = apply_provenance(
        dto,
        collect_provenance(config_path=CONFIG, argv=["lyp", "preview-svg", str(CONFIG)]),
    )
    typst_source = Generate(i18n=i18n).generate(dto)
    cfg = Configurator(dto)
    year = cfg.start_date().year
    week_id = cfg.start_date().week().id
    pages = sample_page_numbers(
        typst_source, year=year, week_id=week_id, jan1=_jan1(year)
    )

    workdir = REPO / "out" / "readme-samples"
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "index.typst").write_text(typst_source, encoding="utf-8")
    page_list = list(pages.values())
    written = Compile().compile_svg(
        workdir=workdir,
        file="index.typst",
        pages=page_list,
        dest_pattern="preview-{p}.svg",
        tools_dir=REPO / ".tools",
    )
    by_page = {int(path.stem.split("-")[-1]): path for path in written}
    DEST.mkdir(parents=True, exist_ok=True)
    for stem, number in pages.items():
        raw = by_page[number].read_text(encoding="utf-8")
        dest = DEST / f"{stem}.svg"
        dest.write_text(preview_svg(raw, scale=DEFAULT_SCALE), encoding="utf-8")
        print(f"Wrote {dest} (page {number})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
