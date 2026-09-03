"""CLI: `parch press`, `parch proof`, `parch specimen`, `parch new`, and `parch edit`."""

import argparse
import sys
import tempfile
from pathlib import Path

from parch import ConfigError, __version__
from parch.config import load
from parch.i18n import I18n
from parch.toml_config import apply_debug, apply_hand, apply_year
from parch.provenance import apply_provenance, collect_provenance
from parch.mos.configurator import Configurator
from parch.mos.preamble import copy_house_typ
from parch.services.compile import OUTPUT_FILE, Compile, CompileError
from parch.services.generate import Generate
from parch.services.config_file import open_resolved, run_edit, run_new, shipped_help
from parch.services.job_file import CANONICAL_SECTIONS, DEFAULT_DEVICE
from parch.devices import get_device
from parch.device_frame import frame_svg
from parch.services.preview_svg import (
    DEFAULT_SCALE,
    SAMPLE_STEMS,
    parse_pages,
    preview_svg,
    sample_page_numbers,
    sample_stems_for_sections,
)
from parch.services.specimen import (
    catalog_dest,
    listed_catalog_devices,
    specimens_dest,
    write_catalog_index,
    write_specimens,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def samples_dest(workdir: Path, config: str | Path) -> Path:
    """Named sample dir: ``<workdir>/<config-stem>/``."""
    return Path(workdir) / Path(config).stem


def _mutex_outfile(positional: str | None, flagged: str | None) -> str | None:
    """Return positional or -o; ConfigError if both are set and disagree."""
    if positional and flagged and positional != flagged:
        raise ConfigError("give outfile as a positional or -o, not both")
    if positional is None:
        return flagged
    return positional


def press_outfile(args: argparse.Namespace) -> str | None:
    """Positional or -o for press; ConfigError if both are set and disagree."""
    return _mutex_outfile(getattr(args, "outfile", None), getattr(args, "output", None))


def press_dest(
    config: str | Path,
    *,
    workdir: str | Path | None = None,
    outfile: str | Path | None = None,
) -> Path:
    """Product PDF: -o, else workdir/index.pdf, else cwd/<config-stem>.pdf."""
    if outfile is not None:
        return Path(outfile)
    if workdir is not None:
        return Path(workdir) / OUTPUT_FILE
    return Path.cwd() / f"{Path(config).stem}.pdf"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="parch",
        description="Generate a yearly e-ink planner PDF from a TOML config.",
    )
    parser.add_argument("--version", action="version", version=f"parch {__version__}")
    sub = parser.add_subparsers(
        dest="command", required=True, metavar="{press,proof,specimen,new,edit}"
    )

    new = sub.add_parser(
        "new",
        help="Write a job file from a device and defaults.",
        description="Write a complete job file from a device record plus defaults.",
        epilog="Devices: " + shipped_help() + ".",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    new.add_argument("outfile", nargs="?", help="Output path")
    new.add_argument(
        "-o",
        "--output",
        help="Output path (alias for outfile)",
    )
    new.add_argument(
        "-d",
        "--device",
        dest="device",
        default=None,
        metavar="DEVICE",
        help=f"Device id (default {DEFAULT_DEVICE}).",
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
        help="No prompts; use flags and device defaults",
    )
    new.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing outfile",
    )
    _add_hand_flag(new)

    edit = sub.add_parser(
        "edit",
        help="Reopen a job file in Questionary.",
        description="Reopen a job file in Questionary and write complete resume state back.",
    )
    edit.add_argument("infile", help="Existing job file")
    _add_hand_flag(edit)

    press = sub.add_parser("press", help="Press a profile to PDF")
    press.add_argument("config", help="Planner job file or device id")
    press.add_argument("outfile", nargs="?", help="Output path")
    press.add_argument(
        "-w",
        "--workdir",
        default=None,
        help="Persist index.typst / index.pdf here",
    )
    press.add_argument(
        "-o",
        "--output",
        help="Output path (alias for outfile)",
    )
    press.add_argument(
        "-l",
        "--locale",
        default="en",
        help="Locale code (default: en)",
    )
    press.add_argument(
        "-g",
        "--with-ghostscript",
        action="store_true",
        help="Run ghostscript after compilation (reduces PDF size)",
    )
    press.add_argument(
        "--debug",
        action="store_true",
        help="Draw MOS debug strokes (not a config key)",
    )
    press.add_argument(
        "--year",
        type=int,
        default=None,
        help="Overlay planner year (dates and cover title; not a config key)",
    )
    _add_hand_flag(press)

    proof = sub.add_parser(
        "proof",
        help="Pull SVG proofs of selected pages",
    )
    proof.add_argument("config", help="Planner job file or device id")
    proof.add_argument(
        "-w",
        "--workdir",
        default="./out",
        help="Working directory for index.typst / preview SVGs (default: ./out)",
    )
    proof.add_argument(
        "-l",
        "--locale",
        default="en",
        help="Locale code (default: en)",
    )
    pages_or_samples = proof.add_mutually_exclusive_group(required=True)
    pages_or_samples.add_argument(
        "--pages",
        help="1-based pages to export, e.g. 1,2,7 or 1-3",
    )
    pages_or_samples.add_argument(
        "--samples",
        action="store_true",
        help="Export sample pages by Typst label to <workdir>/<config-stem>/",
    )
    proof.add_argument(
        "--scale",
        type=float,
        default=DEFAULT_SCALE,
        help="Linear scale for width/height (default: 1/2). 1 keeps Typst page size",
    )
    proof.add_argument(
        "--crop",
        action="store_true",
        help="Tighten viewBox to glyph placements (sparse pages only; clips patterns)",
    )
    proof.add_argument("--debug", action="store_true", help="Draw MOS debug strokes")
    proof.add_argument(
        "--year",
        type=int,
        default=None,
        help="Overlay planner year (dates and cover title; not a config key)",
    )
    _add_hand_flag(proof)

    specimen = sub.add_parser(
        "specimen",
        help="Frame sample pages in a device line-drawing catalog",
    )
    specimen.add_argument("config", help="Planner job file or device id")
    specimen.add_argument(
        "-w",
        "--workdir",
        default="./out",
        help="Working directory; catalog is <workdir>/specimens/<device-id>/",
    )
    specimen.add_argument(
        "-l",
        "--locale",
        default="en",
        help="Locale code (default: en)",
    )
    specimen.add_argument("--debug", action="store_true", help="Draw MOS debug strokes")
    specimen.add_argument(
        "--year",
        type=int,
        default=None,
        help="Overlay planner year (dates and cover title; not a config key)",
    )
    _add_hand_flag(specimen)

    new.set_defaults(run=new_cmd)
    edit.set_defaults(run=edit_cmd)
    press.set_defaults(run=generate_cmd)
    proof.set_defaults(run=preview_svg_cmd)
    specimen.set_defaults(run=specimen_cmd)
    return parser


