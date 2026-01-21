"""Define a command object for use in key-bindings, menus, and the command palette."""

from __future__ import annotations

import logging
import weakref
from functools import cached_property
from inspect import isawaitable, iscoroutinefunction, signature
from typing import TYPE_CHECKING, cast

from euporie.apptk.application.current import get_app

from euporie.apptk.filters import to_filter
from euporie.apptk.key_binding.key_bindings import Binding, KeyBindings
from euporie.apptk.key_binding.key_processor import KeyPressEvent
from euporie.apptk.key_binding.utils import format_keys, parse_keys

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any

    from euporie.apptk.filters import Filter, FilterOrBool
    from euporie.apptk.key_binding.key_bindings import (
        KeyBindingsBase,
        KeyHandlerCallable,
        NotImplementedOrNone,
    )
    from euporie.apptk.keys import AnyKeys

    CommandHandlerNoArgs = Callable[
        ..., Coroutine[Any, Any, None] | NotImplementedOrNone
    ]
    CommandHandlerArgs = Callable[
        [KeyPressEvent], Coroutine[Any, Any, None] | NotImplementedOrNone
    ]
    CommandHandler = CommandHandlerNoArgs | CommandHandlerArgs

log = logging.getLogger(__name__)


COMMANDS: dict[str, Command] = {}


def parse_args(arg: str) -> list[Any]:
    """Parse a command argument string into a list of values.

    Args:
        arg: The argument string to parse

    Returns:
        A list of parsed values, with strings for items that couldn't be evaluated
    """
    if not arg:
        return []

    import ast

    result = []
    for item in arg.split():
        try:
            # Safely evaluate string as a Python literal
            new_value = ast.literal_eval(item)
        except (ValueError, SyntaxError):
            # Keep as string if evaluation fails
            result.append(item)
        else:
            if type(new_value) is str:
                result.append(item)
            else:
                result.append(new_value)
    return result


class _UNSET: ...


UNSET = _UNSET()


