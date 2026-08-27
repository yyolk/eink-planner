"""CLI: `parch new` and `parch generate`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from parch import ConfigError, __version__
from parch.config import load
from parch.i18n import I18n
from parch.toml_config import apply_debug, apply_year
from parch.provenance import apply_provenance, collect_provenance
from parch.mos.configurator import Configurator
from parch.services.compile import Compile, CompileError
from parch.services.generate import Generate
from parch.services.config_file import DEFAULT_FROM, resolve_from, run_new, shipped_help
from parch.services.preview_svg import DEFAULT_SCALE, parse_pages, preview_svg, sample_page_numbers


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def samples_dest(repo: Path, config: str | Path) -> Path:
    """README sample dir: docs/samples/<config-stem>/."""
    return repo / "docs" / "samples" / Path(config).stem


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="parch",
        description="Generate a yearly e-ink planner PDF from a TOML config.",
    )
    parser.add_argument("--version", action="version", version=f"parch {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser(
        "new",
        help="Write a planner from a shipped profile.",
        description="Write a planner from a shipped profile.",
        epilog="Shipped profiles: " + shipped_help() + ".",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    new.add_argument("outfile", nargs="?", help="Output path")
    new.add_argument(
        "-o",
        "--output",
        help="Output path (alias for outfile)",
    )
    new.add_argument(
        "--from",
        dest="from_profile",
        default=None,
        metavar="PROFILE",
        help=f"Starting profile or path (default {DEFAULT_FROM}).",
    )
    new.add_argument(
        "--year",
        type=int,
        default=None,
        help="Year. Also updates a year-only cover title.",
    )
    new.add_argument(
        "--sections",
        default=None,
        help="Sections to keep, comma-separated.",
    )
    new.add_argument(
        "--yes",
        action="store_true",
        help="No prompts; use flags and source-file defaults",
    )
    new.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing outfile",
    )

    gen = sub.add_parser("generate", help="Generate Typst + PDF from a TOML config")
    gen.add_argument("config", help="Planner profile (path or shipped stem)")
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
    prev.add_argument("config", help="Planner profile (path or shipped stem)")
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
    pages_or_samples = prev.add_mutually_exclusive_group(required=True)
    pages_or_samples.add_argument(
        "--pages",
        help="1-based pages to export, e.g. 1,2,7 or 1-3",
    )
    pages_or_samples.add_argument(
        "--samples",
        action="store_true",
        help="Export README sample pages by Typst label to docs/samples/<config-stem>/",
    )
    prev.add_argument(
        "--scale",
        type=float,
        default=DEFAULT_SCALE,
        help="Linear scale for width/height (default: 1/2). 1 keeps Typst page size",
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


def new_cmd(args: argparse.Namespace) -> int:
    outfile = args.outfile
    if outfile and args.output and outfile != args.output:
        raise ConfigError("give outfile as a positional or -o, not both")
    if outfile is None:
        outfile = args.output
    return run_new(
        outfile=outfile,
        from_profile=args.from_profile,
        year=args.year,
        sections=args.sections,
        yes=bool(args.yes),
        force=bool(args.force),
    )


def generate_cmd(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    config_path = resolve_from(args.config)
    i18n = I18n.load_default(args.locale)

    dto = apply_debug(load(config_path), debug=bool(args.debug))
    dto = apply_year(dto, args.year)
    dto = apply_provenance(
        dto,
        collect_provenance(
            config_path=config_path,
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
        tools_dir=_repo_root() / ".tools",
    )
    print(f"Wrote {pdf}")
    return 0


def preview_svg_cmd(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    repo = _repo_root()
    config_path = resolve_from(args.config)
    i18n = I18n.load_default(args.locale)
    dto = apply_debug(load(config_path), debug=bool(args.debug))
    dto = apply_year(dto, args.year)
    dto = apply_provenance(
        dto,
        collect_provenance(
            config_path=config_path,
            argv=list(argv) if argv is not None else list(sys.argv),
        ),
    )
    typst_source = Generate(i18n=i18n).generate(dto)
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "index.typst").write_text(typst_source, encoding="utf-8")
    print(f"Wrote {workdir / 'index.typst'}")

    if args.samples:
        if args.crop:
            raise CompileError("--crop cannot be used with --samples")
        cfg = Configurator(dto)
        year = cfg.start_date().year
        week_id = cfg.start_date().week().id
        jan1 = f"{year:04d}-01-01"
        stems = sample_page_numbers(typst_source, year=year, week_id=week_id, jan1=jan1)
        pages = list(stems.values())
    else:
        try:
            pages = parse_pages(args.pages)
        except ValueError as exc:
            raise CompileError(str(exc)) from exc
        stems = None
    written = Compile().compile_svg(
        workdir=workdir,
        file="index.typst",
        pages=pages,
        dest_pattern="preview-{p}.svg",
        tools_dir=repo / ".tools",
    )
    if stems is None:
        for path in written:
            raw = path.read_text(encoding="utf-8")
            path.write_text(
                preview_svg(raw, scale=args.scale, crop=bool(args.crop)),
                encoding="utf-8",
            )
            print(f"Wrote {path}")
        return 0
    dest_dir = samples_dest(repo, args.config)
    dest_dir.mkdir(parents=True, exist_ok=True)
    by_page = {int(path.stem.split("-")[-1]): path for path in written}
    for stem, number in stems.items():
        raw = by_page[number].read_text(encoding="utf-8")
        dest = dest_dir / f"{stem}.svg"
        dest.write_text(preview_svg(raw, scale=args.scale, crop=False), encoding="utf-8")
        print(f"Wrote {dest} (page {number})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    full_argv = list(sys.argv) if argv is None else [parser.prog, *argv]
    try:
        if args.command == "new":
            return new_cmd(args)
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
