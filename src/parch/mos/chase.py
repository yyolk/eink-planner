"""chase — wrap each section page for compose; MosChase owns MOS chrome on one manifest."""

from parch.i18n import I18n
from parch.mos.builder import Builder
from parch.mos.configurator import Configurator
from parch.mos.manifest import Manifest
from parch.compose.page_data import PageData


class MosChase:
    name = "mos"

    def __init__(self, i18n: I18n, configurator: Configurator, manifest: Manifest) -> None:
        self._builder = Builder(i18n=i18n, configurator=configurator, manifest=manifest)

    def wrap(self, page: PageData, manifest: Manifest) -> str:
        return self._builder.add(page)

    def document(self) -> str:
        return self._builder.generate()


CHASES = {"mos": MosChase}
