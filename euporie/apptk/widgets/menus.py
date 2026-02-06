"""Extended menu widgets for prompt_toolkit.

This module provides enhanced menu widgets that extend prompt_toolkit's menu system
with additional features while maintaining backwards compatibility.

Key enhancements:
- Dynamic formatted text via callables
- Toggle state with checkmark display
- Hidden/disabled filters
- Separator support
- Prefix/suffix alignment control
- Command integration
- Keyboard shortcut hints with Alt+key bindings
- F10 global shortcut for CUA-style menu activation
- Status bar integration
- Custom grid styles for borders
"""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from euporie.apptk.application.current import get_app
from euporie.apptk.filters.utils import to_filter
from euporie.apptk.formatted_text.base import to_formatted_text
from euporie.apptk.layout.utils import explode_text_fragments
from euporie.apptk.utils import get_cwidth
from prompt_toolkit.widgets.menus import MenuContainer as PtkMenuContainer
from prompt_toolkit.widgets.menus import MenuItem as PtkMenuItem

from euporie.apptk.border import OuterHalfGrid, ThinGrid
from euporie.apptk.commands import get_cmd
from euporie.apptk.filters import Condition, has_focus
from euporie.apptk.formatted_text.utils import (
    fragment_list_to_text,
    fragment_list_width,
    to_plain_text,
)
from euporie.apptk.key_binding.key_bindings import KeyBindings
from euporie.apptk.layout.containers import (
    ConditionalContainer,
    Container,
    Float,
    HSplit,
    ScrollOffsets,
    VSplit,
    Window,
    to_container,
)
from euporie.apptk.layout.controls import FormattedTextControl
from euporie.apptk.mouse_events import MouseEvent, MouseEventType
from euporie.apptk.widgets.base import Shadow
from euporie.core.bars.status import StatusContainer

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from typing import Any

    from euporie.apptk.formatted_text.base import (
        AnyFormattedText,
        OneStyleAndTextTuple,
        StyleAndTextTuples,
    )
    from prompt_toolkit.filters import Filter, FilterOrBool
    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.controls import UIControl

    from euporie.apptk.border import GridStyle
    from euporie.apptk.commands import Command
    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields


__all__ = [
    "MenuBar",
    "MenuContainer",
    "MenuItem",
]

log = logging.getLogger(__name__)


