import string
from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING, TypeVar

from apptk.buffer import Buffer
from apptk.clipboard import ClipboardData
from apptk.document import Document
from apptk.filters import Condition
from apptk.key_binding.key_processor import KeyPressEvent
from apptk.selection import SelectionType

from ..key_bindings import KeyBindings, KeyBindingsBase

if TYPE_CHECKING:
    from apptk.key_binding.key_bindings import KeyBindings, KeyBindingsBase

E = KeyPressEvent
ascii_lowercase = string.ascii_lowercase
vi_register_names = ascii_lowercase + "0123456789"

class TextObjectType(Enum):
    EXCLUSIVE = "EXCLUSIVE"
    INCLUSIVE = "INCLUSIVE"
    LINEWISE = "LINEWISE"
    BLOCK = "BLOCK"

class TextObject:
    start: int
    end: int
    type: TextObjectType
    def __init__(
        self,
        start: int,
        end: int = 0,
        type: TextObjectType = TextObjectType.EXCLUSIVE,
    ) -> None: ...
    @property
    def selection_type(self) -> SelectionType: ...
    def sorted(self) -> tuple[int, int]: ...
    def operator_range(self, document: Document) -> tuple[int, int]: ...
    def get_line_numbers(self, buffer: Buffer) -> tuple[int, int]: ...
    def cut(self, buffer: Buffer) -> tuple[Document, ClipboardData]: ...

TextObjectFunction = Callable[[E], TextObject]
_TOF = TypeVar("_TOF", bound=TextObjectFunction)
OperatorFunction = Callable[[E, TextObject], None]
_OF = TypeVar("_OF", bound=OperatorFunction)

__all__ = [
    "load_vi_bindings",
    "load_vi_search_bindings",
]

def create_text_object_decorator(
    key_bindings: KeyBindings,
) -> Callable[..., Callable[[_TOF], _TOF]]: ...
def create_operator_decorator(
    key_bindings: KeyBindings,
) -> Callable[..., Callable[[_OF], _OF]]: ...

is_returnable: Condition
in_block_selection: Condition
digraph_symbol_1_given: Condition
search_buffer_is_empty: Condition
tilde_operator: Condition

def load_vi_bindings() -> KeyBindingsBase: ...
def load_vi_search_bindings() -> KeyBindingsBase: ...
