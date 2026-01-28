"""Define a command object for use in key-bindings, menus, and the command palette."""

from __future__ import annotations

import logging
import weakref
from functools import cached_property
from inspect import isawaitable, iscoroutinefunction, signature
from typing import TYPE_CHECKING

from euporie.apptk.application.current import get_app

from euporie.apptk.filters import to_filter
from euporie.apptk.key_binding.key_bindings import Binding, KeyBindings
from euporie.apptk.key_binding.key_processor import KeyPressEvent
from euporie.apptk.key_binding.utils import format_keys, parse_keys

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypedDict, Unpack

    from euporie.apptk.filters import Filter, FilterOrBool
    from euporie.apptk.key_binding.key_bindings import (
        KeyBindingsBase,
        KeyHandlerCallable,
        NotImplementedOrNone,
    )
    from euporie.apptk.keys import AnyKeys, Keys

    CommandHandlerNoArgs = Callable[
        ..., Coroutine[Any, Any, NotImplementedOrNone] | NotImplementedOrNone
    ]
    CommandHandlerArgs = Callable[
        [KeyPressEvent],
        Coroutine[Any, Any, NotImplementedOrNone] | NotImplementedOrNone,
    ]
    CommandHandler = CommandHandlerNoArgs | CommandHandlerArgs

    class BindingArgs(TypedDict, total=False):
        """Type of partial :py:class:`Binding` arguments."""

        keys: tuple[Keys | str, ...]
        filter: FilterOrBool
        eager: FilterOrBool
        is_global: FilterOrBool
        save_before: Callable[[KeyPressEvent], bool]
        record_in_macro: FilterOrBool

    class CommandUpdateArgs(TypedDict, total=False):
        """Typing of :py:method:`Command.update` parameters."""

        name: str
        group: str
        aliases: list[str]
        title: str
        menu_title: str
        description: str
        icon: str
        style: str
        hidden: FilterOrBool
        toggled: FilterOrBool | None

        filter: FilterOrBool
        eager: FilterOrBool
        is_global: FilterOrBool
        save_before: Callable[[KeyPressEvent], bool]
        record_in_macro: FilterOrBool


log = logging.getLogger(__name__)

# Registry for Commands by name
COMMANDS: dict[str, Command] = {}
# Registry mapping handler id to Command instance for deduplication
_HANDLER_REGISTRY: dict[int, Command] = {}


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