class MenuItem(PtkMenuItem):
    """Enhanced menu item with dynamic text, toggles, and visibility control.

    This class extends prompt_toolkit's MenuItem with additional features:
    - Dynamic formatted text via callables
    - Toggle state with checkmark display (✓)
    - Hidden/disabled filters for conditional visibility
    - Separator support for divider lines
    - Prefix/suffix alignment control
    - Command integration via from_cmd() class method
    - Description field for status bar display

    Maintains backwards compatibility with prompt_toolkit's MenuItem.
    """

    def __init__(
        self,
        text: AnyFormattedText = "",
        handler: Callable[[], None] | None = None,
        children: list[MenuItem] | None = None,
        shortcut: Sequence[str] | None = None,
        disabled: FilterOrBool = False,
        # Extended parameters
        description: str = "",
        separator: bool | None = None,
        hidden: FilterOrBool = False,
        toggled: Filter | None = None,
        collapse_prefix: bool = False,
        collapse_suffix: bool = True,
    ) -> None:
        """Initialize enhanced menu item.

        Args:
            text: Plain text to display (for backwards compatibility)
            handler: Function to call when activated
            children: Submenu items
            shortcut: Keyboard shortcut sequence (for backwards compatibility)
            disabled: Whether item is disabled (bool or Filter)
            formatted_text: Formatted text to display (can be callable), overrides text
            description: Description for status bar
            separator: If True, render as separator line
            hidden: Filter to hide this item
            toggled: Filter for toggle state (shows checkmark when True)
            collapse_prefix: If True, don't pad prefixes to equal width
            collapse_suffix: If True, don't pad suffixes to equal width
        """
        # Store the formatted text, falling back to plain text
        self._formatted_text = text

        self.description = description

        # Detect separators in a backwards compatible way
        self.separator = (
            all(x == "-" for x in self.text) if separator is None else separator
        )

        # Handle disabled as either bool or Filter
        self._disabled = to_filter(disabled) | to_filter(self.separator)
        self.hidden = to_filter(hidden)
        self.toggled = toggled
        self.collapse_prefix = collapse_prefix
        self.collapse_suffix = collapse_suffix
        self._prefix_width: int | None = None

        self.handler = handler
        self.children = children or []

        # Handle shortcut - convert sequence to formatted text if needed
        if shortcut is not None:
            if isinstance(shortcut, (list, tuple)):
                self._shortcut: AnyFormattedText = " ".join(shortcut)
            else:
                self._shortcut = shortcut
        else:
            self._shortcut = ""

        self.selected_item = 0

    @property
    def formatted_text(self) -> StyleAndTextTuples:
        """Generate formatted text, calling if callable."""
        return to_formatted_text(self._formatted_text)

    @property
    def text(self) -> str:
        """Plain text version of formatted text."""
        return to_plain_text(self.formatted_text)

    @text.setter
    def text(self, value: Any) -> None:
        """Prevent parent __init__ from setting text directly."""
        # Only set if _formatted_text hasn't been set yet
        if not hasattr(self, "_formatted_text"):
            self._formatted_text = value

    @property
    def shortcut(self) -> AnyFormattedText:
        """Get the shortcut text."""
        if callable(self._shortcut):
            return self._shortcut()
        return self._shortcut

    @shortcut.setter
    def shortcut(self, value: Any) -> None:
        """Set the shortcut."""
        self._shortcut = value

    @property
    def disabled(self) -> bool:
        """Whether item is currently disabled."""
        return self._disabled()

    @disabled.setter
    def disabled(self, value: FilterOrBool) -> None:
        """Set disabled state."""
        self._disabled = to_filter(value)

    @classmethod
    def from_cmd(cls, cmd: Command | str) -> MenuItem:
        """Create menu item from a Command object.

        Args:
            cmd: Command object or command name string

        Returns:
            MenuItem configured from the command
        """
        if isinstance(cmd, str):
            cmd = get_cmd(cmd)
        return cls(
            text=cmd.menu_title,
            handler=cmd.run,
            shortcut=lambda: next(cmd.key_strs(), ""),
            disabled=~cmd.filter,
            hidden=cmd.hidden,
            toggled=cmd.toggled,
            description=cmd.description,
        )

    @property
    def prefix(self) -> StyleAndTextTuples:
        """Prefix text (e.g., checkmark for toggled items)."""
        prefix: StyleAndTextTuples = []
        if self.toggled is not None:
            prefix.append(("class:menu,prefix", "✓ " if self.toggled() else "  "))
        return prefix

    @property
    def prefix_width(self) -> int:
        """Maximum width of children's prefixes."""
        if self._prefix_width is None:
            self._prefix_width = max(
                [
                    fragment_list_width(c.prefix)
                    for c in self.children
                    if isinstance(c, MenuItem)
                ]
                + [0]
            )
        return self._prefix_width or 0

    @property
    def suffix(self) -> StyleAndTextTuples:
        """Suffix text (submenu arrow or shortcut)."""
        suffix: StyleAndTextTuples = []
        if self.children:
            suffix.append(("", "›"))
        elif self._shortcut:
            shortcut_text = self.shortcut
            if shortcut_text:
                suffix += [("class:menu", "  ")]
                suffix += to_formatted_text(shortcut_text, style="class:menu,shortcut")
        return suffix

    @property
    def suffix_width(self) -> int:
        """Maximum width of children's suffixes."""
        return max(
            [
                fragment_list_width(c.suffix)
                for c in self.children
                if isinstance(c, MenuItem)
            ]
            + [0]
        )

    @property
    def width(self) -> int:
        """Maximum width needed for children."""
        widths = [0]
        for child in self.children:
            width = 0
            if self.collapse_prefix:
                width += fragment_list_width(child.prefix)
            else:
                width += self.prefix_width
            width += get_cwidth(child.text)
            if self.collapse_suffix:
                width += fragment_list_width(child.suffix)
            else:
                width += self.suffix_width
            widths.append(width)
        return max(widths)

    @property
    def has_toggles(self) -> bool:
        """Whether any children have toggle state."""
        return any(
            isinstance(c, MenuItem) and c.toggled is not None for c in self.children
        )


