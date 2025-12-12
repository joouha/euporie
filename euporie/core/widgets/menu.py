"""Define an application menu."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import (
    Condition,
    has_completions,
    has_focus,
    is_done,
    to_filter,
)
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
    ScrollOffsets,
    to_container,
)
from prompt_toolkit.layout.controls import FormattedTextControl, UIContent
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.menus import (
    CompletionsMenuControl as PtkCompletionsMenuControl,
)
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth

from euporie.core.app.current import get_app
from euporie.core.bars.status import StatusContainer
from euporie.core.border import OuterHalfGrid
from euporie.core.layout.containers import HSplit, VSplit, Window
from euporie.core.widgets.decor import Shadow

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from typing import Any

    from prompt_toolkit.filters import Filter, FilterOrBool
    from prompt_toolkit.formatted_text.base import (
        AnyFormattedText,
        OneStyleAndTextTuple,
        StyleAndTextTuples,
    )
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.controls import UIControl

    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields
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
        formatted_text: AnyFormattedText = "",
        description: str = "",
        separator: bool = False,
        handler: Callable[[], None] | None = None,
        children: list[MenuItem] | None = None,
        shortcut: AnyFormattedText = "",
        hidden: FilterOrBool = False,
        disabled: FilterOrBool = False,
        toggled: Filter | None = None,
        collapse_prefix: bool = False,
        collapse_suffix: bool = True,
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
        self._prefix_width: int | None = None

        self.handler = handler
        self.children = children or []
        self.shortcut = shortcut
        self.selected_item = 0

    @property
    def formatted_text(self) -> StyleAndTextTuples:
        """Generate the formatted text for this menu item."""
        if callable(self._formatted_text):
            text = self._formatted_text()
        else:
            text = self._formatted_text

        return to_formatted_text(text)

    # Type checking disabled for the following property methods due to open mypy bug:
    # https://github.com/python/mypy/issues/4125

    @property
    def text(self) -> str:
        """Return plain text version of the item's formatted text."""
        return fragment_list_to_text(self.formatted_text)

    @text.setter
    def text(self, value: Any) -> None:
        """Prevent the inherited `__init__` method setting this property value."""

    @classmethod
    def from_command(cls, command: Command) -> MenuItem:
        """Create a menu item from a command."""
        return cls(
            formatted_text=command.menu_title,
            handler=command.run,
            shortcut=command.key_str,
            disabled=~command.filter,
            hidden=command.hidden,
            toggled=command.toggled,
            description=command.description,
        )

    @property  # type: ignore
    def disabled(self) -> bool:  # type: ignore
        """Determine if the menu item is disabled."""
        return self._disabled()

    @disabled.setter
    def disabled(self, value: Any) -> None:
        """Prevent the inherited `__init__` method setting this property value."""

    @property
    def has_toggles(self) -> bool:
        """Return true if any child items have a toggle state."""
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
    def prefix(self) -> StyleAndTextTuples:
        """The item's prefix.

        Formatted text that will be displayed before the item's main text. All prefixes
        in a menu are left aligned and padded to take up equal width.

        Returns:
            Formatted text

        """
        prefix: StyleAndTextTuples = []
        if self.toggled is not None:
            prefix.append(("class:menu,prefix", "✓ " if self.toggled() else "  "))
        return prefix

    @property
    def prefix_width(self) -> int:
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
    def suffix(self) -> StyleAndTextTuples:
        """The item's suffix.

        Formatted text that will be displayed aligned right after them item's main text.

        Returns:
            Formatted text

        """
        suffix: StyleAndTextTuples = []
        if self.children:
            suffix.append(("", "›"))
        elif self.shortcut is not None:
            suffix += [("class:menu", "  ")]
            suffix += to_formatted_text(self.shortcut, style="class:menu,shortcut")
        return suffix

    @property
    def suffix_width(self) -> int:
        """The maximum width of the item's children's suffixes."""
        return max(
            [
                fragment_list_width(child.suffix) if isinstance(child, MenuItem) else 0
                for child in self.children
            ]
            + [0]
        )

    @property
    def width(self) -> int:
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

    def __init__(
        self,
        app: BaseApp,
        menu_items: Sequence[MenuItem],
        grid: GridStyle = OuterHalfGrid,
    ) -> None:
        """Initiate the menu bar.

        Args:
            app: The application the menubar is attached to
            menu_items: The menu items to show in the menubar
            grid: The grid style to use for the menu's borders

        """
        self.app = app
        self.menu_items = menu_items
        self.grid = grid
        self.selected_menu: list[int] = []
        self.last_focused: UIControl | None = None

        # Key bindings.
        self.kb = kb = KeyBindings()

        @Condition
        def in_main_menu() -> bool:
            return len(self.selected_menu) == 1

        @Condition
        def in_sub_menu() -> bool:
            return len(self.selected_menu) > 1

        # Navigation through the main menu.

        # Menu closed

        @kb.add("enter", filter=~in_main_menu & ~in_sub_menu)
        @kb.add("down", filter=~in_main_menu & ~in_sub_menu)
        def _closed_down(event: KeyPressEvent) -> None:
            self.selected_menu = [0]
            self.refocus()

        @kb.add("left", filter=~in_main_menu & ~in_sub_menu)
        def _closed_left(event: KeyPressEvent) -> None:
            self.selected_menu = [0]
            self.selected_menu[0] = (self.selected_menu[0] - 1) % len(self.menu_items)
            self.refocus()

        @kb.add("right", filter=~in_main_menu & ~in_sub_menu)
        def _closed_right(event: KeyPressEvent) -> None:
            self.selected_menu = [0]
            self.selected_menu[0] = (self.selected_menu[0] + 1) % len(self.menu_items)
            self.refocus()

        # Menu open

        @kb.add("left", filter=in_main_menu)
        def _left(event: KeyPressEvent) -> None:
            self.selected_menu[0] = (self.selected_menu[0] - 1) % len(self.menu_items)
            self.refocus()

        @kb.add("right", filter=in_main_menu)
        def _right(event: KeyPressEvent) -> None:
            self.selected_menu[0] = (self.selected_menu[0] + 1) % len(self.menu_items)
            self.refocus()

        @kb.add("down", filter=in_main_menu)
        def _down(event: KeyPressEvent) -> None:
            menu = self._get_menu(len(self.selected_menu) - 2)
            indices = [i for i, item in enumerate(menu.children) if not item.disabled]
            if indices:
                self.selected_menu.append(indices[0])
                self.refocus()

        @kb.add("c-c", filter=in_main_menu)
        @kb.add("c-g", filter=in_main_menu)
        def _cancel(event: KeyPressEvent) -> None:
            """Leave menu."""
            self.selected_menu = []
            self.refocus()

        # Sub menu navigation.

        @kb.add("left", filter=in_sub_menu)
        @kb.add("c-g", filter=in_sub_menu)
        @kb.add("c-c", filter=in_sub_menu)
        def _back(event: KeyPressEvent) -> None:
            """Go back to parent menu."""
            if len(self.selected_menu) > 1:
                self.selected_menu.pop()
                self.refocus()

        @kb.add("right", filter=in_sub_menu)
        def _submenu(event: KeyPressEvent) -> None:
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
            self.refocus()

        @kb.add("up", filter=in_sub_menu)
        def _up_in_submenu(event: KeyPressEvent) -> None:
            """Select previous (enabled) menu item or return to main menu."""
            # Look for previous enabled items in this sub menu.
            menu = self._get_menu(len(self.selected_menu) - 2)
            index = self.selected_menu[-1]

            previous_index = next(
                (
                    i
                    for i, item in reversed(list(enumerate(menu.children)))
                    if i < index and not item.disabled and not item.hidden()
                ),
                None,
            )
            if previous_index is not None:
                self.selected_menu[-1] = previous_index
            elif len(self.selected_menu) == 2:
                # Return to main menu.
                self.selected_menu.pop()
            self.refocus()

        @kb.add("down", filter=in_sub_menu)
        def _down_in_submenu(event: KeyPressEvent) -> None:
            """Select next (enabled) menu item."""
            menu = self._get_menu(len(self.selected_menu) - 2)
            index = self.selected_menu[-1]

            next_index = next(
                (
                    i
                    for i, item in enumerate(menu.children)
                    if i > index and not item.disabled and not item.hidden()
                ),
                None,
            )

            if next_index is not None:
                self.selected_menu[-1] = next_index
                self.refocus()

        @kb.add("enter")
        def _click(event: KeyPressEvent) -> None:
            """Click the selected menu item."""
            item = self._get_menu(len(self.selected_menu) - 1)
            if item.handler:
                self.selected_menu = []
                self.refocus()
                item.handler()

        @kb.add("escape")
        def _close(event: KeyPressEvent) -> None:
            """Close the current menu."""
            if self.selected_menu:
                self.selected_menu = self.selected_menu[:-1]
                self.refocus()

        # Add global CUA menu shortcut
        @kb.add("f10", is_global=True)
        def _open_menu_default(event: KeyPressEvent) -> None:
            if not self.focused():
                self.selected_menu = [0]
                self.refocus()

        # Add menu shortcuts
        used_keys = set()
        for i, item in enumerate(menu_items):
            key = to_plain_text(item.formatted_text)[0].lower()
            if key not in used_keys:
                used_keys |= {key}

                @kb.add(f"A-{key}", is_global=True)
                def _open_menu(event: KeyPressEvent, index: int = i) -> None:
                    """Open the  menu item."""
                    self.selected_menu = [index]
                    self.refocus()

        # Controls.
        self.control = FormattedTextControl(
            self._get_menu_fragments,
            key_bindings=self.kb,
            focusable=True,
            show_cursor=False,
        )
        self.window: Window = Window(
            height=1, content=self.control, style="class:menu,bar"
        )

        submenu = self._submenu(0)
        submenu2 = self._submenu(1)
        submenu3 = self._submenu(2)

        self.menu_containers = [self.window, submenu, submenu2, submenu3]
        self.focused = (
            has_focus(self.window)
            | has_focus(submenu)
            | has_focus(submenu2)
            | has_focus(submenu3)
        )

        self.app.menus["menu-1"] = Float(
            attach_to_window=self.window,
            xcursor=True,
            ycursor=True,
            content=ConditionalContainer(
                content=Shadow(body=submenu),
                filter=Condition(lambda: len(self.selected_menu) > 0),
            ),
        )
        self.app.menus["menu-2"] = Float(
            attach_to_window=to_container(submenu).get_children()[1],
            xcursor=True,
            ycursor=True,
            allow_cover_cursor=True,
            content=ConditionalContainer(
                content=Shadow(body=submenu2),
                filter=Condition(lambda: len(self.selected_menu) > 1)
                & Condition(lambda: bool(self._get_menu(1).children)),
            ),
        )
        self.app.menus["menu-3"] = Float(
            attach_to_window=to_container(submenu2).get_children()[1],
            xcursor=True,
            ycursor=True,
            allow_cover_cursor=True,
            content=ConditionalContainer(
                content=Shadow(body=submenu3),
                filter=Condition(lambda: len(self.selected_menu) > 2)
                & Condition(lambda: bool(self._get_menu(2).children)),
            ),
        )

    def refocus(self) -> None:
        """Focus the currently selected menu."""
        layout = self.app.layout
        if self.last_focused is None:
            self.last_focused = layout.current_control
        if self.selected_menu:
            layout.focus(self.menu_containers[len(self.selected_menu) - 1])
        elif self.last_focused:
            try:
                layout.focus(self.last_focused)
            except ValueError:
                layout.focus_previous()
            self.last_focused = None

    def _get_menu(self, level: int) -> MenuItem:
        index = self.selected_menu[0] if self.selected_menu else 0
        menu = self.menu_items[index]
        for i, index in enumerate(self.selected_menu[1:]):
            if i < level:
                try:
                    menu = menu.children[index]
                except IndexError:
                    return MenuItem("debug")
        return menu

    def _get_menu_fragments(self) -> StyleAndTextTuples:
        focused = self.focused()

        # This is called during the rendering. When we discover that this
        # widget doesn't have the focus anymore, reset the menu state.
        if not focused:
            self.selected_menu = []

        def mouse_handler(index: int, mouse_event: MouseEvent) -> NotImplementedOrNone:
            focused = self.focused()
            hover = mouse_event.event_type == MouseEventType.MOUSE_MOVE
            if mouse_event.event_type == MouseEventType.MOUSE_DOWN or (
                hover and focused
            ):
                # Toggle focus.
                if self.selected_menu == [index]:
                    if not hover and focused:
                        self.selected_menu = []
                    else:
                        return NotImplemented
                else:
                    self.selected_menu = [index]
                self.refocus()
                return None

            return NotImplemented

        results: StyleAndTextTuples = []
        used_keys = set()

        selected_index: int | None = None
        if self.selected_menu:
            selected_index = self.selected_menu[0]
        elif focused:
            selected_index = 0

        for i, item in enumerate(self.menu_items):
            # Add shortcut key hints
            key = to_plain_text(item.formatted_text)[0].lower()
            ft: StyleAndTextTuples
            if key not in used_keys:
                ft = explode_text_fragments(item.formatted_text)
                ft = [(f"underline {ft[0][0]}", ft[0][1]), *ft[1:]]
                used_keys |= {key}
            else:
                ft = item.formatted_text

            mh = partial(mouse_handler, i)
            selected = i == selected_index
            style = "class:selection" if selected else ""
            first_style = style
            if selected:
                first_style += " [SetMenuPosition]"
            cursor_style = (
                "[SetCursorPosition]"
                if selected and len(self.selected_menu) == 1
                else ""
            )

            results.extend(
                [
                    (first_style, " ", mh),
                    (cursor_style, ""),
                    *[(f"{style} {style_}", text, mh) for style_, text, *_ in ft],
                    (style, " ", mh),
                ]
            )

        return results

    def _submenu(self, level: int = 0) -> AnyContainer:
        grid = self.grid

        def get_text_fragments() -> StyleAndTextTuples:
            result: StyleAndTextTuples = []
            if level < len(self.selected_menu):
                menu = self._get_menu(level)

                if menu.children:
                    try:
                        selected_item = self.selected_menu[level + 1]
                    except IndexError:
                        selected_item = -1

                    def one_item(
                        i: int, item: MenuItem
                    ) -> Iterable[OneStyleAndTextTuple]:
                        assert isinstance(item, MenuItem)
                        assert isinstance(menu, MenuItem)

                        def mouse_handler(
                            mouse_event: MouseEvent,
                        ) -> NotImplementedOrNone:
                            if item.disabled:
                                # The arrow keys can't interact with menu items that
                                # are disabled. The mouse shouldn't be able to either.
                                return None
                            hover = mouse_event.event_type == MouseEventType.MOUSE_MOVE
                            if (
                                mouse_event.event_type == MouseEventType.MOUSE_UP
                                or hover
                            ):
                                app = get_app()
                                if not hover and item.handler:
                                    self.selected_menu = []
                                    self.refocus()
                                    item.handler()
                                else:
                                    new_selection = [
                                        *self.selected_menu[: level + 1],
                                        i,
                                    ]
                                    if self.selected_menu != new_selection:
                                        self.selected_menu = new_selection
                                        app.layout.focus(
                                            self.menu_containers[
                                                len(self.selected_menu) - 1
                                            ]
                                        )
                                        return None
                            elif mouse_event.event_type == MouseEventType.SCROLL_UP:
                                menu = self._get_menu(len(self.selected_menu) - 2)
                                index = self.selected_menu[-1]

                                previous_index = next(
                                    (
                                        i
                                        for i, item in reversed(
                                            list(enumerate(menu.children))
                                        )
                                        if i < index
                                        and not item.disabled
                                        and not item.hidden()
                                    ),
                                    None,
                                )
                                if previous_index is not None:
                                    self.selected_menu[-1] = previous_index
                                    return None

                            elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                                menu = self._get_menu(len(self.selected_menu) - 2)
                                index = self.selected_menu[-1]

                                next_index = next(
                                    (
                                        i
                                        for i, item in enumerate(menu.children)
                                        if i > index
                                        and not item.disabled
                                        and not item.hidden()
                                    ),
                                    None,
                                )
                                if next_index is not None:
                                    self.selected_menu[-1] = next_index
                                    return None

                            return NotImplemented

                        if item.separator:
                            # Show a connected line with no mouse handler
                            yield (
                                "class:menu,border",
                                grid.SPLIT_LEFT
                                + (grid.SPLIT_MID * menu.width)
                                + grid.SPLIT_RIGHT,
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
                            yield (f"{style} class:menu,border", grid.MID_LEFT)
                            if i == selected_item:
                                # XXXXXXX
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
                            menu_formatted_text: StyleAndTextTuples = to_formatted_text(
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
                            yield (f"{style} class:menu,border", grid.MID_RIGHT)

                    visible_children = [x for x in menu.children if not x.hidden()]
                    for i, item in enumerate(visible_children):
                        result.extend(one_item(i, item))
                        if i < len(visible_children) - 1:
                            result.append(("", "\n"))

            return result

        return StatusContainer(
            body=HSplit(
                [
                    VSplit(
                        [
                            Window(char=grid.TOP_LEFT, width=1, height=1),
                            Window(char=grid.TOP_MID, height=1),
                            Window(char=grid.TOP_RIGHT, width=1, height=1),
                        ],
                        style="class:border",
                    ),
                    Window(
                        FormattedTextControl(
                            get_text_fragments,
                            focusable=True,
                            show_cursor=False,
                            key_bindings=self.kb,
                        ),
                        scroll_offsets=ScrollOffsets(top=1, bottom=1),
                    ),
                    VSplit(
                        [
                            Window(char=grid.BOTTOM_LEFT, width=1, height=1),
                            Window(char=grid.BOTTOM_MID, height=1),
                            Window(char=grid.BOTTOM_RIGHT, width=1, height=1),
                        ],
                        style="class:border",
                    ),
                ],
                style="class:menu",
            ),
            status=self.__pt_status__,
        )

    def __pt_container__(self) -> Container:
        """Return the menu bar container's content."""
        return self.window

    def __pt_status__(self) -> StatusBarFields:
        """Return the description of the currently selected menu item."""
        selected_item = self._get_menu(len(self.selected_menu) - 1)
        if isinstance(selected_item, MenuItem):
            return ([selected_item.description], [])
        else:
            return ([], [])


class CompletionsMenuControl(PtkCompletionsMenuControl):
    """A custom completions menu control."""

    def create_content(self, width: int, height: int) -> UIContent:
        """Create a UIContent object for this control."""
        complete_state = get_app().current_buffer.complete_state
        if complete_state:
            completions = complete_state.completions
            index = complete_state.complete_index  # Can be None!

            # Calculate width of completions menu.
            menu_width = self._get_menu_width(width, complete_state)
            menu_meta_width = self._get_menu_meta_width(
                width - menu_width, complete_state
            )
            total_width = menu_width + menu_meta_width

            grid = OuterHalfGrid

            def get_line(i: int) -> StyleAndTextTuples:
                c = completions[i]
                selected_item = i == index
                output: StyleAndTextTuples = []

                style = "class:menu"
                if selected_item:
                    style += ",selection"

                output.append((f"{style},border", grid.MID_LEFT))
                if selected_item:
                    output.append(("[SetCursorPosition]", ""))
                # Construct the menu item contents
                padding = " " * (
                    total_width
                    - fragment_list_width(c.display)
                    - fragment_list_width(c.display_meta)
                    - 2
                )
                output.extend(
                    to_formatted_text(
                        [
                            *c.display,
                            ("", padding),
                            *to_formatted_text(
                                c.display_meta, style=f"{style} {c.style}"
                            ),
                        ],
                        style=style,
                    )
                )
                output.append((f"{style},border", grid.MID_RIGHT))

                # Apply mouse handler
                return [
                    (fragment[0], fragment[1], self.mouse_handler)
                    for fragment in output
                ]

            return UIContent(
                get_line=get_line,
                cursor_position=Point(x=0, y=index or 0),
                line_count=len(completions),
            )

        return UIContent()

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events: clicking and scrolling."""
        if mouse_event.event_type == MouseEventType.MOUSE_MOVE:
            # Set completion
            complete_state = get_app().current_buffer.complete_state
            if complete_state:
                complete_state.complete_index = mouse_event.position.y
                return None

        return super().mouse_handler(mouse_event)


class CompletionsMenu(ConditionalContainer):
    """A custom completions menu."""

    def __init__(
        self,
        max_height: int | None = 16,
        scroll_offset: int | Callable[[], int] = 1,
        extra_filter: FilterOrBool = True,
        z_index: int = 10**8,
    ) -> None:
        """Create a completions menu with borders."""
        extra_filter = to_filter(extra_filter)
        grid = OuterHalfGrid
        super().__init__(
            content=HSplit(
                [
                    VSplit(
                        [
                            Window(char=grid.TOP_LEFT, width=1, height=1),
                            Window(char=grid.TOP_MID, height=1),
                            Window(char=grid.TOP_RIGHT, width=1, height=1),
                        ],
                        style="class:border",
                    ),
                    Window(
                        content=CompletionsMenuControl(),
                        width=Dimension(min=8),
                        height=Dimension(min=1, max=max_height),
                        scroll_offsets=ScrollOffsets(
                            top=scroll_offset, bottom=scroll_offset
                        ),
                        dont_extend_width=True,
                        z_index=z_index,
                    ),
                    VSplit(
                        [
                            Window(char=grid.BOTTOM_LEFT, width=1, height=1),
                            Window(char=grid.BOTTOM_MID, height=1),
                            Window(char=grid.BOTTOM_RIGHT, width=1, height=1),
                        ],
                        style="class:border",
                    ),
                ],
                style="class:menu",
            ),
            # Show when there are completions but not at the point we are
            # returning the input.
            filter=has_completions & ~is_done & extra_filter,
        )
