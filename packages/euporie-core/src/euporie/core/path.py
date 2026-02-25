"""Responsible for loading data from urls."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from upath.implementations.memory import MemoryPath

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any


log = logging.getLogger(__name__)


# Define custom universal_pathlib path implementations


class UntitledPath(MemoryPath):
    """A path for untitled files, as needed for LSP servers."""

    @classmethod
    def _parse_storage_options(
        cls, urlpath: str, protocol: str, storage_options: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Parse storage_options from the urlpath."""
        return {}

    def exists(self, *, follow_symlinks: bool = True) -> bool:
        """Untitled files are unsaved and do not exist."""
        return False
