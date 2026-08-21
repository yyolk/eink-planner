"""CLI: `lyp generate <config>` / `eink-planner generate <config>`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from eink_planner import ConfigError, __version__
from eink_planner.config import load
from eink_planner.i18n import I18n
from eink_planner.kdl_config import apply_debug
from eink_planner.services.compile import Compile, CompileError
from eink_planner.services.generate import Generate


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lyp",
        description="Generate a yearly e-ink planner PDF from a KDL config (YAML still accepted).",
    )
    parser.add_argument("--version", action="version", version=f"eink-planner {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate Typst + PDF from a KDL (or YAML) config")
    gen.add_argument("config", help="Path to planner KDL or YAML config")
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
        "-i",
        "--i18n-path",
        default=None,
        help="Path to a locale YAML file or locales/ directory",
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
    return parser


def generate_cmd(args: argparse.Namespace) -> int:
    repo = _repo_root()
    locale_path = Path(args.i18n_path) if args.i18n_path else repo / "locales"
    i18n = I18n.load(locale_path, locale=args.locale) if locale_path.is_file() else I18n.load_default(repo, args.locale)

    dto = apply_debug(load(args.config), debug=bool(args.debug))
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            return generate_cmd(args)
        parser.error(f"unknown command {args.command}")
        return 2
    except (ConfigError, CompileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