class Command:
    """Wrap a function so it can be used as a key-binding or a menu item."""

    def __new__(
        cls,
        handler: CommandHandler,
        *,
        name: str | None = None,
        aliases: list[str] | None = None,
        title: str | None = None,
        menu_title: str | None = None,
        description: str | None = None,
        group: str = "",
        icon: str = " ",
        style: str = "",
        hidden: FilterOrBool = False,
        toggled: FilterOrBool | None = None,
        filter: FilterOrBool = True,
        eager: FilterOrBool = False,
        is_global: FilterOrBool = False,
        save_before: Callable[[KeyPressEvent], bool] = (lambda event: True),
        record_in_macro: FilterOrBool = True,
        keys: list[AnyKeys] | None = None,
        bindings: list[Binding] | None = None,
    ) -> Command:
        """Return existing Command for handler or create a new one.

        Args:
            handler: The callable to run when the command is triggered
            name: The name of the command, for accessing the command from the registry
            aliases: List of additional names for the command
            title: The title of the command for display
            menu_title: The title to display in menus if different
            description: The description of the command to explain it's function
            icon: A unicode character representing the command
            style: A style associated with this command
            hidden: The condition under the command is visible to the user
            toggled: The toggle state of this command If this command toggles something
            filter: The condition under which the command is allowed to run
            eager: When True, ignore potential longer matches for this key binding
            is_global: Make this a global (always active) binding
            save_before: Determines if the buffer should be saved before running
            record_in_macro: Whether these key bindings should be recorded in macros
            keys: List of key bindings to associate with the command using default binding parameters
            bindings: A list of existing key-bindings to associate with this command

        Returns:
            An existing Command if handler was already registered, otherwise a new one.
        """
        handler_id = id(handler)

        # Check if command already exists for this handler
        if handler_id in _HANDLER_REGISTRY:
            existing = _HANDLER_REGISTRY[handler_id]
            # Update existing command with new parameters
            existing.update(
                name=name,
                aliases=aliases,
                title=title,
                menu_title=menu_title,
                description=description,
                icon=icon,
                style=style,
                hidden=hidden,
                toggled=toggled,
                filter=filter,
                eager=eager,
                is_global=is_global,
                save_before=save_before,
                record_in_macro=record_in_macro,
            )
            return existing

        # Create new instance
        instance = super().__new__(cls)
        _HANDLER_REGISTRY[handler_id] = instance
        return instance

    def __init__(
        self,
        handler: CommandHandler,
        *,
        name: str | None = None,
        aliases: list[str] | None = None,
        title: str | None = None,
        menu_title: str | None = None,
        description: str | None = None,
        icon: str = " ",
        style: str = "",
        hidden: FilterOrBool = False,
        toggled: FilterOrBool | None = None,
        # Default binding parameters
        filter: FilterOrBool = True,
        eager: FilterOrBool = False,
        is_global: FilterOrBool = False,
        save_before: Callable[[KeyPressEvent], bool] = (lambda event: True),
        record_in_macro: FilterOrBool = True,
        # Kwys or bindings
        bindings: list[BindingArgs] | None = None,
        keys: list[AnyKeys] | None = None,
    ) -> None:
        """Create a new instance of a command.

        Similar to a :py:`prompt_toolkit.key_binding.bindings.named_commands`, but also
         collection of :py:class:`prompt_toolkit.key_binding.key_bindings:Bindings`.

        Args:
            handler: The callable to run when the command is triggered
            name: The name of the command, for accessing the command from the registry
            aliases: List of additional names for the command
            title: The title of the command for display
            menu_title: The title to display in menus if different
            description: The description of the command to explain it's function
            icon: A unicode character representing the command
            style: A style associated with this command
            hidden: The condition under the command is visible to the user
            toggled: The toggle state of this command If this command toggles something
            filter: The condition under which the command is allowed to run
            eager: When True, ignore potential longer matches for this key binding
            is_global: Make this a global (always active) binding
            save_before: Determines if the buffer should be saved before running
            record_in_macro: Whether these key bindings should be recorded in macros
            bindings: A list of arguments for key-bindings
            keys: List of key bindings to associate with the command

        """
        # Register handler
        self.handler = handler
        # Set parameters
        self.update(
            name=name,
            title=title,
            menu_title=menu_title,
            description=description,
            icon=icon,
            style=style,
            hidden=hidden,
            toggled=toggled,
            filter=filter,
            eager=eager,
            is_global=is_global,
            save_before=save_before,
            record_in_macro=record_in_macro,
        )
        # Add to command aliases registry
        self.add_alias(*aliases or [])
        # Add passed keys/bindings
        self.bindings: list[Binding] = []
        for args in bindings or []:
            self.add_keys(**args)
        if keys:
            self.add_keys(
                keys,
                filter=self._default_filter,
                eager=self._default_eager,
                is_global=self._default_is_global,
                save_before=self._default_save_before,
                record_in_macro=self._default_record_in_macro,
            )

    def update(self, **kwargs: Unpack[CommandUpdateArgs]) -> Command:
        """Set command attributes."""
        if "name" in kwargs:
            self.name = kwargs["name"]
        if "title" in kwargs:
            self.title = kwargs["title"]
        if "menu_title" in kwargs:
            self.menu_title = kwargs["menu_title"]
        if "description" in kwargs:
            self.description = kwargs["description"]
        if "icon" in kwargs:
            self.icon = kwargs["icon"]
        if "style" in kwargs:
            self.style = kwargs["style"]
        if "hidden" in kwargs:
            self.hidden = kwargs["hidden"]
        if "toggled" in kwargs:
            self.toggled = kwargs["toggled"]

        if "filter" in kwargs:
            self._default_filter = to_filter(kwargs["filter"])
        if "eager" in kwargs:
            self._default_eager = to_filter(kwargs["eager"])
        if "is_global" in kwargs:
            self._default_is_global = to_filter(kwargs["is_global"])
        if "save_before" in kwargs:
            self._default_save_before = kwargs["save_before"]
        if "record_in_macro" in kwargs:
            self._default_record_in_macro = to_filter(kwargs["record_in_macro"])

        return self

    @property
    def name(self) -> str:
        """The command's name."""
        return self._name

    @name.setter
    def name(self, value: str | None) -> None:
        if value is None:
            value = self.handler.__name__.strip("_").replace("_", "-")
        if hasattr(self, "_name") and self._name != value and self._name in COMMANDS:
            del COMMANDS[self._name]
        COMMANDS[value] = self
        self._name = value

    @property
    def title(self) -> str:
        """The title of the command for display."""
        return self._title

    @title.setter
    def title(self, value: str | None) -> None:
        if value is None:
            value = self.name.capitalize().replace("-", " ")
        self._title = value

    @property
    def menu_title(self) -> str:
        """Title of the command for display in menus."""
        return self._menu_title

    @menu_title.setter
    def menu_title(self, value: str | None) -> None:
        if value is None:
            value = self.title
        self._menu_title = value

    @property
    def description(self) -> str:
        """The description of the command to explain it's function."""
        return self._description

    @description.setter
    def description(self, value: str | None) -> None:
        if value is None:
            if self.handler.__doc__:
                value = (
                    "".join(self.handler.__doc__.strip().split("\n")).split(".")[0]
                    + "."
                )
            else:
                value = self.title or self.name.capitalize()
        self._description = value

    def add_alias(self, *aliases: str) -> Command:
        """Add additional aliases to the command."""
        for alias in aliases:
            COMMANDS[alias] = self
        return self

    @property
    def aliases(self) -> list[str]:
        """Return a list of known aliases of this command."""
        return [k for k, v in COMMANDS.items() if v is self]

    @property
    def hidden(self) -> Filter:
        """Condition under the command is visible to the user."""
        return self._hidden

    @hidden.setter
    def hidden(self, value: FilterOrBool) -> None:
        self._hidden = to_filter(value)

    @property
    def toggled(self) -> Filter:
        """Condition under the command is visible to the user."""
        return self._toggled

    @toggled.setter
    def toggled(self, value: FilterOrBool | None) -> None:
        self._toggled = None if value is None else to_filter(value)

    @property
    def filter(self) -> Filter:
        """Return the combined filter from all bindings, or the default filter."""
        return self._default_filter

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

    def add_keys(
        self,
        keys: AnyKeys,
        *,
        filter: FilterOrBool | None = None,
        eager: FilterOrBool | None = None,
        is_global: FilterOrBool | None = None,
        save_before: Callable[[KeyPressEvent], bool] | None = None,
        record_in_macro: FilterOrBool | None = None,
    ) -> None:
        """Add keyboard shortcuts to this command.

        Args:
            keys: Key sequences to bind to this command
            filter: Condition for these bindings (uses default if not provided)
            eager: Eager setting for these bindings (uses default if not provided)
            is_global: Global setting for these bindings (uses default if not provided)
            save_before: Save before setting (uses default if not provided)
            record_in_macro: Macro recording setting (uses default if not provided)
        """
        handler = self.key_handler
        if filter is None:
            filter = self._default_filter
        if eager is None:
            eager = self._default_eager
        if is_global is None:
            is_global = self._default_is_global
        if save_before is None:
            save_before = self._default_save_before
        if record_in_macro is None:
            record_in_macro = self._default_record_in_macro

        for key_seq in parse_keys(keys):
            self.bindings.append(
                Binding(
                    keys=key_seq,
                    handler=handler,
                    filter=filter,
                    eager=eager,
                    is_global=is_global,
                    save_before=save_before,
                    record_in_macro=record_in_macro,
                )
            )

    def bind(self, key_bindings: KeyBindingsBase) -> None:
        """Add the current command's bindings to a set of key bindings.

        Args:
            key_bindings: The set of key bindings to bind to
        """
        for binding in self.bindings:
            key_bindings.bindings.append(binding)

    def key_str(self) -> str:
        """Return a string representing the first registered key-binding."""
        # keys = get_app().key_processor._bindings.handler_keys.get(self.key_handler, [])
        # if keys:
        #     return format_keys(keys[0])[0]
        if self.bindings:
            return format_keys(list(self.bindings[0].keys))[0]
        return ""


