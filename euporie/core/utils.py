"""Miscellaneous utility classes."""

from __future__ import annotations

from itertools import chain
from typing import TYPE_CHECKING, Sequence, TypeVar, overload

from upath import UPath

if TYPE_CHECKING:
    from os import PathLike
    from typing import Iterable, Optional, Union

T = TypeVar("T")


class ChainedList(Sequence[T]):
    """A list-like class which chains multiple lists."""

    def __init__(self, *lists: "Iterable[T]") -> "None":
        """Create a new instance."""
        self.lists = lists

    @property
    def data(self) -> "list[T]":
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


def parse_path(path: "Optional[Union[str, PathLike]]") -> "Optional[UPath]":
    """Parse and resolve a path."""
    if path is None:
        return None
    upath = UPath(path)
    try:
        upath = upath.expanduser()
    except NotImplementedError:
        pass
    try:
        upath = upath.resolve()
    except AttributeError:
        pass
    return upath
