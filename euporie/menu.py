# -*- coding: utf-8 -*-
"""Defines a smarter menu item."""
from typing import TYPE_CHECKING, Any, Callable, Optional, Sequence, Union

from prompt_toolkit.widgets.menus import MenuItem

if TYPE_CHECKING:
    from prompt_toolkit.filters import Filter
    from prompt_toolkit.keys import Keys


class SmartMenuItem(MenuItem):
    """A prompt-toolkit compatible menu item with more advanced capabilities.

    It can use a function to generate the text to display, display a checkmark if a
    condition is true, and disable the handler if a condition is met.
    """

    def __init__(
        self,
        text: "Union[str, Callable]" = "",
        handler: "Optional[Callable[[], None]]" = None,
        children: "Optional[list[MenuItem]]" = None,
        shortcut: "Optional[Sequence[Union[Keys, str]]]" = None,
        disabler: "Union[Filter]" = None,
        toggler: "Optional[Filter]" = None,
    ) -> None:
        """Initiate a smart menu item.

        Args:
            text: A string, or a callable which returns the text to display.
            handler: As per `prompt_toolkit.widgets.menus.MenuItem`.
            children: As per `prompt_toolkit.widgets.menus.MenuItem`.
            shortcut: As per `prompt_toolkit.widgets.menus.MenuItem`.
            disabler: The handler will be disabled when this callable returns True.
            toggler: A checkmark will be displayed next to the menu text when this
                callable returns true.

        """
        self.text_generator = text
        self.disabler = disabler
        self.toggler = toggler
        self._handler = handler
        super().__init__(self.text, handler, children, shortcut, False)

    # Type checking disabled for the following property methods due to open mypy bug:
    # https://github.com/python/mypy/issues/4125

    @property  # type: ignore
    def text(self) -> "str":  # type: ignore
        """Generate the text for this menu item."""
        if callable(self.text_generator):
            text = self.text_generator()
        else:
            text = self.text_generator
        if self.toggler is not None:
            text += " ✓" if self.toggler() else ""

        # Check if this menu item should be disabled, and if so, remove the handler
        self.handler = None if self.disabled else self._handler

        return text

    @text.setter
    def text(self, value: "Any") -> "None":
        """Prevent the inherited `__init__` method setting this property value."""
        pass

    @property  # type: ignore
    def disabled(self) -> "bool":  # type: ignore
        """Determine if the menu item is disabled."""
        return self.disabler is not None and self.disabler()

    @disabled.setter
    def disabled(self, value: "Any") -> None:
        """Prevent the inherited `__init__` method setting this property value."""
        pass
