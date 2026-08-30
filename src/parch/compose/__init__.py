"""compose — coordinator + manifest + page payload. Not Typst compile. Not CLI press."""

from parch.compose.manifest import Manifest
from parch.compose.page_data import HeadingMark, PageData
from parch.compose.protocols import Chase, Section
from parch.compose.coordinator import Coordinator

__all__ = [
    "Chase",
    "Coordinator",
    "HeadingMark",
    "Manifest",
    "PageData",
    "Section",
]
