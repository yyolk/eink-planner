"""CLI: `lyp generate <config>` / `eink-planner generate <config>`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from eink_planner import ConfigError, __version__
from eink_planner.config import load
from eink_planner.i18n import I18n
from eink_planner.toml_config import apply_debug, apply_year
from eink_planner.provenance import apply_provenance, collect_provenance
from eink_planner.services.compile import Compile, CompileError
from eink_planner.services.generate import Generate
from eink_planner.services.preview_svg import DEFAULT_SCALE, parse_pages, preview_svg


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lyp",
        description="Generate a yearly e-ink planner PDF from a TOML config.",
    )
    parser.add_argument("--version", action="version", version=f"eink-planner {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate Typst + PDF from a TOML config")
    gen.add_argument("config", help="Path to planner TOML config")
    gen.add_argument(
        "-w",
        "--workdir",
        default="./out",
        help="Working directory for index.typst / index.pdf (default: ./out)",
    )
    gen.add_argument(
        "-l",
        "--locale",
        default="en",
        help="Locale code (default: en)",
    )
    gen.add_argument(
        "-g",
        "--with-ghostscript",
        action="store_true",
        help="Run ghostscript after compilation (reduces PDF size)",
    )
    gen.add_argument(
        "--debug",
        action="store_true",
        help="Draw MOS debug strokes (not a config key)",
    )
    gen.add_argument(
        "--year",
        type=int,
        default=None,
        help="Overlay planner year (dates and cover title; not a config key)",
    )

    prev = sub.add_parser(
        "preview-svg",
        help="Compile selected Typst pages to preview SVGs (not a PDF raster)",
    )
    prev.add_argument("config", help="Path to planner TOML config")
    prev.add_argument(
        "-w",
        "--workdir",
        default="./out",
        help="Working directory for index.typst / preview SVGs (default: ./out)",
    )
    prev.add_argument(
        "-l",
        "--locale",
        default="en",
        help="Locale code (default: en)",
    )
    prev.add_argument(
        "--pages",
        required=True,
        help="1-based pages to export, e.g. 1,2,7 or 1-3",
    )
    prev.add_argument(
        "--scale",
        type=float,
        default=DEFAULT_SCALE,
        help="Linear scale for width/height (default: 1/3). 1 keeps Typst page size",
    )
    prev.add_argument(
        "--crop",
        action="store_true",
        help="Tighten viewBox to glyph placements (sparse pages only; clips patterns)",
    )
    prev.add_argument("--debug", action="store_true", help="Draw MOS debug strokes")
    prev.add_argument(
        "--year",
        type=int,
        default=None,
        help="Overlay planner year (dates and cover title; not a config key)",
    )
    return parser


def generate_cmd(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    repo = _repo_root()
    i18n = I18n.load_default(repo, args.locale)

    dto = apply_debug(load(args.config), debug=bool(args.debug))
    dto = apply_year(dto, args.year)
    dto = apply_provenance(
        dto,
        collect_provenance(
            config_path=args.config,
            argv=list(argv) if argv is not None else list(sys.argv),
        ),
    )
    typst_source = Generate(i18n=i18n).generate(dto)

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "index.typst").write_text(typst_source, encoding="utf-8")
    print(f"Wrote {workdir / 'index.typst'}")

    pdf = Compile().compile(
        workdir=workdir,
        file="index.typst",
        enable_ghostscript=args.with_ghostscript,
        tools_dir=repo / ".tools",
    )
    print(f"Wrote {pdf}")
    return 0


def preview_svg_cmd(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    repo = _repo_root()
    i18n = I18n.load_default(repo, args.locale)
    dto = apply_debug(load(args.config), debug=bool(args.debug))
    dto = apply_year(dto, args.year)
    dto = apply_provenance(
        dto,
        collect_provenance(
            config_path=args.config,
            argv=list(argv) if argv is not None else list(sys.argv),
        ),
    )
    typst_source = Generate(i18n=i18n).generate(dto)
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "index.typst").write_text(typst_source, encoding="utf-8")
    print(f"Wrote {workdir / 'index.typst'}")

    try:
        pages = parse_pages(args.pages)
    except ValueError as exc:
        raise CompileError(str(exc)) from exc
    written = Compile().compile_svg(
        workdir=workdir,
        file="index.typst",
        pages=pages,
        dest_pattern="preview-{p}.svg",
        tools_dir=repo / ".tools",
    )
    for path in written:
        raw = path.read_text(encoding="utf-8")
        path.write_text(
            preview_svg(raw, scale=args.scale, crop=bool(args.crop)),
            encoding="utf-8",
        )
        print(f"Wrote {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    full_argv = list(sys.argv) if argv is None else [parser.prog, *argv]
    try:
        if args.command == "generate":
            return generate_cmd(args, argv=full_argv)
        if args.command == "preview-svg":
            return preview_svg_cmd(args, argv=full_argv)
        parser.error(f"unknown command {args.command}")
        return 2
    except (ConfigError, CompileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
