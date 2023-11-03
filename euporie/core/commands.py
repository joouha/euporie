"""Define a command object for use in key-bindings, menus, and the command palette."""

from __future__ import annotations

import logging
import weakref
from inspect import isawaitable, iscoroutinefunction, signature
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import to_filter
from prompt_toolkit.key_binding.key_bindings import Binding
from prompt_toolkit.key_binding.key_processor import KeyPressEvent

from euporie.core.key_binding.utils import parse_keys

if TYPE_CHECKING:
    from typing import Any, Callable, Coroutine

    from prompt_toolkit.filters import Filter, FilterOrBool
    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        KeyHandlerCallable,
        NotImplementedOrNone,
    )

    from euporie.core.keys import Keys
    from euporie.core.widgets.menu import MenuItem

    AnyKey = tuple[Keys | str, ...] | Keys | str
    AnyKeys = list[AnyKey] | AnyKey
    CommandHandlerNoArgs = Callable[
        ..., Coroutine[Any, Any, None] | NotImplementedOrNone
    ]
    CommandHandlerArgs = Callable[
        [KeyPressEvent], Coroutine[Any, Any, None] | NotImplementedOrNone
    ]
    CommandHandler = CommandHandlerNoArgs | CommandHandlerArgs

log = logging.getLogger(__name__)


class Command:
    """Wrap a function so it can be used as a key-binding or a menu item."""

    def __init__(
        self,
        handler: CommandHandler,
        *,
        filter: FilterOrBool = True,
        hidden: FilterOrBool = False,
        name: str | None = None,
        title: str | None = None,
        menu_title: str | None = None,
        description: str | None = None,
        toggled: Filter | None = None,
        eager: FilterOrBool = False,
        is_global: FilterOrBool = False,
        save_before: Callable[[KeyPressEvent], bool] = (lambda event: True),
        record_in_macro: FilterOrBool = True,
    ) -> None:
        """Create a new instance of a command.

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
        self._menu: MenuItem | None = None

        self.eager = to_filter(eager)
        self.is_global = to_filter(is_global)
        self.save_before = save_before
        self.record_in_macro = to_filter(record_in_macro)

        self.keys: list[tuple[str | Keys, ...]] = []

    def run(self) -> None:
        """Run the command's handler."""
        if self.filter():
            app = get_app()
            result = self.key_handler(
                KeyPressEvent(
                    key_processor_ref=weakref.ref(app.key_processor),
                    arg=None,
                    key_sequence=[],
                    previous_key_sequence=[],
                    is_repeat=False,
                )
            )
            if isawaitable(result):

                async def _wait_and_invalidate() -> None:
                    assert isawaitable(result)
                    output = await result
                    if output is None:
                        app.invalidate()

                app.create_background_task(_wait_and_invalidate())
            elif result is None:
                app.invalidate()

    @property
    def key_handler(self) -> KeyHandlerCallable:
        """Return a key handler for the command."""
        handler = self.handler
        sig = signature(handler)

        if sig.parameters:
            # The handler already accepts a `KeyPressEvent` argument
            return cast("KeyHandlerCallable", handler)

        if iscoroutinefunction(handler):

            async def _key_handler_async(event: KeyPressEvent) -> NotImplementedOrNone:
                result = cast("CommandHandlerNoArgs", handler)()
                assert isawaitable(result)
                return await result

            return _key_handler_async

        else:

            def _key_handler(event: KeyPressEvent) -> NotImplementedOrNone:
                return cast("CommandHandlerNoArgs", handler)()

            return _key_handler

    def bind(self, key_bindings: KeyBindingsBase, keys: AnyKeys) -> None:
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

    def key_str(self) -> str:
        """Return a string representing the first registered key-binding."""
        from euporie.core.key_binding.utils import format_keys

        if self.keys:
            return format_keys([self.keys[0]])[0]
        return ""

    @property
    def menu_handler(self) -> Callable[[], None]:
        """Return a menu handler for the command."""
        handler = self.handler
        if isawaitable(handler):

            def _menu_handler() -> None:
                task = cast("CommandHandlerNoArgs", handler)()
                task = cast("Coroutine[Any, Any, None]", task)
                if task is not None:
                    get_app().create_background_task(task)

            return _menu_handler
        else:
            return cast("Callable[[], None]", handler)

    @property
    def menu(self) -> MenuItem:
        """Return a menu item for the command."""
        from euporie.core.widgets.menu import MenuItem

        if self._menu is None:
            self._menu = MenuItem.from_command(self)
        return self._menu


commands: dict[str, Command] = {}


def add_cmd(**kwargs: Any) -> Callable:
    """Add a command to the centralized command system."""

    def decorator(handler: Callable) -> Callable:
        cmd = Command(handler, **kwargs)
        commands[cmd.name] = cmd
        return handler

    return decorator


def get_cmd(name: str) -> Command:
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
