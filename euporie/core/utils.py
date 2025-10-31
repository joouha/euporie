"""Miscellaneous utility classes."""

from __future__ import annotations

from collections.abc import Sequence
from functools import cache
from itertools import chain
from typing import TYPE_CHECKING, TypeVar, overload

from prompt_toolkit.mouse_events import MouseButton, MouseEventType

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from types import ModuleType

    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.mouse_handlers import MouseHandler
    from prompt_toolkit.mouse_events import MouseEvent

T = TypeVar("T")


class ChainedList(Sequence[T]):
    """A list-like class which chains multiple lists."""

    def __init__(self, *lists: Iterable[T]) -> None:
        """Create a new instance."""
        self.lists = lists

    @property
    def data(self) -> list[T]:
        """Return the list data."""
        return list(chain.from_iterable(self.lists))

    @overload
    def __getitem__(self, i: int) -> T: ...

    @overload
    def __getitem__(self, i: slice) -> list[T]: ...

    def __getitem__(self, i):
        """Get an item from the chained lists."""
        return self.data[i]

    def __len__(self) -> int:
        """Return the length of the chained lists."""
        return len(self.data)


def dict_merge(target_dict: dict, input_dict: dict) -> None:
    """Merge the second dictionary onto the first."""
    for k in input_dict:
        if k in target_dict:
            if isinstance(target_dict[k], dict) and isinstance(input_dict[k], dict):
                dict_merge(target_dict[k], input_dict[k])
            elif isinstance(target_dict[k], list) and isinstance(input_dict[k], list):
                target_dict[k] = [*target_dict[k], *input_dict[k]]
            else:
                target_dict[k] = input_dict[k]
        else:
            target_dict[k] = input_dict[k]


def on_click(func: Callable) -> MouseHandler:
    """Return a mouse handler which call a given function on click."""

    def _mouse_handler(mouse_event: MouseEvent) -> NotImplementedOrNone:
        if (
            mouse_event.button == MouseButton.LEFT
            and mouse_event.event_type == MouseEventType.MOUSE_UP
        ):
            return func()
        return NotImplemented

    return _mouse_handler


@cache
def root_module(name: str) -> ModuleType:
    """Find and load the root module of a given module name by traversing up the module hierarchy.

    This function walks up the module hierarchy until it finds the topmost parent module
    that has a valid location. It uses Python's importlib machinery to inspect module
    specifications and load modules.

    Args:
        name: The name of the module to find the root for (e.g., 'package.subpackage.module')

    Returns:
        The loaded root module object

    Example:
        >>> root = root_module("django.contrib.admin")
        >>> print(root.__name__)
        'django'

    Note:
        The function is cached using lru_cache to improve performance for repeated lookups.
        The function handles both regular packages and frozen modules.
    """
    from importlib.util import find_spec, module_from_spec

    if spec := find_spec(name):
        while True:
            if spec.name == spec.parent:
                try:
                    parent = find_spec("..", spec.parent)
                except ImportError:
                    break
            elif spec.parent is not None:
                parent = find_spec(spec.parent)
            if (spec and not spec.parent) or (parent and not parent.has_location):
                break
            if parent:
                spec = parent
        if spec.loader:
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ModuleNotFoundError(name=name)


@cache
def import_submodules(root: ModuleType, names: tuple[str]) -> list[ModuleType]:
    """Import all submodules with a specific name within a root module's package hierarchy.

    This function walks through all packages under the given root module and imports
    any submodules that match the specified name. It handles various module types
    including regular packages, single file modules, and frozen modules.

    Args:
        root: The root module object to search within
        names: The specific submodule name to search for

    Returns:
        A list of imported module objects matching the specified name

    Example:
        >>> root = import_module("django")
        >>> admin_modules = import_submodules(root, "admin")
        >>> print([m.__name__ for m in admin_modules])
        ['django.contrib.admin', 'django.contrib.gis.admin']

    Note:
        - The function is cached using lru_cache to improve performance for repeated imports
        - For packages, it searches through __path__
        - For single file modules, it uses __file__
        - For frozen modules, it uses the module specification's origin
    """
    from importlib import import_module
    from pkgutil import walk_packages

    if hasattr(root, "__path__"):
        path = root.__path__
    elif hasattr(root, "__file__"):
        path = [root.__file__] if root.__file__ else []
    else:
        # For frozen modules, we need to create a special path
        spec = root.__spec__
        path = [spec.origin] if spec and spec.origin else []
    return [
        import_module(module_name)
        for _loader, module_name, _is_pkg in walk_packages(path, f"{root.__name__}.")
        if module_name.rpartition(".")[2] in names
    ]
