"""Defines an application menu."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from prompt_toolkit.filters import to_filter
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import (
    fragment_list_to_text,
    fragment_list_width,
)
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import VSplit
from prompt_toolkit.layout.containers import Container, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.widgets.menus import MenuContainer as PtKMenuContainer
from prompt_toolkit.widgets.menus import MenuItem as PtkMenuItem

from euporie.app.current import get_base_app as get_app
from euporie.box import SquareBorder as Border

if TYPE_CHECKING:
    from typing import Any, Callable, Iterable, Optional, Sequence, Union

    from prompt_toolkit.filters import Filter, FilterOrBool
    from prompt_toolkit.formatted_text.base import (
        AnyFormattedText,
        OneStyleAndTextTuple,
        StyleAndTextTuples,
    )
    from prompt_toolkit.key_binding import KeyBindingsBase
    from prompt_toolkit.layout.containers import AnyContainer, Float

    from euporie.commands.base import Command


__all__ = ["MenuContainer", "MenuItem"]

log = logging.getLogger(__name__)


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


class MenuContainer(PtKMenuContainer):
    """A container to hold the menubar and main application body."""

    def __init__(
        self,
        body: "AnyContainer",
        menu_items: "list[PtkMenuItem]",
        floats: "Optional[list[Float]]" = None,
        key_bindings: "Optional[KeyBindingsBase]" = None,
        left: "Optional[Sequence[AnyContainer]]" = None,
        right: "Optional[Sequence[AnyContainer]]" = None,
    ) -> "None":
        """Initiate the menu bar.

        Args:
            body: The main application container below the menubar
            menu_items: The menu items to show in the menubar
            floats: Any floats which might be displayed above the menu container
            key_bindings: Any key-bindings to apply to the menu-bar
            left: A list of containers to display to the left of the menubar
            right: A list of containers to display to the right of the menubar

        """
        super().__init__(body, menu_items, floats, key_bindings)

        assert isinstance(self.container.content, HSplit)
        assert isinstance(self.body, Container)

        # Add left and right containers to menubar
        self.container.content.children = [
            VSplit([*(left or []), self.window, *(right or [])]),
            self.body,
        ]

        get_app().container_statuses[self.window] = self.statusbar_fields

    def statusbar_fields(
        self,
    ) -> "tuple[list[AnyFormattedText], list[AnyFormattedText]]":
        """Return the description of the currently selected menu item."""
        selected_item = self._get_menu(len(self.selected_menu) - 1)
        if isinstance(selected_item, MenuItem):
            return (["", selected_item.description], [])
        else:
            return (["", ""], [])

    def _get_menu_fragments(self) -> "StyleAndTextTuples":

        focused = get_app().layout.has_focus(self.window)

        # This is called during the rendering. When we discover that this
        # widget doesn't have the focus anymore. Reset menu state.
        if not focused:
            self.selected_menu = [0]

        # Generate text fragments for the main menu.
        def one_item(i: "int", item: "MenuItem") -> "Iterable[OneStyleAndTextTuple]":
            item = cast("MenuItem", item)

            def mouse_handler(mouse_event: MouseEvent) -> None:
                hover = mouse_event.event_type == MouseEventType.MOUSE_MOVE
                if (
                    mouse_event.event_type == MouseEventType.MOUSE_DOWN
                    or hover
                    and focused
                ):
                    # Toggle focus.
                    app = get_app()
                    if not hover:
                        if app.layout.has_focus(self.window):
                            if self.selected_menu == [i]:
                                app.layout.focus_last()
                        else:
                            app.layout.focus(self.window)
                    self.selected_menu = [i]

            if i == self.selected_menu[0] and focused:
                yield ("[SetMenuPosition]", "", mouse_handler)
                style = "class:menu-bar.selected-item"
            else:
                style = "class:menu-bar"
            yield (style, " ", mouse_handler)
            yield from to_formatted_text(
                [
                    (fragment[0], fragment[1], mouse_handler)
                    for fragment in item.formatted_text
                ],
                style=style,
            )
            yield (style, " ", mouse_handler)

        result: "StyleAndTextTuples" = []
        for i, item in enumerate(self.menu_items):
            item = cast("MenuItem", item)
            result.extend(one_item(i, item))

        return result

    def _submenu(self, level: "int" = 0) -> "Window":
        def get_text_fragments() -> "StyleAndTextTuples":
            result: "StyleAndTextTuples" = []
            if level < len(self.selected_menu):
                menu = self._get_menu(level)

                if menu.children:
                    result.append(("class:menu-border", Border.TOP_LEFT))
                    result.append(
                        ("class:menu-border", Border.HORIZONTAL * (menu.width + 2))
                    )
                    result.append(("class:menu-border", Border.TOP_RIGHT))
                    result.append(("", "\n"))
                    try:
                        selected_item = self.selected_menu[level + 1]
                    except IndexError:
                        selected_item = -1

                    def one_item(
                        i: int, item: "MenuItem"
                    ) -> "Iterable[OneStyleAndTextTuple]":
                        assert isinstance(item, MenuItem)
                        assert isinstance(menu, MenuItem)

                        def mouse_handler(mouse_event: "MouseEvent") -> None:
                            if item.disabled:
                                # The arrow keys can't interact with menu items that
                                # are disabled. The mouse shouldn't be able to either.
                                return
                            hover = mouse_event.event_type == MouseEventType.MOUSE_MOVE
                            if (
                                mouse_event.event_type == MouseEventType.MOUSE_UP
                                or hover
                            ):
                                app = get_app()
                                if not hover and item.handler:
                                    app.layout.focus_last()
                                    item.handler()
                                else:
                                    self.selected_menu = self.selected_menu[
                                        : level + 1
                                    ] + [i]

                        if item.separator:
                            # Show a connected line with no mouse handler
                            yield (
                                "class:menu-border",
                                Border.LEFT_SPLIT
                                + (Border.HORIZONTAL * (menu.width + 2))
                                + Border.RIGHT_SPLIT,
                            )

                        else:
                            # Show the right edge
                            yield ("class:menu-border", Border.VERTICAL)
                            # Set the style and cursor if selected
                            style = ""
                            if i == selected_item:
                                yield ("[SetCursorPosition]", "")
                                style += "class:menu-bar.selected-item"
                            # Set the style if disabled
                            if item.disabled:
                                style += "class:menu-bar.disabled-item"
                            # Construct the menu item contents
                            menu_formatted_text: "StyleAndTextTuples" = (
                                to_formatted_text(
                                    [
                                        ("", " "),
                                        *item.prefix,
                                        (
                                            "",
                                            " "
                                            * (
                                                menu.prefix_width
                                                - fragment_list_width(item.prefix)
                                            ),
                                        ),
                                        *item.formatted_text,
                                        (
                                            "",
                                            " "
                                            * (
                                                menu.width
                                                - menu.prefix_width
                                                - fragment_list_width(
                                                    item.formatted_text
                                                )
                                                - menu.suffix_width
                                            ),
                                        ),
                                        (
                                            "",
                                            " "
                                            * (
                                                menu.suffix_width
                                                - fragment_list_width(item.suffix)
                                            ),
                                        ),
                                        *item.suffix,
                                        ("", " "),
                                    ],
                                    style=style,
                                )
                            )
                            # Apply mouse handler to all fragments
                            menu_formatted_text = [
                                (fragment[0], fragment[1], mouse_handler)
                                for fragment in menu_formatted_text
                            ]
                            # Show the menu item contents
                            yield from menu_formatted_text
                            # Position the sub-menu
                            if i == selected_item:
                                yield ("[SetMenuPosition]", "")
                            # Show the right edge
                            yield ("class:menu-border", Border.VERTICAL)

                        yield ("", "\n")

                    for i, item in enumerate(menu.children):
                        item = cast("MenuItem", item)
                        if not item.hidden():
                            result.extend(one_item(i, item))

                    result.append(("class:menu-border", Border.BOTTOM_LEFT))
                    result.append(
                        ("class:menu-border", Border.HORIZONTAL * (menu.width + 2))
                    )
                    result.append(("class:menu-border", Border.BOTTOM_RIGHT))

            return result

        return Window(FormattedTextControl(get_text_fragments), style="class:menu")