class Command:
    """Wrap a function so it can be used as a key-binding or a menu item."""

    def __init__(
        self,
        handler: CommandHandler,
        *,
        keys: list[AnyKeys] | None = None,
        filter: FilterOrBool = True,
        hidden: FilterOrBool = False,
        name: str | None = None,
        aliases: list[str] | None = None,
        title: str | None = None,
        menu_title: str | None = None,
        description: str | None = None,
        icon: str = " ",
        style: str = "",
        toggled: Filter | None = None,
        eager: FilterOrBool = False,
        is_global: FilterOrBool = False,
        save_before: Callable[[KeyPressEvent], bool] = (lambda event: True),
        record_in_macro: FilterOrBool = True,
    ) -> None:
        """Create a new instance of a command.

        Similar to a :py:`prompt_toolkit.key_binding.bindings.named_commands`, but also
         collection of :py:class:`prompt_toolkit.key_binding.key_bindings:Bindings`.

        Args:
            handler: The callable to run when the command is triggered
            keys: List of key bindings to associate with the command
            filter: The condition under which the command is allowed to run
            hidden: The condition under the command is visible to the user
            name: The name of the command, for accessing the command from the registry
            aliases: List of additional names for the command
            title: The title of the command for display
            menu_title: The title to display in menus if different
            description: The description of the command to explain it's function
            icon: A unicode character representing the command
            style: A style associated with this command
            toggled: The toggle state of this command If this command toggles something
            eager: When True, ignore potential longer matches for this key binding
            is_global: Make this a global (always active) binding
            save_before: Determines if the buffer should be saved before running
            record_in_macro: Whether these key bindings should be recorded in macros

        """
        self.update(
            handler=handler,
            keys=keys,
            filter=filter,
            hidden=hidden,
            name=name,
            aliases=aliases,
            title=title,
            menu_title=menu_title,
            description=description,
            icon=icon,
            style=style,
            toggled=toggled,
            eager=eager,
            is_global=is_global,
            save_before=save_before,
            record_in_macro=record_in_macro,
        )

    def update(
        self,
        handler: CommandHandler | _UNSET = UNSET,
        keys: list[AnyKeys] | None | _UNSET = UNSET,
        filter: FilterOrBool | _UNSET = UNSET,
        hidden: FilterOrBool | _UNSET = UNSET,
        name: str | None | _UNSET = UNSET,
        aliases: list[str] | None | _UNSET = UNSET,
        title: str | None | _UNSET = UNSET,
        menu_title: str | None | _UNSET = UNSET,
        description: str | None | _UNSET = UNSET,
        icon: str | _UNSET = UNSET,
        style: str | _UNSET = UNSET,
        toggled: Filter | None | _UNSET = UNSET,
        eager: FilterOrBool | _UNSET = UNSET,
        is_global: FilterOrBool | _UNSET = UNSET,
        save_before: Callable[[KeyPressEvent], bool] | _UNSET = UNSET,
        record_in_macro: FilterOrBool | _UNSET = UNSET,
    ) -> None:
        """Update attributes on Command."""
        if handler is not UNSET:
            self.handler = handler
        if keys is not UNSET:
            self.keys = parse_keys(keys or [])
        if aliases is not UNSET:
            self.aliases = aliases or []
        if filter is not UNSET:
            self.filter = to_filter(filter)
        if hidden is not UNSET:
            self.hidden = to_filter(hidden)
        if name is not UNSET:
            if name is None:
                name = handler.__name__.strip("_").replace("_", "-")
            self.name = name
        if title is not UNSET:
            if title is None:
                title = name.capitalize().replace("-", " ")
            self.title = title
            self.menu_title = menu_title or title
        if description is not UNSET:
            if description is None:
                # Use the first line of the docstring as the command description
                if handler.__doc__:
                    description = (
                        "".join(handler.__doc__.strip().split("\n")).split(".")[0] + "."
                    )
                else:
                    description = title or name.capitalize()
            self.description = description
        if icon is not UNSET:
            self.icon = icon
        if style is not UNSET:
            self.style = style
        if toggled is not UNSET:
            self.toggled = toggled
        if eager is not UNSET:
            self.eager = to_filter(eager)
        if is_global is not UNSET:
            self.is_global = to_filter(is_global)
        if save_before is not UNSET:
            self.save_before = save_before
        if record_in_macro is not UNSET:
            self.record_in_macro = to_filter(record_in_macro)

    def run(self, arg: str = "") -> None:
        """Run the command's handler."""
        if not self.filter():
            return
        app = get_app()
        result = self.key_handler(
            KeyPressEvent(
                key_processor_ref=weakref.ref(app.key_processor),
                arg=None,
                key_sequence=[],
                previous_key_sequence=[],
                is_repeat=False,
            ),
            *parse_args(arg),
        )
        if isawaitable(result):

            async def _wait_and_invalidate() -> None:
                if await result is None:
                    app.invalidate()

            app.create_background_task(_wait_and_invalidate())
        elif result is None:
            app.invalidate()

    @cached_property
    def key_handler(self) -> KeyHandlerCallable:
        """Return a key handler for the command."""
        sig = signature(self.handler)
        params = list(sig.parameters.keys())

        # Handler already accepts event as first parameter
        if params and params[0] == "event":
            return self.handler  # type: ignore[return-value]

        # Wrap handler to accept event parameter
        if iscoroutinefunction(self.handler):

            async def _wrapper(
                event: KeyPressEvent, *args: Any
            ) -> NotImplementedOrNone:
                return await self.handler(*args)

            return _wrapper

        def _wrapper(event: KeyPressEvent, *args: Any) -> NotImplementedOrNone:
            return self.handler(*args)

        return _wrapper

    def __call__(self, event: KeyPressEvent, *args: Any) -> NotImplementedOrNone:
        """Call the command's key handler.

        Args:
            event: The key press event that triggered the command.
            *args: Additional arguments to pass to the handler.

        Returns:
            The result of the key handler, or NotImplemented.
        """
        return self.key_handler(event, *args)

    call = __call__

    def add_keys(self, *keys: AnyKeys) -> None:
        """Add a keyboard shortcut to this commend."""
        for key in parse_keys(keys):
            self.keys.add(key)

    def bind(self, key_bindings: KeyBindingsBase, keys=None) -> None:
        """Add the current commands to a set of key bindings.

        Args:
            key_bindings: The set of key bindings to bind to
            keys: Additional keys to bind to the command

        """
        for key in self.keys:
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
        keys = get_app().key_processor._bindings.handler_keys.get(self.key_handler, [])
        if keys:
            return format_keys(keys[0])[0]
        # if self.bindings:
        #     return format_keys(self.bindings[0].keys)[0]
        return ""


