"""Defines an application menu."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.filters import Condition, to_filter
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import (
    fragment_list_to_text,
    fragment_list_width,
    to_plain_text,
)
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Container,
    Float,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth

from euporie.core.border import OuterHalfGrid
from euporie.core.current import get_app
from euporie.core.widgets.decor import Shadow

if TYPE_CHECKING:
    from typing import Any, Callable, Iterable, Optional, Sequence

    from prompt_toolkit.filters import Filter, FilterOrBool
    from prompt_toolkit.formatted_text.base import (
        AnyFormattedText,
        OneStyleAndTextTuple,
        StyleAndTextTuples,
    )
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent

    from euporie.core.app import BaseApp
    from euporie.core.border import GridStyle
    from euporie.core.commands import Command


log = logging.getLogger(__name__)


class MenuItem:
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
        children: "Optional[list[MenuItem]]" = None,
        shortcut: "AnyFormattedText" = "",
        hidden: "FilterOrBool" = False,
        disabled: "FilterOrBool" = False,
        toggled: "Optional[Filter]" = None,
        collapse_prefix: "bool" = False,
        collapse_suffix: "bool" = True,
    ) -> "None":
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
            collapse_prefix: If :py:const:`False`, all prefixes in the menu will be
                padded so they have equal widths
            collapse_suffix: if :py:const:`False`, all suffixes in the menu will be
                padded so they have equal widths

        """
        self._formatted_text = formatted_text
        self.description = description
        self.separator = separator
        self._disabled = to_filter(disabled) | to_filter(self.separator)
        self.hidden = to_filter(hidden)
        self.toggled = toggled
        self.collapse_prefix = collapse_prefix
        self.collapse_suffix = collapse_suffix
        self._prefix_width: "Optional[int]" = None

        self.handler = handler
        self.children = children or []
        self.shortcut = shortcut
        self.selected_item = 0

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
            shortcut=command.key_str,
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
    def disabled(self, value: "Any") -> "None":
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
            prefix.append(("class:menu,prefix", "✓ " if self.toggled() else "  "))
        return prefix

    @property
    def prefix_width(self) -> "int":
        """The maximum width of the item's children's prefixes."""
        if self._prefix_width is None:
            self._prefix_width = max(
                [
                    fragment_list_width(child.prefix)
                    if isinstance(child, MenuItem)
                    else 0
                    for child in self.children
                ]
                + [0]
            )

        return self._prefix_width or 0

    @property
    def suffix(self) -> "StyleAndTextTuples":
        """The item's suffix.

        Formatted text that will be displayed aligned right after them item's main text.

        Returns:
            Formatted text

        """
        suffix: "StyleAndTextTuples" = []
        if self.children:
            suffix.append(("", "›"))
        elif self.shortcut is not None:
            suffix += [("class:menu", "  ")]
            suffix += to_formatted_text(self.shortcut, style="class:menu,shortcut")
        return suffix

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
        widths = [0]
        for child in self.children:
            width = 0
            if self.collapse_prefix:
                width += (
                    get_cwidth(to_plain_text(child.prefix))
                    if isinstance(child, MenuItem)
                    else 0
                )
            else:
                width += self.prefix_width
            width += get_cwidth(child.text)
            if self.collapse_suffix:
                width += (
                    get_cwidth(to_plain_text(child.suffix))
                    if isinstance(child, MenuItem)
                    else 0
                )
            else:
                width += self.suffix_width
            widths.append(width)
        return max(widths)