def _add_hand_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--hand",
        choices=("left", "right"),
        default=None,
        help="MOS strip side (default: profile mos.side_menu, or left)",
    )


def new_cmd(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    outfile = _mutex_outfile(args.outfile, args.output)
    return run_new(
        outfile=outfile,
        device=args.device,
        year=args.year,
        sections=args.sections,
        yes=bool(args.yes),
        force=bool(args.force),
        hand=getattr(args, "hand", None),
    )


def edit_cmd(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    return run_edit(infile=args.infile, hand=getattr(args, "hand", None))


def generate_cmd(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    outfile = press_outfile(args)
    workdir_arg = args.workdir
    dest = press_dest(args.config, workdir=workdir_arg, outfile=outfile)
    with open_resolved(args.config) as config_path:
        i18n = I18n.load_default(args.locale)
        dto = apply_debug(load(config_path), debug=bool(args.debug))
        dto = apply_year(dto, args.year)
        dto = apply_hand(dto, getattr(args, "hand", None))
        dto = apply_provenance(
            dto,
            collect_provenance(
                config_path=config_path,
                argv=list(argv) if argv is not None else list(sys.argv),
            ),
        )
    typst_source = Generate(i18n=i18n).generate(dto)
    device = str(dto["device"])
    if workdir_arg:
        return _press_from_workdir(Path(workdir_arg), dest, typst_source, device, args)
    return _press_from_temp(dest, typst_source, device, args)


def _compile_book(
    workdir: Path,
    typst_source: str,
    device: str,
    args: argparse.Namespace,
    *,
    announce: bool,
) -> Path:
    """Write Typst and compile; dest placement is the caller's job."""
    _write_generated_book(workdir, typst_source, device, announce=announce)
    return Compile().compile(
        workdir=workdir,
        file="index.typst",
        enable_ghostscript=args.with_ghostscript,
        tools_dir=_repo_root() / ".tools",
    )


def _press_from_workdir(
    workdir: Path,
    dest: Path,
    typst_source: str,
    device: str,
    args: argparse.Namespace,
) -> int:
    """Persist intermediates in workdir; copy to -o when dest is elsewhere."""
    pdf = _compile_book(workdir, typst_source, device, args, announce=True)
    if dest.resolve() != pdf.resolve():
        dest.parent.mkdir(parents=True, exist_ok=True)
        pdf.copy(dest)
    print(f"Wrote {dest}")
    return 0


def _press_from_temp(
    dest: Path,
    typst_source: str,
    device: str,
    args: argparse.Namespace,
) -> int:
    """Compile in a TemporaryDirectory and Path.move the PDF onto dest before cleanup."""
    with tempfile.TemporaryDirectory() as tmp:
        pdf = _compile_book(Path(tmp), typst_source, device, args, announce=False)
        dest.parent.mkdir(parents=True, exist_ok=True)
        pdf.move(dest)
        print(f"Wrote {dest}")
        return 0


def preview_svg_cmd(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    repo = _repo_root()
    with open_resolved(args.config) as config_path:
        i18n = I18n.load_default(args.locale)
        dto = apply_debug(load(config_path), debug=bool(args.debug))
        dto = apply_year(dto, args.year)
        dto = apply_hand(dto, getattr(args, "hand", None))
        dto = apply_provenance(
            dto,
            collect_provenance(
                config_path=config_path,
                argv=list(argv) if argv is not None else list(sys.argv),
            ),
        )
    typst_source = Generate(i18n=i18n).generate(dto)
    workdir = Path(args.workdir)
    _write_generated_book(workdir, typst_source, device=str(dto["device"]))

    if args.samples:
        if args.crop:
            raise CompileError("--crop cannot be used with --samples")
        cfg = Configurator(dto)
        year = cfg.start_date().year
        week_id = cfg.start_date().week().id
        jan1 = f"{year:04d}-01-01"
        wanted = sample_stems_for_sections(
            [section["name"] for section in cfg.enabled_sections()]
        )
        stems = sample_page_numbers(
            typst_source, year=year, week_id=week_id, jan1=jan1, stems=wanted
        )
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
    dest_dir = samples_dest(workdir, args.config)
    dest_dir.mkdir(parents=True, exist_ok=True)
    by_page = {int(path.stem.split("-")[-1]): path for path in written}
    for stem, number in stems.items():
        raw = by_page[number].read_text(encoding="utf-8")
        dest = dest_dir / f"{stem}.svg"
        dest.write_text(preview_svg(raw, scale=args.scale, crop=False), encoding="utf-8")
        print(f"Wrote {dest} (page {number})")
    return 0


def specimen_cmd(args: argparse.Namespace, argv: list[str] | None = None) -> int:
    repo = _repo_root()
    with open_resolved(args.config, sections=CANONICAL_SECTIONS) as config_path:
        i18n = I18n.load_default(args.locale)
        dto = apply_debug(load(config_path), debug=bool(args.debug))
        dto = apply_year(dto, args.year)
        dto = apply_hand(dto, getattr(args, "hand", None))
        dto = apply_provenance(
            dto,
            collect_provenance(
                config_path=config_path,
                argv=list(argv) if argv is not None else list(sys.argv),
            ),
        )
        device = get_device(str(dto["device"]))
        try:
            frame_svg(device)
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc
    typst_source = Generate(i18n=i18n).generate(dto)
    workdir = Path(args.workdir)
    _write_generated_book(workdir, typst_source, device=device.id)
    cfg = Configurator(dto)
    year = cfg.start_date().year
    week_id = cfg.start_date().week().id
    jan1 = f"{year:04d}-01-01"
    stems = sample_page_numbers(
        typst_source, year=year, week_id=week_id, jan1=jan1, stems=SAMPLE_STEMS
    )
    pages = list(stems.values())
    written = Compile().compile_svg(
        workdir=workdir,
        file="index.typst",
        pages=pages,
        dest_pattern="preview-{p}.svg",
        tools_dir=repo / ".tools",
    )
    by_page = {int(path.stem.split("-")[-1]): path for path in written}
    dest_dir = specimens_dest(workdir, device.id)
    pages_by_stem = {
        stem: by_page[stems[stem]].read_text(encoding="utf-8") for stem in SAMPLE_STEMS
    }
    write_specimens(dest_dir, device, pages_by_stem)
    root = catalog_dest(workdir)
    catalog = write_catalog_index(root, listed_catalog_devices(root))
    for stem in SAMPLE_STEMS:
        print(f"Wrote {dest_dir / f'{stem}.svg'} (page {stems[stem]})")
    print(f"Wrote {dest_dir / 'index.html'}")
    print(f"Wrote {catalog}")
    return 0


def _write_generated_book(
    workdir: Path, typst_source: str, device: str, *, announce: bool = True
) -> None:
    """Write index.typst, house.typ, and the parameterized device.typ."""
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "index.typst").write_text(typst_source, encoding="utf-8")
    copy_house_typ(workdir, device=device)
    if announce:
        print(f"Wrote {workdir / 'index.typst'}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    full_argv = list(sys.argv) if argv is None else [parser.prog, *argv]
    try:
        return args.run(args, argv=full_argv)
    except (ConfigError, CompileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
