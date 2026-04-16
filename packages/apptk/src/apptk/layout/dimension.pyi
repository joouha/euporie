from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from typing import TypeGuard

AnyDimension = Union[
    None,  # None is a valid dimension that will fit anything.
    int,
    Dimension,
    # Callable[[], 'AnyDimension']  # Recursive definition not supported by mypy.
    Callable[[], Any],
]
D = Dimension
LayoutDimension = Dimension

__all__ = [
    "AnyDimension",
    "D",
    "Dimension",
    "is_dimension",
    "max_layout_dimensions",
    "sum_layout_dimensions",
    "to_dimension",
]

def sum_layout_dimensions(dimensions: list[Dimension]) -> Dimension: ...
def max_layout_dimensions(dimensions: list[Dimension]) -> Dimension: ...
def to_dimension(value: AnyDimension) -> Dimension: ...
def is_dimension(value: object) -> TypeGuard[AnyDimension]: ...

class Dimension:
    min_specified = min is not None
    max_specified = max is not None
    preferred_specified = preferred is not None
    weight_specified = weight is not None
    min: int | None
    max: int | None
    preferred: int | None
    weight: int | None
    def __init__(
        self,
        min: int | None = None,
        max: int | None = None,
        weight: int | None = None,
        preferred: int | None = None,
    ) -> None: ...
    @classmethod
    def exact(cls, amount: int) -> Dimension: ...
    @classmethod
    def zero(cls) -> Dimension: ...
    def __repr__(self) -> str: ...