class MenuBar:
    """A container to hold the menubar and main application body."""

    def _get_menu(self, level: "int") -> "MenuItem":
        menu = self.menu_items[self.selected_menu[0]]

        for i, index in enumerate(self.selected_menu[1:]):
            if i < level:
                try:
                    menu = menu.children[index]
                except IndexError:
                    return MenuItem("debug")

        return menu

    def _get_menu_fragments(self) -> "StyleAndTextTuples":

        focused = get_app().layout.has_focus(self.window)

        # This is called during the rendering. When we discover that this
        # widget doesn't have the focus anymore. Reset menu state.
        if not focused:
            self.selected_menu = [0]

        def mouse_handler(index: "int", mouse_event: MouseEvent) -> "None":
            hover = mouse_event.event_type == MouseEventType.MOUSE_MOVE
            if mouse_event.event_type == MouseEventType.MOUSE_DOWN or hover and focused:
                # Toggle focus.
                app = get_app()
                if not hover:
                    if app.layout.has_focus(self.window):
                        if self.selected_menu == [index]:
                            app.layout.focus_last()
                    else:
                        app.layout.focus(self.window)
                self.selected_menu = [index]

        results: "StyleAndTextTuples" = []
        used_keys = set()

        for i, item in enumerate(self.menu_items):

            # Add shortcut key hints
            key = to_plain_text(item.formatted_text)[0].lower()
            ft: "StyleAndTextTuples"
            if key not in used_keys:
                ft = explode_text_fragments(item.formatted_text)
                ft = [(f"underline {ft[0][0]}", ft[0][1]), *ft[1:]]
                used_keys |= {key}
            else:
                ft = item.formatted_text

            mh = partial(mouse_handler, i)
            selected = i == self.selected_menu[0] and focused
            style = "class:selection" if selected else ""
            first_style = f"{style} [SetMenuPosition]" if selected else style

            results.extend(
                [
                    (first_style, " ", mh),
                    *[(f"{style} {style_}", text, mh) for style_, text, *_ in ft],
                    (style, " ", mh),
                ]
            )

        return results

    def _submenu(self, level: "int" = 0) -> "Window":
        def get_text_fragments() -> "StyleAndTextTuples":
            result: "StyleAndTextTuples" = []
            if level < len(self.selected_menu):
                menu = self._get_menu(level)

                if menu.children:
                    result.extend(
                        [
                            ("class:menu,border", self.grid.TOP_LEFT),
                            ("class:menu,border", self.grid.TOP_MID * menu.width),
                            ("class:menu,border", self.grid.TOP_RIGHT),
                            ("", "\n"),
                        ]
                    )

                    try:
                        selected_item = self.selected_menu[level + 1]
                    except IndexError:
                        selected_item = -1

                    def one_item(
                        i: int, item: "MenuItem"
                    ) -> "Iterable[OneStyleAndTextTuple]":
                        assert isinstance(item, MenuItem)
                        assert isinstance(menu, MenuItem)

                        def mouse_handler(mouse_event: "MouseEvent") -> "None":
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
                                "class:menu,border",
                                self.grid.SPLIT_LEFT
                                + (self.grid.SPLIT_MID * menu.width)
                                + self.grid.SPLIT_RIGHT,
                            )

                        else:
                            # Show the right edge
                            style = ""
                            # Set the style if disabled
                            if item.disabled:
                                style += "class:menu,disabled"
                            # Set the style and cursor if selected
                            if i == selected_item:
                                style += "class:menu,selection"
                            yield (f"{style} class:menu,border", self.grid.MID_LEFT)
                            if i == selected_item:
                                yield ("[SetCursorPosition]", "")
                            # Construct the menu item contents
                            prefix_padding = " " * (
                                0
                                if menu.collapse_prefix
                                else menu.prefix_width
                                - fragment_list_width(item.prefix)
                            )
                            suffix_padding = " " * (
                                menu.width
                                - fragment_list_width(item.prefix)
                                - len(prefix_padding)
                                - fragment_list_width(item.formatted_text)
                                - (
                                    fragment_list_width(item.suffix)
                                    if menu.collapse_suffix
                                    else menu.suffix_width
                                )
                            )
                            text_padding = " " * (
                                menu.width
                                - fragment_list_width(item.prefix)
                                - len(prefix_padding)
                                - fragment_list_width(item.formatted_text)
                                - fragment_list_width(item.suffix)
                                - len(suffix_padding)
                            )
                            menu_formatted_text: "StyleAndTextTuples" = (
                                to_formatted_text(
                                    [
                                        *item.prefix,
                                        ("", prefix_padding),
                                        *item.formatted_text,
                                        ("", text_padding),
                                        ("", suffix_padding),
                                        *item.suffix,
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
                            yield (f"{style} class:menu,border", self.grid.MID_RIGHT)

                        yield ("", "\n")

                    for i, item in enumerate(menu.children):
                        if not item.hidden():
                            result.extend(one_item(i, item))

                    result.extend(
                        [
                            ("class:menu,border", self.grid.BOTTOM_LEFT),
                            ("class:menu,border", self.grid.BOTTOM_MID * menu.width),
                            ("class:menu,border", self.grid.BOTTOM_RIGHT),
                        ]
                    )

            return result

        return Window(FormattedTextControl(get_text_fragments), style="class:menu")

    def __init__(
        self,
        app: "BaseApp",
        menu_items: "Sequence[MenuItem]",
        grid: "GridStyle" = OuterHalfGrid,
    ) -> "None":
        """Initiate the menu bar.

        Args:
            app: The application the menubar is attached to
            menu_items: The menu items to show in the menubar
            grid: The grid style to use for the menu's borders

        """
        self.app = app
        self.menu_items = menu_items
        self.grid = grid
        self.selected_menu = [0]

        # Key bindings.
        kb = KeyBindings()

        @Condition
        def in_main_menu() -> bool:
            return len(self.selected_menu) == 1

        @Condition
        def in_sub_menu() -> bool:
            return len(self.selected_menu) > 1

        # Navigation through the main menu.

        @kb.add("left", filter=in_main_menu)
        def _left(event: "KeyPressEvent") -> "None":
            self.selected_menu[0] = max(0, self.selected_menu[0] - 1)

        @kb.add("right", filter=in_main_menu)
        def _right(event: "KeyPressEvent") -> "None":
            self.selected_menu[0] = min(
                len(self.menu_items) - 1, self.selected_menu[0] + 1
            )

        @kb.add("down", filter=in_main_menu)
        def _down(event: "KeyPressEvent") -> "None":
            self.selected_menu.append(0)

        @kb.add("c-c", filter=in_main_menu)
        @kb.add("c-g", filter=in_main_menu)
        def _cancel(event: "KeyPressEvent") -> "None":
            """Leave menu."""
            event.app.layout.focus_last()

        # Sub menu navigation.

        @kb.add("left", filter=in_sub_menu)
        @kb.add("c-g", filter=in_sub_menu)
        @kb.add("c-c", filter=in_sub_menu)
        def _back(event: "KeyPressEvent") -> "None":
            """Go back to parent menu."""
            if len(self.selected_menu) > 1:
                self.selected_menu.pop()

        @kb.add("right", filter=in_sub_menu)
        def _submenu(event: "KeyPressEvent") -> "None":
            """Go into a sub menu."""
            if self._get_menu(len(self.selected_menu) - 1).children:
                self.selected_menu.append(0)

            # If This item does not have a sub menu. Go up in the parent menu.
            elif (
                len(self.selected_menu) == 2
                and self.selected_menu[0] < len(self.menu_items) - 1
            ):
                self.selected_menu = [
                    min(len(self.menu_items) - 1, self.selected_menu[0] + 1)
                ]
                if self.menu_items[self.selected_menu[0]].children:
                    self.selected_menu.append(0)

        @kb.add("up", filter=in_sub_menu)
        def _up_in_submenu(event: "KeyPressEvent") -> "None":
            """Select previous (enabled) menu item or return to main menu."""
            # Look for previous enabled items in this sub menu.
            menu = self._get_menu(len(self.selected_menu) - 2)
            index = self.selected_menu[-1]

            previous_indexes = [
                i
                for i, item in enumerate(menu.children)
                if i < index and not item.disabled
            ]

            if previous_indexes:
                self.selected_menu[-1] = previous_indexes[-1]
            elif len(self.selected_menu) == 2:
                # Return to main menu.
                self.selected_menu.pop()

        @kb.add("down", filter=in_sub_menu)
        def _down_in_submenu(event: "KeyPressEvent") -> "None":
            """Select next (enabled) menu item."""
            menu = self._get_menu(len(self.selected_menu) - 2)
            index = self.selected_menu[-1]

            next_indexes = [
                i
                for i, item in enumerate(menu.children)
                if i > index and not item.disabled
            ]

            if next_indexes:
                self.selected_menu[-1] = next_indexes[0]

        @kb.add("enter")
        def _click(event: "KeyPressEvent") -> "None":
            """Click the selected menu item."""
            item = self._get_menu(len(self.selected_menu) - 1)
            if item.handler:
                event.app.layout.focus_last()
                item.handler()

        @kb.add("escape")
        def _close(event: "KeyPressEvent") -> "None":
            """Close the current menu."""
            if len(self.selected_menu) > 1:
                self.selected_menu = self.selected_menu[:-1]
            else:
                app.layout.focus_previous()

        # Add global CUA menu shortcut
        @kb.add("f10", is_global=True)
        def _open_menu_default(event: "KeyPressEvent") -> "None":
            self.selected_menu = [0]
            event.app.layout.focus(self.window)

        # Add menu shortcuts
        used_keys = set()
        for i, item in enumerate(menu_items):
            key = to_plain_text(item.formatted_text)[0].lower()
            if key not in used_keys:
                used_keys |= {key}

                @kb.add("escape", key, is_global=True)
                def _open_menu(event: "KeyPressEvent", index: "int" = i) -> "None":
                    """Open the  menu item."""
                    self.selected_menu = [index]
                    event.app.layout.focus(self.window)

        # Controls.
        self.control = FormattedTextControl(
            self._get_menu_fragments,
            key_bindings=kb,
            focusable=True,
            show_cursor=False,
        )
        self.window: "Window" = Window(
            height=1,
            content=self.control,
            style="class:menu,bar",
        )

        submenu = self._submenu(0)
        submenu2 = self._submenu(1)
        submenu3 = self._submenu(2)

        @Condition
        def has_focus() -> bool:
            return get_app().layout.current_window == self.window

        self.app.menus["menu-1"] = Float(
            xcursor=True,
            ycursor=True,
            content=ConditionalContainer(
                content=Shadow(body=submenu), filter=has_focus
            ),
        )
        self.app.menus["menu-2"] = Float(
            attach_to_window=submenu,
            xcursor=True,
            ycursor=True,
            allow_cover_cursor=True,
            content=ConditionalContainer(
                content=Shadow(body=submenu2),
                filter=has_focus & Condition(lambda: len(self.selected_menu) >= 1),
            ),
        )
        self.app.menus["menu-3"] = Float(
            attach_to_window=submenu2,
            xcursor=True,
            ycursor=True,
            allow_cover_cursor=True,
            content=ConditionalContainer(
                content=Shadow(body=submenu3),
                filter=has_focus & Condition(lambda: len(self.selected_menu) >= 2),
            ),
        )

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

    def __pt_container__(self) -> "Container":
        """Return the menu bar container's content."""
        return self.window
