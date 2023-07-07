"""Miscellaneou utility classes."""

from __future__ import annotations

import contextvars
from itertools import chain
from threading import Thread
from typing import TYPE_CHECKING, Sequence, TypeVar, overload

from prompt_toolkit.mouse_events import MouseButton, MouseEventType

if TYPE_CHECKING:
    from typing import Any, Callable, Iterable

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
    def __getitem__(self, i: int) -> T:
        ...

    @overload
    def __getitem__(self, i: slice) -> list[T]:
        ...

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


def run_in_thread_with_context(
    func: Callable, *args: Any, daemon: bool = True, **kwargs: Any
) -> None:
    """Run a function in an thread, but make sure it uses the same contextvars.

    This is required so that the function will see the right application.
    """
    Thread(
        target=contextvars.copy_context().run,
        args=(func, *args),
        kwargs=kwargs,
        daemon=daemon,
    ).start()