def add_cmd(
    *,
    keys: list[AnyKeys] | None = None,
    filter: FilterOrBool = True,
    hidden: FilterOrBool = False,
    name: str | None = None,
    aliases: list[str] | None = None,
    title: str | None = None,
    menu_title: str | None = None,
    description: str | None = None,
    icon: str = " ",
    style: str = "",
    toggled: Filter | None = None,
    eager: FilterOrBool = False,
    is_global: FilterOrBool = False,
    save_before: Callable[[KeyPressEvent], bool] = (lambda event: True),
    record_in_macro: FilterOrBool = True,
) -> Callable:
    """Add a command to the centralized command system."""

    def decorator(handler: Callable) -> Callable:
        cmd = Command(
            handler,
            keys=keys,
            filter=filter,
            hidden=hidden,
            name=name,
            aliases=aliases,
            title=title,
            menu_title=menu_title,
            description=description,
            icon=icon,
            style=style,
            toggled=toggled,
            eager=eager,
            is_global=is_global,
            save_before=save_before,
            record_in_macro=record_in_macro,
        )
        COMMANDS[cmd.name] = cmd
        for alias in cmd.aliases:
            COMMANDS[alias] = cmd
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
        return COMMANDS[name]
    except KeyError as e:
        raise KeyError(f"Unknown command: {name}") from e


def commands_from_key_bindings(
    key_bindings: KeyBindingsBase,
    prefix: str = "",
    hidden: FilterOrBool = True,
) -> KeyBindings:
    """Convert a KeyBindingsBase into Commands and return a new KeyBindings.

    This function takes existing prompt_toolkit key bindings and converts them
    into Command objects, registering them in the global commands registry.
    It returns a new KeyBindings object where the bindings are loaded through
    the command system, allowing for future key override capabilities.

    Args:
        key_bindings: The key bindings to convert
        prefix: A prefix to add to command names to avoid collisions
        hidden: Whether the commands should be hidden from the command palette

    Returns:
        A new KeyBindings object with bindings loaded through the command system
    """
    seen_handlers: dict[int, Command] = {}  # Track handlers we've already processed
    new_key_bindings = KeyBindings()

    for binding in key_bindings.bindings:
        handler = binding.handler
        handler_id = id(handler)

        # Check if we've already created a command for this handler
        if handler_id in seen_handlers:
            # Add the keys to the existing command and create a new binding
            existing_cmd = seen_handlers[handler_id]
            existing_cmd.keys.update(parse_keys(binding.keys))
            # Add binding through the command system
            new_key_bindings.bindings.append(
                Binding(
                    keys=binding.keys,
                    handler=existing_cmd.key_handler,
                    filter=binding.filter,
                    eager=binding.eager,
                    is_global=binding.is_global,
                    save_before=binding.save_before,
                    record_in_macro=binding.record_in_macro,
                )
            )
            continue

        # Generate a name from the handler function
        handler_name = getattr(handler, "__name__", "")
        if not handler_name or handler_name in ("<lambda>", "_"):
            # Use keys as part of the name for anonymous handlers
            key_str = "-".join(
                str(k.value if hasattr(k, "value") else k) for k in binding.keys
            )
            handler_name = f"key-{key_str}"

        name = handler_name.strip("_").replace("_", "-")
        if prefix:
            name = f"{prefix}-{name}"

        # Ensure unique name by appending a counter if needed
        base_name = name
        counter = 1
        while name in COMMANDS:
            name = f"{base_name}-{counter}"
            counter += 1

        cmd = Command(
            handler=handler,
            keys=[binding.keys],
            filter=binding.filter,
            hidden=hidden,
            name=name,
            eager=binding.eager,
            is_global=binding.is_global,
            save_before=binding.save_before,
            record_in_macro=binding.record_in_macro,
        )

        COMMANDS[cmd.name] = cmd
        seen_handlers[handler_id] = cmd

        # Add binding through the command system
        new_key_bindings.bindings.append(
            Binding(
                keys=binding.keys,
                handler=cmd.key_handler,
                filter=binding.filter,
                eager=binding.eager,
                is_global=binding.is_global,
                save_before=binding.save_before,
                record_in_macro=binding.record_in_macro,
            )
        )

    return new_key_bindings
