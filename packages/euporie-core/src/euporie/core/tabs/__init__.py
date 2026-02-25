"""Contain various application tab implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pkgutil import resolve_name
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
        return resolve_name(self.path)

    def __lt__(self, other: TabRegistryEntry) -> bool:
        """Sort by weight."""
        return self.weight < other.weight

    def __hash__(self) -> int:
        """Make the class hashable based on its path."""
        return hash(self.path)

    def __eq__(self, other: object) -> bool:
        """Compare TabRegistryEntry objects based on their path."""
        if not isinstance(other, TabRegistryEntry):
            return NotImplemented
        return self.path == other.path


_TAB_REGISTRY: list[TabRegistryEntry] = []