class MenuContainer(PtkMenuContainer):
    """Enhanced menu container with extended MenuItem support.

    This class provides a menu container that uses the enhanced MenuBar
    and MenuItem features while maintaining backwards compatibility with
    prompt_toolkit's MenuContainer interface.
    """

    def __init__(
        self,
        body: AnyContainer,
        menu_items: list[MenuItem],
        floats: list[Float] | None = None,
        key_bindings: KeyBindingsBase | None = None,
        grid: type[GridStyle] = ThinGrid,
    ) -> None:
        """Initialize the menu container.

        Args:
            body: The main application body container
            menu_items: List of MenuItem objects for the menu bar
            floats: Additional Float objects to display
            key_bindings: Additional key bindings
            grid: Grid style class for menu borders
        """
        from prompt_toolkit.layout.containers import FloatContainer

        self.body = body
        self.menu_items = menu_items

        # Create the enhanced menu bar
        self._menu_bar = MenuBar(
            menu_items=menu_items,
            grid=grid,
        )

        # Build the main container with menu bar and body
        self.container = FloatContainer(
            content=HSplit(
                [
                    self._menu_bar,
                    body,
                ]
            ),
            floats=[*self._menu_bar.floats, *floats],
            key_bindings=key_bindings,
        )

    @property
    def selected_menu(self) -> list[int]:
        """Get the selected menu indices."""
        return self._menu_bar.selected_menu

    @selected_menu.setter
    def selected_menu(self, value: list[int]) -> None:
        """Set the selected menu indices."""
        self._menu_bar.selected_menu = value

    def _get_menu(self, level: int) -> MenuItem:
        """Get the menu at the specified nesting level."""
        return self._menu_bar._get_menu(level)

    @property
    def floats(self) -> list[Float] | None:
        """Return the float containers."""
        return self.container.floats

    def __pt_container__(self) -> Container:
        """Return the menu container."""
        return self.container


class MenuBar:
    """A container to hold the menubar and main application body."""

    def __init__(
        self,
        menu_items: Sequence[MenuItem],
        grid: GridStyle = OuterHalfGrid,
    ) -> None:
        """Initiate the menu bar.

        Args:
            app: The application the menubar is attached to
            menu_items: The menu items to show in the menubar
            grid: The grid style to use for the menu's borders

        """
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

        self.floats = [
            Float(
                attach_to_window=self.window,
                xcursor=True,
                ycursor=True,
                content=ConditionalContainer(
                    content=Shadow(body=submenu),
                    filter=Condition(lambda: len(self.selected_menu) > 0),
                ),
                z_index=100_000,
            ),
            Float(
                attach_to_window=to_container(submenu).get_children()[1],
                xcursor=True,
                ycursor=True,
                allow_cover_cursor=True,
                content=ConditionalContainer(
                    content=Shadow(body=submenu2),
                    filter=Condition(lambda: len(self.selected_menu) > 1)
                    & Condition(lambda: bool(self._get_menu(1).children)),
                ),
                z_index=100_001,
            ),
            Float(
                attach_to_window=to_container(submenu2).get_children()[1],
                xcursor=True,
                ycursor=True,
                allow_cover_cursor=True,
                content=ConditionalContainer(
                    content=Shadow(body=submenu3),
                    filter=Condition(lambda: len(self.selected_menu) > 2)
                    & Condition(lambda: bool(self._get_menu(2).children)),
                ),
                z_index=100_002,
            ),
        ]

    def refocus(self) -> None:
        """Focus the currently selected menu."""
        layout = get_app().layout
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
