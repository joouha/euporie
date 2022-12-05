"""Defines a command object for use in key-bindings, menus, and the command palette."""

from __future__ import annotations

import logging
import weakref
from inspect import isawaitable, signature
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import to_filter
from prompt_toolkit.key_binding.key_bindings import Binding
from prompt_toolkit.key_binding.key_processor import KeyPressEvent

from euporie.core.key_binding.utils import parse_keys
from euporie.core.keys import Keys

if TYPE_CHECKING:
    from typing import Any, Callable, Coroutine, Optional, Sequence, Union

    from prompt_toolkit.filters import Filter, FilterOrBool
    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        KeyHandlerCallable,
    )

    from euporie.core.widgets.menu import MenuItem

    AnyKey = tuple[Keys | str, ...] | Keys | str
    AnyKeys = list[AnyKey] | AnyKey

log = logging.getLogger(__name__)


commands: "dict[str, Command]" = {}


class Command:
    """Wraps a function so it can be used as a key-binding or a menu item."""

    def __init__(
        self,
        handler: "Callable[..., Optional[Coroutine[Any, Any, None]]]",
        *,
        filter: "FilterOrBool" = True,
        hidden: "FilterOrBool" = False,
        name: "Optional[str]" = None,
        title: "Optional[str]" = None,
        menu_title: "Optional[str]" = None,
        description: "Optional[str]" = None,
        toggled: "Optional[Filter]" = None,
        eager: "FilterOrBool" = False,
        is_global: "FilterOrBool" = False,
        save_before: "Callable[[KeyPressEvent], bool]" = (lambda event: True),
        record_in_macro: "FilterOrBool" = True,
    ) -> "None":
        """Creates a new instance of a command.

        Args:
            handler: The callable to run when the command is triggers
            filter: The condition under which the command is allowed to run
            hidden: The condition under the command is visible to the user
            name: The name of the command, for accessing the command from the registry
            title: The title of the command for display
            menu_title: The title to display in menus if different
            description: The description of the command to explain it's function
            toggled: The toggle state of this command If this command toggles something
            eager: When True, ignore potential longer matches for this key binding
            is_global: Make this a global (always active) binding
            save_before: Determines if the buffer should be saved before running
            record_in_macro: Whether these key bindings should be recorded in macros

        """
        self.handler = handler
        self.filter = to_filter(filter)
        self.hidden = to_filter(hidden)
        if name is None:
            name = handler.__name__.strip("_").replace("_", "-")
        self.name = name
        if title is None:
            title = name.capitalize().replace("-", " ")
        self.title = title
        self.menu_title = menu_title or title
        if description is None:
            # Use the first line of the docstring as the command description
            if handler.__doc__:
                description = (
                    "".join(handler.__doc__.strip().split("\n")).split(".")[0] + "."
                )
            else:
                description = title or name.capitalize()
        self.description = description

        self.toggled = toggled
        self._menu: "Optional[MenuItem]" = None

        self.eager = to_filter(eager)
        self.is_global = to_filter(is_global)
        self.save_before = save_before
        self.record_in_macro = to_filter(record_in_macro)

        self.keys: "list[tuple[Union[str, Keys], ...]]" = []

        self.selected_item = 0
        self.children: "Sequence[MenuItem]" = []

    def run(self) -> "None":
        """Runs the command's handler."""
        if self.filter():
            self.key_handler(
                KeyPressEvent(
                    key_processor_ref=weakref.ref(get_app().key_processor),
                    arg=None,
                    key_sequence=[],
                    previous_key_sequence=[],
                    is_repeat=False,
                )
            )

    @property
    def key_handler(self) -> "KeyHandlerCallable":
        """Returns a key handler for the command."""
        sig = signature(self.handler)

        if sig.parameters:
            # The handler already accepts a `KeyPressEvent` argument
            return cast("KeyHandlerCallable", self.handler)

        def _key_handler(event: "KeyPressEvent") -> "None":
            result = self.handler()
            # If the handler is a coroutine, create an asyncio task.
            if isawaitable(result):
                awaitable = result

                async def bg_task() -> None:
                    result = await awaitable
                    if result != NotImplemented:
                        event.app.invalidate()

                event.app.create_background_task(bg_task())
            elif result != NotImplemented:
                event.app.invalidate()

        return _key_handler

    def bind(self, key_bindings: "KeyBindingsBase", keys: "AnyKeys") -> "None":
        """Add the current commands to a set of key bindings.

        Args:
            key_bindings: The set of key bindings to bind to
            keys: Additional keys to bind to the command

        """
        for key in parse_keys(keys):
            self.keys.append(key)
            key_bindings.bindings.append(
                Binding(
                    key,
                    handler=self.key_handler,
                    filter=self.filter,
                    eager=self.eager,
                    is_global=self.is_global,
                    save_before=self.save_before,
                    record_in_macro=self.record_in_macro,
                )
            )

    def key_str(self) -> "str":
        """Return a string representing the first registered key-binding."""
        from euporie.core.key_binding.utils import format_keys

        if self.keys:
            return format_keys([self.keys[0]])[0]
        return ""

    @property
    def menu_handler(self) -> "Callable[[], None]":
        """Returns a menu handler for the command."""
        if isawaitable(self.handler):

            def _menu_handler() -> "None":
                task = self.handler()
                if task is not None:
                    get_app().create_background_task(task)

            return _menu_handler
        else:
            return cast("Callable[[], None]", self.handler)

    @property
    def menu(self) -> "MenuItem":
        """Returns a menu item for the command."""
        from euporie.core.widgets.menu import MenuItem

        if self._menu is None:
            self._menu = MenuItem.from_command(self)
        return self._menu


def add_cmd(**kwargs: "Any") -> "Callable":
    """Adds a command to the centralized command system."""

    def decorator(handler: "Callable") -> "Callable":
        cmd = Command(handler, **kwargs)
        commands[cmd.name] = cmd
        return handler

    return decorator


def get_cmd(name: "str") -> "Command":
    """Get a command from the centralized command system by name.

    Args:
        name: The name of the command to retrieve

    Returns:
        The requested command object

    Raises:
        KeyError: Raised if the named command is not found

    """
    try:
        return commands[name]
    except KeyError as e:
        raise KeyError("Unknown command: %r" % name) from e
