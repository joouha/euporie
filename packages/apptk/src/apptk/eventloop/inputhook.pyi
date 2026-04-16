from asyncio import AbstractEventLoop
from collections.abc import Callable, Mapping
from selectors import BaseSelector, SelectorKey
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import TypeAlias

_EventMask = int
InputHook: TypeAlias = Callable[[InputHookContext], None]

__all__ = [
    "InputHook",
    "InputHookContext",
    "InputHookSelector",
    "new_eventloop_with_inputhook",
    "set_eventloop_with_inputhook",
]

def new_eventloop_with_inputhook(
    inputhook: Callable[[InputHookContext], None],
) -> AbstractEventLoop: ...
def set_eventloop_with_inputhook(
    inputhook: Callable[[InputHookContext], None],
) -> AbstractEventLoop: ...

class InputHookContext:
    _fileno: int
    input_is_ready: Callable[[], bool]
    def __init__(self, fileno: int, input_is_ready: Callable[[], bool]) -> None: ...
    def fileno(self) -> int: ...

class InputHookSelector(BaseSelector):
    selector: BaseSelector
    inputhook: Callable[[InputHookContext], None]
    _r = -1
    _w = -1
    def __init__(
        self,
        selector: BaseSelector,
        inputhook: Callable[[InputHookContext], None],
    ) -> None: ...
    def register(
        self,
        fileobj: FileDescriptorLike,
        events: _EventMask,
        data: Any = None,
    ) -> SelectorKey: ...
    def unregister(self, fileobj: FileDescriptorLike) -> SelectorKey: ...
    def modify(
        self,
        fileobj: FileDescriptorLike,
        events: _EventMask,
        data: Any = None,
    ) -> SelectorKey: ...
    def select(
        self,
        timeout: float | None = None,
    ) -> list[tuple[SelectorKey, _EventMask]]: ...
    def close(self) -> None: ...
    def get_map(self) -> Mapping[FileDescriptorLike, SelectorKey]: ...
