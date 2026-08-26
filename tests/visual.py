"""Raster helpers for design checks; safe to delete with the tests that import them."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image


def raster_page(pdf: Path, page: int, dest: Path, dpi: int = 150) -> Path:
    """Raster one 1-based PDF page to *dest* as a PNG via pdftoppm."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        raise FileNotFoundError(
            "pdftoppm not found; install poppler-utils (CI already does)"
        )
    prefix = dest.with_suffix("")
    result = subprocess.run(
        [
            pdftoppm,
            "-png",
            "-r",
            str(dpi),
            "-f",
            str(page),
            "-l",
            str(page),
            "-singlefile",
            str(pdf),
            str(prefix),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"pdftoppm failed (page {page}, dpi {dpi}): {detail}")
    written = prefix.with_suffix(".png")
    if written != dest:
        written.replace(dest)
    if not dest.is_file():
        raise RuntimeError(f"pdftoppm did not write {dest}")
    return dest


def full_width_bands(
    image: Path,
    *,
    x0_frac: float = 0.12,
    dark: int = 64,
    coverage: float = 0.62,
) -> list[tuple[int, int, int]]:
    """Return (y0, y1, thickness_px) for dark full-width rows, skipping the MOS strip."""
    with Image.open(image) as src:
        im = src.convert("L")
    width, height = im.size
    pixels = im.load()
    x0 = int(width * x0_frac)
    span = width - x0
    dark_rows: list[int] = []
    for y in range(height):
        n = sum(1 for x in range(x0, width) if pixels[x, y] <= dark)
        if n / span >= coverage:
            dark_rows.append(y)
    out: list[tuple[int, int, int]] = []
    i = 0
    while i < len(dark_rows):
        start = dark_rows[i]
        end = start
        i += 1
        while i < len(dark_rows) and dark_rows[i] == end + 1:
            end = dark_rows[i]
            i += 1
        out.append((start, end, end - start + 1))
    return out
