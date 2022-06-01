"""Miscellaneous utility classes."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import chain
from typing import TYPE_CHECKING, TypeVar, overload

if TYPE_CHECKING:
    from typing import Iterable, List

T = TypeVar("T")


class ChainedList(Sequence[T]):
    """A list-like class which chains multiple lists."""

    def __init__(self, *lists: "Iterable[T]") -> "None":
        """Create a new instance."""
        self.lists = lists

    @property
    def data(self) -> "List[T]":
        """Return the list data."""
        return list(chain.from_iterable(self.lists))

    @overload
    def __getitem__(self, i: "int") -> "T":
        ...

    @overload
    def __getitem__(self, i: "slice"):
        ...

    def __getitem__(self, i):
        """Get an item from the chained lists."""
        return self.data[i]

    def __len__(self) -> "int":
        """Returns the length of the chained lists."""
        return len(self.data)
