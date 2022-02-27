# -*- coding: utf-8 -*-
"""Defines the application menu."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import fragment_list_width
from prompt_toolkit.layout import VSplit
from prompt_toolkit.layout.containers import Container, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.widgets.menus import MenuContainer as PtKMenuContainer
from prompt_toolkit.widgets.menus import MenuItem as PtkMenuItem

from euporie.app.current import get_base_app as get_app
from euporie.box import SquareBorder as Border
from euporie.menu.item import MenuItem

if TYPE_CHECKING:
    from typing import Iterable, Optional, Sequence

    from prompt_toolkit.formatted_text.base import (
        AnyFormattedText,
        OneStyleAndTextTuple,
        StyleAndTextTuples,
    )
    from prompt_toolkit.key_binding import KeyBindingsBase
    from prompt_toolkit.layout.containers import AnyContainer, Float

__all__ = ["MenuContainer"]

log = logging.getLogger(__name__)


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
        def one_item(i: "int", item: "PtkMenuItem") -> "Iterable[OneStyleAndTextTuple]":
            assert isinstance(item, MenuItem)

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
                        i: int, item: "PtkMenuItem"
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
                                Border.SPLIT_LEFT
                                + (Border.HORIZONTAL * (menu.width + 2))
                                + Border.SPLIT_RIGHT,
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
