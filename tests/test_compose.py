from parch.compose import Chase, ComposeCtx, Manifest, PageData, Section
from parch.compose.manifest import Manifest as ComposeManifest
from parch.compose.page_data import PageData as ComposePageData
from parch.mos.manifest import Manifest as MosManifest
from parch.mos.page_data import PageData as MosPageData


def test_compose_exports_match_mos_reexports():
    assert Manifest is ComposeManifest
    assert Manifest is MosManifest
    assert PageData is ComposePageData
    assert PageData is MosPageData
    assert Section is not None
    assert Chase is not None
    assert ComposeCtx is not None
