from typing import NamedTuple, TypeVar, overload

_T = TypeVar("_T")

__all__ = [
    "DiBool",
    "DiInt",
    "DiStr",
    "Point",
    "Size",
    "WeightedDiInt",
    "WeightedInt",
]

class Point(NamedTuple):
    x: int
    y: int

class Size(NamedTuple):
    rows: int
    columns: int

class DiBool(NamedTuple):
    top: bool = False
    right: bool = False
    bottom: bool = False
    left: bool = False
    @classmethod
    def from_value(cls, value: bool) -> DiBool: ...

class DiInt(Generic[_T], NamedTuple):
    top: int = 0
    right: int = 0
    bottom: int = 0
    left: int = 0
    @overload
    def __add__(self, other: tuple[int, ...], /) -> DiInt: ...
    @overload
    def __add__(self, other: tuple[_T, ...], /) -> DiInt: ...
    def __add__(self, other): ...
    @classmethod
    def from_value(cls, value: int) -> DiInt: ...

class DiStr(NamedTuple):
    top: str = ""
    right: str = ""
    bottom: str = ""
    left: str = ""
    @classmethod
    def from_value(cls, value: str) -> DiStr: ...

class WeightedInt(NamedTuple):
    weight: int
    value: int

class WeightedDiInt(NamedTuple):
    top: WeightedInt
    right: WeightedInt
    bottom: WeightedInt
    left: WeightedInt
    @property
    def unweighted(self) -> DiInt: ...
