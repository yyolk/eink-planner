"""compose — coordinator + manifest + page payload. Not Typst compile. Not CLI press."""

from parch.compose.ctx import ComposeCtx
from parch.compose.manifest import Manifest
from parch.compose.page_data import PageData
from parch.compose.protocols import Chase, Section

__all__ = [
    "Chase",
    "ComposeCtx",
    "Manifest",
    "PageData",
    "Section",
]
