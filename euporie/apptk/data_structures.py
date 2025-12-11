"""Contain commonly used data structures."""

from __future__ import annotations

from functools import lru_cache
from typing import NamedTuple, TypeVar, overload

_T = TypeVar("_T")


class DiBool(NamedTuple):
    """A tuple of four bools with directions."""

    top: bool = False
    right: bool = False
    bottom: bool = False
    left: bool = False

    @classmethod
    def from_value(cls, value: bool) -> DiBool:
        """Construct an instance from a single value."""
        return cls(top=value, right=value, bottom=value, left=value)


class DiInt(NamedTuple):
    """A tuple of four integers with directions."""

    top: int = 0
    right: int = 0
    bottom: int = 0
    left: int = 0

    @overload
    def __add__(self, other: tuple[int, ...], /) -> DiInt: ...
    @overload
    def __add__(self, other: tuple[_T, ...], /) -> DiInt: ...

    def __add__(self, other):
        """Add two DiInt instances together."""
        if not isinstance(other, DiInt):
            return NotImplemented

        return DiInt(
            top=self.top + other.top,
            right=self.right + other.right,
            bottom=self.bottom + other.bottom,
            left=self.left + other.left,
        )

    @classmethod
    def from_value(cls, value: int) -> DiInt:
        """Construct an instance from a single value."""
        return cls(top=value, right=value, bottom=value, left=value)


class DiStr(NamedTuple):
    """A tuple of four strings with directions."""

    top: str = ""
    right: str = ""
    bottom: str = ""
    left: str = ""

    @classmethod
    def from_value(cls, value: str) -> DiStr:
        """Construct an instance from a single value."""
        return cls(top=value, right=value, bottom=value, left=value)


class WeightedInt(NamedTuple):
    """Ainterger with an associated weight."""

    weight: int
    value: int


class WeightedDiInt(NamedTuple):
    """A tuple of four weighted integers."""

    top: WeightedInt
    right: WeightedInt
    bottom: WeightedInt
    left: WeightedInt

    # We cannot use :py:func:`functools.cached_property` here as it does not work with
    # :py:Class:`NamedTuple`s.
    @property  # type: ignore
    @lru_cache(maxsize=1)  # noqa: B019
    def unweighted(self) -> DiInt:
        """Get the padding without weights."""
        return DiInt(*(x.value for x in self))
