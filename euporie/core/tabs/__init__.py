"""Contain various application tab implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from euporie.core.tabs.base import Tab


@dataclass
class TabRegistryEntry:
    """Class to store tab information."""

    path: str
    name: str
    mime_types: set = field(default_factory=set)
    file_extensions: dict[str, None] = field(default_factory=dict)
    weight: int = 0

    @property
    def tab_class(self) -> type[Tab]:
        """Import and return the tab class."""
        module_path, _, attribute = self.path.partition(":")
        module = import_module(module_path)
        return getattr(module, attribute)

    def __lt__(self, other: TabRegistryEntry) -> bool:
        """Sort by weight."""
        return self.weight < other.weight


_TAB_REGISTRY: list[TabRegistryEntry] = []
