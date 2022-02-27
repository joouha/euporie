# -*- coding: utf-8 -*-
"""Defines the application menu."""
from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.filters import to_filter
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import (
    fragment_list_to_text,
    fragment_list_width,
)
from prompt_toolkit.keys import Keys
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.widgets.menus import MenuItem as PtkMenuItem

if TYPE_CHECKING:
    from typing import Any, Callable, Optional, Sequence, Union

    from prompt_toolkit.filters import Filter, FilterOrBool
    from prompt_toolkit.formatted_text.base import AnyFormattedText, StyleAndTextTuples

    from euporie.commands.base import Command

__all__ = ["MenuItem"]


class MenuItem(PtkMenuItem):
    """A prompt-toolkit compatible menu item with more advanced capabilities.

    It can use a function to generate formatted text to display, display a checkmark if
    a condition is true, and disable the handler if a condition is met.
    """

    def __init__(
        self,
        formatted_text: "AnyFormattedText" = "",
        description: "str" = "",
        separator: "bool" = False,
        handler: "Optional[Callable[[], None]]" = None,
        children: "Optional[list[PtkMenuItem]]" = None,
        shortcut: "Optional[Sequence[Union[Keys, str]]]" = None,
        hidden: "FilterOrBool" = False,
        disabled: "FilterOrBool" = False,
        toggled: "Optional[Filter]" = None,
    ) -> None:
        """Initiate a smart menu item.

        Args:
            formatted_text: A formatted text, or a callable which returns the text to
                display
            description: More information about what the menu item does
            separator: If True, this menu item is treated as a separator
            handler: As per `prompt_toolkit.widgets.menus.MenuItem`
            children: As per `prompt_toolkit.widgets.menus.MenuItem`
            shortcut: As per `prompt_toolkit.widgets.menus.MenuItem`
            hidden: The handler will be hidden when this filter is True
            disabled: The handler will be disabled when this filter is True
            toggled: A checkmark will be displayed next to the menu text when this
                callable returns True

        """
        self._formatted_text = formatted_text
        self.description = description
        self.separator = separator
        self._disabled = to_filter(disabled) | to_filter(self.separator)
        self.hidden = to_filter(hidden)
        self.toggled = toggled
        super().__init__(
            text=self.text,
            handler=handler,
            children=children,
            shortcut=shortcut,
            disabled=False,
        )

    @property
    def formatted_text(self) -> "StyleAndTextTuples":
        """Generate the formatted text for this menu item."""
        if callable(self._formatted_text):
            text = self._formatted_text()
        else:
            text = self._formatted_text

        return to_formatted_text(text)

    # Type checking disabled for the following property methods due to open mypy bug:
    # https://github.com/python/mypy/issues/4125

    @property  # type: ignore
    def text(self) -> "str":  # type: ignore
        """Return plain text verision of the item's formatted text."""
        return fragment_list_to_text(self.formatted_text)

    @text.setter
    def text(self, value: "Any") -> "None":
        """Prevent the inherited `__init__` method setting this property value."""
        pass

    @classmethod
    def from_command(cls, command: "Command") -> "MenuItem":
        """Create a menu item from a command."""
        return cls(
            formatted_text=command.menu_title,
            handler=command.menu_handler,
            shortcut=command.keys[0] if command.keys else None,
            disabled=~command.filter,
            hidden=command.hidden,
            toggled=command.toggled,
            description=command.description,
        )

    @property  # type: ignore
    def disabled(self) -> "bool":  # type: ignore
        """Determine if the menu item is disabled."""
        return self._disabled()

    @disabled.setter
    def disabled(self, value: "Any") -> None:
        """Prevent the inherited `__init__` method setting this property value."""
        pass

    @property
    def has_toggles(self) -> "bool":
        """Returns true if any child items have a toggle state."""
        toggles = False
        for child in self.children:
            if (
                not toggles
                and isinstance(child, MenuItem)
                and child.toggled is not None
            ):
                toggles = True
        return toggles

    @property
    def prefix(self) -> "StyleAndTextTuples":
        """The item's prefix.

        Formatted text that will be displayed before the item's main text. All prefixes
        in a menu are left aligned and padded to take up equal width.

        Returns:
            Formatted text

        """
        prefix: "StyleAndTextTuples" = []
        if self.toggled is not None:
            prefix.append(("", "✓ " if self.toggled() else "  "))
        return prefix

    @property
    def suffix(self) -> "StyleAndTextTuples":
        """The item's suffix.

        Formatted text that will be displayed aligned right after them item's main text.

        Returns:
            Formatted text

        """
        suffix: "StyleAndTextTuples" = []
        if self.children:
            suffix.append(("", ">"))
        elif self.shortcut is not None:
            suffix.append(("class:menu-bar.shortcut", f"  {self.shortcut_str}"))
        return suffix

    @property
    def shortcut_str(self) -> "str":
        """A string representing the item's main keyboard shortcut."""
        key_strs = []
        for key in self.shortcut or []:
            if isinstance(key, Keys):
                key_strs.append(key.value)
            else:
                key_strs.append(key)
        return ",".join(key_strs)

    @property
    def prefix_width(self) -> "int":
        """The maximum width of the item's children's prefixes."""
        return max(
            [
                fragment_list_width(child.prefix) if isinstance(child, MenuItem) else 0
                for child in self.children
            ]
            + [0]
        )

    @property
    def suffix_width(self) -> "int":
        """The maximum width of the item's children's suffixes."""
        return max(
            [
                fragment_list_width(child.suffix) if isinstance(child, MenuItem) else 0
                for child in self.children
            ]
            + [0]
        )

    @property
    def width(self) -> "int":
        """The maximum width of the item's children."""
        return (
            self.prefix_width
            + max([get_cwidth(child.text) for child in self.children])
            + self.suffix_width
        )
