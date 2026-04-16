from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from .application import Application

class CursorShape(Enum):
    _NEVER_CHANGE = "_NEVER_CHANGE"
    BLOCK = "BLOCK"
    BEAM = "BEAM"
    UNDERLINE = "UNDERLINE"
    BLINKING_BLOCK = "BLINKING_BLOCK"
    BLINKING_BEAM = "BLINKING_BEAM"
    BLINKING_UNDERLINE = "BLINKING_UNDERLINE"

class CursorShapeConfig(ABC):
    @abstractmethod
    def get_cursor_shape(self, application: Application[Any]) -> CursorShape: ...

AnyCursorShapeConfig = Union[CursorShape, CursorShapeConfig, None]

__all__ = [
    "CursorShape",
    "CursorShapeConfig",
    "DynamicCursorShapeConfig",
    "ModalCursorShapeConfig",
    "SimpleCursorShapeConfig",
    "to_cursor_shape_config",
]

def to_cursor_shape_config(value: AnyCursorShapeConfig) -> CursorShapeConfig: ...

class SimpleCursorShapeConfig(CursorShapeConfig):
    cursor_shape: CursorShape
    def __init__(
        self, cursor_shape: CursorShape = CursorShape._NEVER_CHANGE
    ) -> None: ...
    def get_cursor_shape(self, application: Application[Any]) -> CursorShape: ...

class ModalCursorShapeConfig(CursorShapeConfig):
    def get_cursor_shape(self, application: Application[Any]) -> CursorShape: ...

class DynamicCursorShapeConfig(CursorShapeConfig):
    get_cursor_shape_config: Callable[[], AnyCursorShapeConfig]
    def __init__(
        self,
        get_cursor_shape_config: Callable[[], AnyCursorShapeConfig],
    ) -> None: ...
    def get_cursor_shape(self, application: Application[Any]) -> CursorShape: ...
