import logging
from abc import abstractmethod
from collections.abc import Callable, Coroutine, Hashable, Sequence
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
)

from apptk.cache import SimpleCache
from apptk.filters import FilterOrBool
from apptk.keys import Keys

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .key_processor import KeyPressEvent

NotImplementedOrNone = object
KeyHandlerCallable = Callable[
    ["KeyPressEvent"],
    Union["NotImplementedOrNone", Coroutine[Any, Any, "NotImplementedOrNone"]],
]
KeysTuple = tuple[Keys | str, ...]
T = TypeVar("T", bound=KeyHandlerCallable | Binding)
log = logging.getLogger(__name__)

__all__ = [
    "Binding",
    "ConditionalKeyBindings",
    "DynamicKeyBindings",
    "GlobalOnlyKeyBindings",
    "KeyBindings",
    "KeyBindingsBase",
    "NotImplementedOrNone",
    "merge_key_bindings",
]

def key_binding(
    filter: FilterOrBool = True,
    eager: FilterOrBool = False,
    is_global: FilterOrBool = False,
    save_before: Callable[[KeyPressEvent], bool] = lambda event: True,
    record_in_macro: FilterOrBool = True,
) -> Callable[[KeyHandlerCallable], Binding]: ...
def merge_key_bindings(bindings: Sequence[KeyBindingsBase]) -> _MergedKeyBindings: ...

class Binding:
    keys: tuple[Keys | str, ...]
    handler: KeyHandlerCallable
    filter: FilterOrBool
    eager: FilterOrBool
    is_global: FilterOrBool
    save_before: Callable[[KeyPressEvent], bool]
    record_in_macro: FilterOrBool
    def __init__(
        self,
        keys: tuple[Keys | str, ...],
        handler: KeyHandlerCallable,
        filter: FilterOrBool = True,
        eager: FilterOrBool = False,
        is_global: FilterOrBool = False,
        save_before: Callable[[KeyPressEvent], bool] = lambda e: True,
        record_in_macro: FilterOrBool = True,
    ) -> None: ...
    def call(self, event: KeyPressEvent) -> None: ...
    def __repr__(self) -> str: ...

class KeyBindingsBase:
    @property
    @abstractmethod
    def _version(self) -> Hashable: ...
    @abstractmethod
    def get_bindings_for_keys(self, keys: KeysTuple) -> list[Binding]: ...
    @abstractmethod
    def get_bindings_starting_with_keys(self, keys: KeysTuple) -> list[Binding]: ...
    @property
    @abstractmethod
    def bindings(self) -> list[Binding]: ...

class KeyBindings:
    add_binding = add
    remove_binding = remove
    _bindings: list[Binding]
    _get_bindings_for_keys_cache: SimpleCache[KeysTuple, list[Binding]]
    _get_bindings_starting_with_keys_cache: SimpleCache[KeysTuple, list[Binding]]
    __version = 0
    def __init__(self) -> None: ...
    def _clear_cache(self) -> None: ...
    @property
    def bindings(self) -> list[Binding]: ...
    @property
    def _version(self) -> Hashable: ...
    def add(
        self,
        *keys: Keys | str,
        filter: FilterOrBool = True,
        eager: FilterOrBool = False,
        is_global: FilterOrBool = False,
        save_before: Callable[[KeyPressEvent], bool] = lambda e: True,
        record_in_macro: FilterOrBool = True,
    ) -> Callable[[T], T]: ...
    def remove(self, *args: Keys | str | KeyHandlerCallable) -> None: ...
    def get_bindings_for_keys(self, keys: KeysTuple) -> list[Binding]: ...
    def get_bindings_starting_with_keys(self, keys: KeysTuple) -> list[Binding]: ...
    @classmethod
    def from_commands(cls, commands: Sequence[str]) -> KeyBindings: ...

class _Proxy(KeyBindingsBase):
    _bindings2: KeyBindingsBase
    _last_version: Hashable
    def __init__(self) -> None: ...
    def _update_cache(self) -> None: ...
    @property
    def bindings(self) -> list[Binding]: ...
    @property
    def _version(self) -> Hashable: ...
    def get_bindings_for_keys(self, keys: KeysTuple) -> list[Binding]: ...
    def get_bindings_starting_with_keys(self, keys: KeysTuple) -> list[Binding]: ...

class ConditionalKeyBindings(_Proxy):
    key_bindings: KeyBindingsBase
    filter: FilterOrBool
    _bindings2 = bindings2
    _last_version = expected_version
    def __init__(
        self,
        key_bindings: KeyBindingsBase,
        filter: FilterOrBool = True,
    ) -> None: ...
    def _update_cache(self) -> None: ...

class _MergedKeyBindings(_Proxy):
    registries: Sequence[KeyBindingsBase]
    _bindings2 = bindings2
    _last_version = expected_version
    def __init__(self, registries: Sequence[KeyBindingsBase]) -> None: ...
    def _update_cache(self) -> None: ...

class DynamicKeyBindings(_Proxy):
    get_key_bindings: Callable[[], KeyBindingsBase | None]
    __version = 0
    _last_child_version = None
    _dummy: KeyBindings
    _bindings2 = key_bindings
    _last_version = version
    def __init__(
        self, get_key_bindings: Callable[[], KeyBindingsBase | None]
    ) -> None: ...
    def _update_cache(self) -> None: ...

class GlobalOnlyKeyBindings(_Proxy):
    key_bindings: KeyBindingsBase
    _bindings2 = bindings2
    _last_version = expected_version
    def __init__(self, key_bindings: KeyBindingsBase) -> None: ...
    def _update_cache(self) -> None: ...
