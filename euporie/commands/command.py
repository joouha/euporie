# -*- coding: utf-8 -*-
import logging
from inspect import isawaitable, signature

from prompt_toolkit.buffer import indent, unindent
from prompt_toolkit.filters import to_filter
from prompt_toolkit.key_binding.key_bindings import (
    Binding,
    KeyBindings,
    _parse_key,
    key_binding,
)
from prompt_toolkit.keys import Keys

log = logging.getLogger(__name__)


commands: "dict[str, Command]" = {}


class Command:
    """Wraps a function so it can be used as a key-binding or a menu item."""

    def __init__(
        self,
        handler: "Callable[[], None]",
        *,
        filter: "FilterOrBool" = True,
        name: "Optional[str]" = None,
        title: "Optional[str]" = None,
        description: "Optional[str]" = None,
        group: "Optional[str]" = None,
        menu: "bool" = False,
        menu_idx: "int" = 0,
        status: "Optional[Filter]" = None,
        keys: "Optional[list[Union[Keys, str]], tuple[Union[Keys, str], ...]]" = None,
        key_repr: "Optional[str]" = None,
        eager: "FilterOrBool" = False,
        is_global: "FilterOrBool" = False,
        save_before: "Callable[[KeyPressEvent], bool]" = (lambda event: True),
        record_in_macro: "FilterOrBool" = True,
    ):
        self._handler = handler
        self.filter = to_filter(filter)
        if name is None:
            name = handler.__name__.replace("_", "-")
        self.name = name
        if title is None:
            title = name.title().replace("-", " ")
        self.title = title
        if description is None:
            # Use the first line of the docstring as the command description
            if handler.__doc__:
                description = handler.__doc__.split("\n")[0]
            else:
                description = title
        self.description = description
        self.group = group
        self.menu = menu
        self.menu_idx = menu_idx
        self.keys = []
        self.eager = to_filter(eager)
        self.is_global = to_filter(is_global)
        self.save_before = save_before
        self.record_in_macro = to_filter(record_in_macro)

        self.add_keys(keys)

        self.selected_item = 0

    def bind(self, key_bindings, keys):
        self.add_keys(keys)
        for binding in self.key_bindings:
            key_bindings.bindings.append(binding)

    def add_keys(self, keys):
        if keys is None:
            keys = []
        if not isinstance(keys, list):
            keys = [keys]
        for key in keys:
            if isinstance(key, tuple):
                self.keys.append(tuple(_parse_key(k) for k in key))
            else:
                self.keys.append((_parse_key(key),))
        return self

    @property
    def key_bindings(self):
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
    def key_handler(self) -> "Callable":
        sig = signature(self._handler)

        if sig.parameters:
            # The handler already accepts a `KeyPressEvent` argument
            return self._handler

        if isawaitable(self._handler):

            async def _key_handler(event: "KeyPressEvent"):
                return await self._handler()

            return _key_handler
        else:

            def _key_handler(event: "KeyPressEvent"):
                return self._handler()

            return _key_handler

    @property
    def menu_handler(self):
        """The handler must be ``None`` for a disabled menu item."""
        if self.filter():
            return self._handler

    @property
    def text(self) -> "str":
        """Generate the text for the menu item."""
        text = self.title
        if self.status is not None:
            text += " ✓" if self.status() else ""

        return text

    @property
    def disabled(self) -> "bool":
        """Determine if the menu item is disabled."""
        return self.filter()

    def __repr__(self):
        return f"<Command name='{self.name}'>"


def add(**kwargs: "Any"):
    """Adds a command to the centralized command system."""

    def decorator(handler: "Callable") -> "Callable":
        cmd = Command(handler, **kwargs)
        commands[cmd.name] = cmd
        return handler

    return decorator


def get(name: "str"):
    """Get a command from the centralized command system by name."""
    try:
        return commands[name]
    except KeyError as e:
        raise KeyError("Unknown command: %r" % name) from e
