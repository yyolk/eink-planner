"""ComposeCtx — i18n and configurator for section constructors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from parch.i18n import I18n

if TYPE_CHECKING:
    from parch.mos.configurator import Configurator


@dataclass(frozen=True)
class ComposeCtx:
    i18n: I18n
    configurator: Configurator
