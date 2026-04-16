import logging
from enum import Enum
from typing import TYPE_CHECKING

from .filters import FilterOrBool

if TYPE_CHECKING:
    from apptk.layout.controls import BufferControl, SearchBufferControl

log = logging.getLogger(__name__)

__all__ = [
    "SearchDirection",
    "accept_global_search",
    "accept_search",
    "do_incremental_search",
    "find_next_match",
    "find_search_control",
    "find_searchable_controls",
    "replace_all",
    "start_global_search",
    "start_search",
    "stop_global_search",
    "stop_search",
]

class SearchDirection(Enum):
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"

def start_search(
    buffer_control: BufferControl | None = None,
    direction: SearchDirection = SearchDirection.FORWARD,
) -> None: ...
def stop_search(buffer_control: BufferControl | None = None) -> None: ...
def do_incremental_search(direction: SearchDirection, count: int = 1) -> None: ...
def accept_search() -> None: ...
def find_search_control() -> tuple[
    SearchBufferControl | None, BufferControl | None
]: ...
def find_searchable_controls(
    search_buffer_control: SearchBufferControl,
    current_control: BufferControl | None,
) -> list[BufferControl]: ...
def start_global_search(
    buffer_control: BufferControl | None = None,
    direction: SearchDirection = SearchDirection.FORWARD,
) -> None: ...
def stop_global_search() -> None: ...
def accept_global_search() -> None: ...
def find_next_match(direction: SearchDirection) -> None: ...
def find() -> None: ...
def replace_all(find_str: str, replace_str: str) -> None: ...

class SearchState:
    __slots__ = ("direction", "ignore_case", "text")
    text: str
    direction: SearchDirection
    ignore_case: FilterOrBool
    def __init__(
        self,
        text: str = "",
        direction: SearchDirection = SearchDirection.FORWARD,
        ignore_case: FilterOrBool = False,
    ) -> None: ...
    def __invert__(self) -> SearchState: ...
    def __repr__(self) -> str: ...
