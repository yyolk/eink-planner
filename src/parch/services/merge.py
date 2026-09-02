"""Concatenate section PDFs, drop dest-table pages, union named dests."""

from collections.abc import AbstractSet, Sequence
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from parch.services.compile import CompileError


def named_dest_pages(path: Path) -> dict[str, int]:
    """Map PDF named destinations to 1-based page numbers."""
    reader = PdfReader(str(path))
    pages: dict[str, int] = {}
    for name, dest in reader.named_destinations.items():
        page = dest.get("/Page")
        if page is None:
            continue
        for i, candidate in enumerate(reader.pages, start=1):
            if candidate.indirect_reference == page or candidate == page:
                pages[str(name)] = i
                break
    return pages


def merge_pdfs(
    sources: Sequence[Path],
    dest: Path,
    *,
    drop_pages: Sequence[AbstractSet[int]] | None = None,
) -> Path:
    """Concatenate PDFs in order, drop dest-table pages, union named dests."""
    if not sources:
        raise CompileError("merge_pdfs needs at least one PDF")
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for i, src in enumerate(sources):
        src = Path(src)
        reader = PdfReader(str(src))
        total = len(reader.pages)
        if total < 1:
            raise CompileError(f"{src} has no pages")
        drop = set(drop_pages[i]) if drop_pages is not None else {total}
        keep = [p for p in range(total) if (p + 1) not in drop]
        if not keep:
            raise CompileError(f"{src}: dest-table drop left no pages")
        writer.append(reader, pages=keep, import_outline=False)
    writer.write(dest)
    writer.close()
    return dest