def add_cmd(
    *,
    name: str | None = None,
    aliases: list[str] | None = None,
    title: str | None = None,
    menu_title: str | None = None,
    description: str | None = None,
    icon: str = " ",
    style: str = "",
    hidden: FilterOrBool = False,
    toggled: FilterOrBool | None = None,
    # Default binding parameters
    filter: FilterOrBool = True,
    eager: FilterOrBool = False,
    is_global: FilterOrBool = False,
    save_before: Callable[[KeyPressEvent], bool] = (lambda event: True),
    record_in_macro: FilterOrBool = True,
    bindings: list[Binding] | None = None,
    keys: list[AnyKeys] | None = None,
) -> Callable:
    """Add a command to the centralized command system.

    If a command with the same handler already exists, this updates the existing
    command with the new parameters and adds any new key bindings.
    """

    def decorator(handler: Callable) -> Callable:
        # Command.__new__ handles deduplication by handler
        # Command.update handles registry management
        Command(
            handler,
            name=name,
            aliases=aliases,
            title=title,
            menu_title=menu_title,
            description=description,
            icon=icon,
            style=style,
            hidden=hidden,
            toggled=toggled,
            filter=filter,
            eager=eager,
            is_global=is_global,
            save_before=save_before,
            record_in_macro=record_in_macro,
            bindings=bindings,
            keys=keys,
        )
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
    new_key_bindings = KeyBindings()

    for binding in key_bindings.bindings:
        handler = binding.handler
        handler_id = id(handler)

        # Check if command already exists for this handler (via _HANDLER_REGISTRY)
        if handler_id in _HANDLER_REGISTRY:
            # Add the keys to the existing command
            existing_cmd = _HANDLER_REGISTRY[handler_id]
            existing_cmd.add_keys(
                binding.keys,
                filter=binding.filter,
                eager=binding.eager,
                is_global=binding.is_global,
                save_before=binding.save_before,
                record_in_macro=binding.record_in_macro,
            )
            # Add the new binding to the key bindings
            new_key_bindings.bindings.append(existing_cmd.bindings[-1])
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

        # Command.__new__ handles deduplication, update handles registry
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

        # Add the binding from the command to the key bindings
        new_key_bindings.bindings.extend(cmd.bindings)

    return new_key_bindings
