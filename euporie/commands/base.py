"""Defines a command object for use in key-bindings, menus, and the command palette."""
import logging
from inspect import isawaitable, signature
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import to_filter
from prompt_toolkit.key_binding.key_bindings import Binding, _parse_key

from euporie.keys import Keys
from euporie.menu.item import MenuItem

if TYPE_CHECKING:
    from typing import (
        Any,
        Awaitable,
        Callable,
        Dict,
        List,
        Optional,
        Sequence,
        Tuple,
        Union,
    )

    from prompt_toolkit.filters import Filter, FilterOrBool
    from prompt_toolkit.key_binding import KeyBindingsBase, KeyPressEvent
    from prompt_toolkit.key_binding.key_bindings import KeyHandlerCallable

    AnyKey = Union[Tuple[Union[Keys, str], ...], Union[Keys, str]]
    AnyKeys = Union[List[AnyKey], AnyKey]

log = logging.getLogger(__name__)


commands: "Dict[str, Command]" = {}


class Command:
    """Wraps a function so it can be used as a key-binding or a menu item."""

    def __init__(
        self,
        handler: "Callable[..., Optional[Awaitable[Any]]]",
        *,
        filter: "FilterOrBool" = True,
        name: "Optional[str]" = None,
        title: "Optional[str]" = None,
        description: "Optional[str]" = None,
        group: "Optional[str]" = None,
        toggled: "Optional[Filter]" = None,
        keys: "Optional[AnyKeys]" = None,
        eager: "FilterOrBool" = False,
        is_global: "FilterOrBool" = False,
        save_before: "Callable[[KeyPressEvent], bool]" = (lambda event: True),
        record_in_macro: "FilterOrBool" = True,
    ):
        """Creates a new instance of a command.

        Args:
            handler: The callable to run when the command is triggers
            filter: The condition under which the command is allowed to run
            name: The name of the command, for accessing the command from the registry
            title: The title of the command for display in menu and the command palette
            description: The discription of the command to explain it's function
            group: The group to which this command belongs
            toggled: The toggle state of this command If this command toggles something
            keys: The default keys to which this command should be bound
            eager: When True, ignore potential longer matches for this key binding
            is_global: Make this a global (always active) binding
            save_before: Determines if the buffer should be saved before running
            record_in_macro: Whether these key bindings should be recorded in macros

        """
        self.handler = handler
        self.filter = to_filter(filter)
        if name is None:
            name = handler.__name__.replace("_", "-")
        self.name = name
        if title is None:
            title = name.capitalize().replace("-", " ")
        self.title = title
        if description is None:
            # Use the first line of the docstring as the command description
            if handler.__doc__:
                description = handler.__doc__.split("\n")[0]
            else:
                description = title
        self.description = description
        self.group = group

        self.toggled = toggled
        self._menu: "Optional[MenuItem]" = None

        self.keys: "List[Tuple[Union[str, Keys], ...]]" = []
        self.add_keys(keys)
        self.eager = to_filter(eager)
        self.is_global = to_filter(is_global)
        self.save_before = save_before
        self.record_in_macro = to_filter(record_in_macro)

        self.selected_item = 0
        self.children: "Sequence[MenuItem]" = []

    def bind(
        self, key_bindings: "KeyBindingsBase", keys: "Optional[AnyKeys]" = None
    ) -> "None":
        """Add the current commands to a set of key bindings.

        Args:
            key_bindings: The set of key bindings to bind to
            keys: Additional keys to bind to the command

        """
        self.add_keys(keys)
        for binding in self.key_bindings:
            key_bindings.bindings.append(binding)

    def add_keys(self, keys: "Optional[AnyKeys]") -> "Command":
        """Adds keyboard shortcuts to the current command."""
        if keys is None:
            keys = []
        if not isinstance(keys, list):
            keys = [keys]
        for key in keys:
            if isinstance(key, Keys):
                self.keys.append((key,))
            elif isinstance(key, tuple):
                self.keys.append(tuple(_parse_key(k) for k in key))
            else:
                self.keys.append((_parse_key(key),))
        return self

    @property
    def key_bindings(self) -> "Sequence[Binding]":
        """Returns a list of key-bindings given to the current command."""
        return [
            Binding(
                key,
                handler=self.key_handler,
                filter=self.filter,
                eager=self.eager,
                is_global=self.is_global,
                save_before=self.save_before,
                record_in_macro=self.record_in_macro,
            )
            for key in self.keys
        ]

    @property
    def key_handler(self) -> "KeyHandlerCallable":
        """Returns a key hander for the command."""
        sig = signature(self.handler)

        if sig.parameters:
            # The handler already accepts a `KeyPressEvent` argument
            return cast("KeyHandlerCallable", self.handler)

        if isawaitable(self.handler):

            async def _key_handler_async(event: "KeyPressEvent") -> "None":
                await cast("Awaitable", self.handler())

            return _key_handler_async
        else:

            def _key_handler(event: "KeyPressEvent") -> "None":
                self.handler()

            return _key_handler

    @property
    def menu_handler(self) -> "Callable[[], None]":
        """Returns a menu hander for the command."""
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
        if self._menu is None:
            self._menu = MenuItem.from_command(self)
        return self._menu


def add(**kwargs: "Any") -> "Callable":
    """Adds a command to the centralized command system."""

    def decorator(handler: "Callable") -> "Callable":
        cmd = Command(handler, **kwargs)
        commands[cmd.name] = cmd
        return handler

    return decorator


def get(name: "str") -> "Command":
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