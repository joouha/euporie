from collections.abc import Iterable
from typing import TYPE_CHECKING, TypeVar, overload

from apptk.formatted_text.base import OneStyleAndTextTuple

if TYPE_CHECKING:
    from typing_extensions import SupportsIndex

_T = TypeVar("_T", bound=OneStyleAndTextTuple)

__all__ = [
    "explode_text_fragments",
]

def explode_text_fragments(fragments: Iterable[_T]) -> _ExplodedList[_T]: ...

class _ExplodedList(Generic[_T], list[_T]):
    exploded = True
    def append(self, item: _T) -> None: ...
    def extend(self, lst: Iterable[_T]) -> None: ...
    def insert(self, index: SupportsIndex, item: _T) -> None: ...
    @overload
    def __setitem__(self, index: SupportsIndex, value: _T) -> None: ...
    @overload
    def __setitem__(self, index: slice, value: Iterable[_T]) -> None: ...
    def __setitem__(
        self,
        index: SupportsIndex | slice,
        value: _T | Iterable[_T],
    ) -> None: ...
