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

from prompt_toolkit.keys import Keys
from prompt_toolkit.widgets.menus import (
    MenuContainer as PtkMenuContainer,
)
from prompt_toolkit.widgets.menus import (
    MenuItem as PtkMenuItem,
)

from apptk.application.current import get_app
from apptk.border import ThinGrid
from apptk.commands import get_cmd
from apptk.filters import Condition, has_focus
from apptk.filters.utils import to_filter
from apptk.formatted_text.base import to_formatted_text
from apptk.formatted_text.utils import (
    fragment_list_width,
    to_plain_text,
)
from apptk.key_binding.key_bindings import KeyBindings
from apptk.layout.containers import (
    ConditionalContainer,
    Container,
    Float,
    FloatContainer,
    HSplit,
    ScrollOffsets,
    StatusContainer,
    VSplit,
    Window,
    to_container,
)
from apptk.layout.controls import FormattedTextControl
from apptk.layout.utils import explode_text_fragments
from apptk.mouse_events import MouseEvent, MouseEventType
from apptk.widgets.base import Shadow

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from typing import Any

    from euporie.core.bars.status import StatusBarFields
    from prompt_toolkit.filters import Filter, FilterOrBool
    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.controls import UIControl

    from apptk.border import GridStyle
    from apptk.commands import Command
    from apptk.formatted_text.base import (
        AnyFormattedText,
        OneStyleAndTextTuple,
        StyleAndTextTuples,
    )


__all__ = [
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
    - Icon support
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
        icon: AnyFormattedText = "",
    ) -> None:
        """Initialize enhanced menu item.

        Args:
            text: Plain text to display (for backwards compatibility)
            handler: Function to call when activated
            children: Submenu items
            shortcut: Keyboard shortcut sequence (for backwards compatibility)
            disabled: Whether item is disabled (bool or Filter)
            description: Description for status bar
            separator: If True, render as separator line
            hidden: Filter to hide this item
            toggled: Filter for toggle state (shows checkmark when True)
            icon: Icon to display before the menu item text
        """
        # Store the formatted text, falling back to plain text
        self._formatted_text = text
        self._icon = icon

        self.description = description

        # Detect separators in a backwards compatible way
        self.separator = (
            all(x == "-" for x in self.text) if separator is None else separator
        )

        # Handle disabled as either bool or Filter
        self._disabled = to_filter(disabled) | to_filter(self.separator)
        self.hidden = to_filter(hidden)
        self.toggled = toggled

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
    def icon(self) -> StyleAndTextTuples:
        """Get icon as formatted text."""
        if self._icon:
            return to_formatted_text(self._icon)
        return []

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
            icon=cmd.icon,
        )


class MenuContainer(PtkMenuContainer):
    """Enhanced menu container with extended MenuItem support.

    This class provides a menu container that uses the enhanced MenuBar
    and MenuItem features while maintaining backwards compatibility with
    prompt_toolkit's MenuContainer interface.
    """

    grid: type[GridStyle] = ThinGrid  # Class attribute default

    def __init__(
        self,
        body: AnyContainer | None = None,
        menu_items: list[MenuItem] | None = None,
        floats: list[Float] | None = None,
        key_bindings: KeyBindingsBase | None = None,
        grid: type[GridStyle] | None = None,
        padding: int = 1,
        max_depth: int = 4,
        collapse_prefix: bool = False,
        collapse_suffix: bool = True,
        icons: FilterOrBool = True,
        shadows: FilterOrBool = True,
    ) -> None:
        """Initialize the menu container.

        Args:
            body: The main application body container
            menu_items: List of MenuItem objects for the menu bar
            floats: Additional Float objects to display
            key_bindings: Additional key bindings
            grid: Grid style class for menu borders
            padding: Padding around menu items
            max_depth: Maximum depth of nested submenus
            collapse_prefix: If True, don't pad prefixes to equal width
            collapse_suffix: If True, don't pad suffixes to equal width
            icons: Whether to show icons in menu items
            shadows: Whether to show drop shadows under menus
        """
        self.body = body
        self.menu_items = menu_items or []
        self.grid = grid or self.__class__.grid
        self.padding = padding
        self.max_depth = max_depth
        self._show_icons = to_filter(icons)
        self.collapse_prefix = collapse_prefix
        self.collapse_suffix = collapse_suffix
        self._shadows = to_filter(shadows)
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
            indices = [
                i
                for i, item in enumerate(menu.children)
                if not item.disabled and not item.hidden()
            ]
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
            if not self._select_previous_item() and len(self.selected_menu) == 2:
                # Return to main menu.
                self.selected_menu.pop()
            self.refocus()

        @kb.add("down", filter=in_sub_menu)
        def _down_in_submenu(event: KeyPressEvent) -> None:
            """Select next (enabled) menu item."""
            if self._select_next_item():
                self.refocus()

        @kb.add("home", filter=in_sub_menu)
        def _home_in_submenu(event: KeyPressEvent) -> None:
            """Select first enabled menu item."""
            menu = self._get_menu(len(self.selected_menu) - 2)
            first_index = next(
                (
                    i
                    for i, item in enumerate(menu.children)
                    if not item.disabled and not item.hidden()
                ),
                None,
            )
            if first_index is not None:
                self.selected_menu[-1] = first_index
                self.refocus()

        @kb.add("end", filter=in_sub_menu)
        def _end_in_submenu(event: KeyPressEvent) -> None:
            """Select last enabled menu item."""
            menu = self._get_menu(len(self.selected_menu) - 2)
            last_index = next(
                (
                    i
                    for i, item in reversed(list(enumerate(menu.children)))
                    if not item.disabled and not item.hidden()
                ),
                None,
            )
            if last_index is not None:
                self.selected_menu[-1] = last_index
                self.refocus()

        @kb.add(Keys.Any, filter=in_sub_menu)
        def _type_ahead(event: KeyPressEvent) -> None:
            """Jump to menu item starting with typed character."""
            char = event.data.lower()
            if not char.isalnum():
                return
            menu = self._get_menu(len(self.selected_menu) - 2)
            current = self.selected_menu[-1]

            # Search from current position, wrapping around
            indices = list(range(current + 1, len(menu.children))) + list(
                range(current + 1)
            )
            for i in indices:
                item = menu.children[i]
                if (
                    not item.disabled
                    and not item.hidden()
                    and item.text.lower().startswith(char)
                ):
                    self.selected_menu[-1] = i
                    self.refocus()
                    break

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
        self.window: Window = Window(height=1, content=self.control, style="class:menu")

        # Build submenus and floats dynamically based on max_depth
        self.menu_containers: list[AnyContainer] = [self.window]
        menu_floats: list[Float] = []

        for depth in range(max_depth):
            submenu = self._submenu(depth)
            self.menu_containers.append(submenu)

            if depth == 0:
                attach_to = self.window
            else:
                attach_to = to_container(self.menu_containers[depth]).get_children()[1]

            menu_floats.append(
                Float(
                    attach_to_window=attach_to,
                    xcursor=True,
                    ycursor=True,
                    allow_cover_cursor=depth > 0,
                    content=ConditionalContainer(
                        content=Shadow(body=submenu, filter=self._shadows),
                        filter=Condition(lambda d=depth: len(self.selected_menu) > d)
                        & Condition(lambda d=depth: bool(self._get_menu(d).children)),
                    ),
                    z_index=100_000 + depth,
                    allow_overflow=True,
                )
            )

        # Build focused filter from all menu containers
        self.focused = has_focus(self.window)
        for container in self.menu_containers[1:]:
            self.focused = self.focused | has_focus(container)

        self.container = FloatContainer(
            content=StatusContainer(
                body=HSplit([self.window, body]) if body else self.window,
                status=self.__pt_status__,
            ),
            floats=menu_floats + (floats or []),
        )

    def _render_prefix(self, item: PtkMenuItem) -> StyleAndTextTuples:
        """Build prefix fragments for a menu item.

        Renders the toggle checkmark or icon depending on item state
        and the container's icon visibility filter.

        Args:
            item: The menu item to render a prefix for.

        Returns:
            Formatted text fragments for the prefix.
        """
        if item.toggled is not None:
            return [("class:prefix", "✓ " if item.toggled() else "  ")]
        elif item.icon and self._show_icons():
            return [*item.icon, ("", " ")]
        return []

    def _render_suffix(self, item: PtkMenuItem) -> StyleAndTextTuples:
        """Build suffix fragments for a menu item.

        Renders the submenu arrow or keyboard shortcut hint.

        Args:
            item: The menu item to render a suffix for.

        Returns:
            Formatted text fragments for the suffix.
        """
        if item.children:
            return [("", "›")]
        shortcut_text = item.shortcut
        if shortcut_text:
            return [
                ("", "  "),
                *to_formatted_text(shortcut_text, style="class:shortcut"),
            ]
        return []

    def _compute_prefix_width(self, menu: PtkMenuItem) -> int:
        """Compute max prefix width across a menu's visible children.

        Args:
            menu: The parent menu item whose children to measure.

        Returns:
            Maximum prefix width in characters.
        """
        return max(
            [
                fragment_list_width(self._render_prefix(c))
                for c in menu.children
                if not c.hidden()
            ]
            + [0]
        )

    def _compute_suffix_width(self, menu: PtkMenuItem) -> int:
        """Compute max suffix width across a menu's visible children.

        Args:
            menu: The parent menu item whose children to measure.

        Returns:
            Maximum suffix width in characters.
        """
        return max(
            [
                fragment_list_width(self._render_suffix(c))
                for c in menu.children
                if not c.hidden()
            ]
            + [0]
        )

    def _compute_menu_width(self, menu: PtkMenuItem) -> int:
        """Compute total width needed for a menu's children.

        Includes text width plus prefix and suffix contributions,
        respecting collapse settings.

        Args:
            menu: The parent menu item whose children to measure.

        Returns:
            Total menu width in characters.
        """
        base_width = menu.width
        if not menu.children:
            return base_width

        prefix_w = self._compute_prefix_width(menu)
        suffix_w = self._compute_suffix_width(menu)

        max_extra = 0
        for child in menu.children:
            if child.hidden():
                continue
            extra = 0
            if self.collapse_prefix:
                extra += fragment_list_width(self._render_prefix(child))
            else:
                extra += prefix_w
            if self.collapse_suffix:
                extra += fragment_list_width(self._render_suffix(child))
            else:
                extra += suffix_w
            max_extra = max(max_extra, extra)

        return base_width + max_extra

    def refocus(self) -> None:
        """Focus the appropriate container based on menu selection state.

        Focuses the submenu at the current selection depth, or restores
        focus to the previously focused control if the menu is closed.
        """
        layout = get_app().layout
        if self.last_focused is None:
            self.last_focused = layout.current_control
        if self.selected_menu:
            depth = min(len(self.selected_menu) - 1, len(self.menu_containers) - 1)
            layout.focus(self.menu_containers[depth])
        elif self.last_focused:
            try:
                layout.focus(self.last_focused)
            except ValueError:
                layout.focus_previous()
            self.last_focused = None

    def _select_previous_item(self) -> bool:
        """Select previous enabled, visible menu item.

        Returns:
            True if selection changed, False otherwise.
        """
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
            return True
        return False

    def _select_next_item(self) -> bool:
        """Select next enabled, visible menu item.

        Returns:
            True if selection changed, False otherwise.
        """
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
            return True
        return False

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
            style = "class:menu-bar.selected-item" if selected else ""
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

                    menu_width = self._compute_menu_width(menu)
                    prefix_width = self._compute_prefix_width(menu)
                    suffix_width = self._compute_suffix_width(menu)

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
                                    return None
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
                                if self._select_previous_item():
                                    return None

                            elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                                if self._select_next_item():
                                    return None

                            return NotImplemented

                        is_separator = item.separator

                        if is_separator:
                            # Show a connected line with no mouse handler
                            yield (
                                "class:menu-border",
                                grid.SPLIT_LEFT
                                + (grid.SPLIT_MID * (menu_width + self.padding * 2))
                                + grid.SPLIT_RIGHT,
                            )

                        else:
                            item_prefix = self._render_prefix(item)
                            item_suffix = self._render_suffix(item)
                            item_prefix_width = fragment_list_width(item_prefix)
                            item_suffix_width = fragment_list_width(item_suffix)

                            # Show the left edge
                            style = ""
                            # Set the style if disabled
                            if item.disabled:
                                style += "class:disabled"
                            # Set the style and cursor if selected
                            if i == selected_item:
                                style += "class:menu-bar.selected-item"
                            yield (f"{style} class:menu-border", grid.MID_LEFT)
                            if i == selected_item:
                                yield ("[SetCursorPosition]", "")
                            # Construct the menu item contents
                            item_text: StyleAndTextTuples = item.formatted_text
                            item_text_width = fragment_list_width(item_text)
                            prefix_pad = " " * (
                                0
                                if self.collapse_prefix
                                else prefix_width - item_prefix_width
                            )
                            effective_suffix_width = (
                                item_suffix_width
                                if self.collapse_suffix
                                else suffix_width
                            )
                            suffix_pad = " " * (
                                menu_width
                                - item_prefix_width
                                - len(prefix_pad)
                                - item_text_width
                                - effective_suffix_width
                            )
                            text_pad = " " * (
                                menu_width
                                - item_prefix_width
                                - len(prefix_pad)
                                - item_text_width
                                - item_suffix_width
                                - len(suffix_pad)
                                - self.padding * 2
                            )
                            menu_formatted_text: StyleAndTextTuples = to_formatted_text(
                                [
                                    ("", " " * self.padding),
                                    *item_prefix,
                                    ("", prefix_pad),
                                    *item_text,
                                    ("", text_pad),
                                    ("", suffix_pad),
                                    *item_suffix,
                                    ("", " " * self.padding),
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
                            yield (f"{style} class:menu-border", grid.MID_RIGHT)

                    visible_children = [x for x in menu.children if not x.hidden()]
                    for i, item in enumerate(visible_children):
                        result.extend(one_item(i, item))
                        if i < len(visible_children) - 1:
                            result.append(("", "\n"))

            return result

        return HSplit(
            [
                VSplit(
                    [
                        Window(char=grid.TOP_LEFT, width=1, height=1),
                        Window(char=grid.TOP_MID, height=1),
                        Window(char=grid.TOP_RIGHT, width=1, height=1),
                    ],
                    style="class:menu-border",
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
                    style="class:menu-border",
                ),
            ],
            style="class:menu",
        )

    def __pt_container__(self) -> Container:
        """Return the menu bar container's content."""
        return self.container

    def __pt_status__(self) -> StatusBarFields:
        """Return the description of the currently selected menu item."""
        selected_item = self._get_menu(len(self.selected_menu) - 1)
        return ([selected_item.description], [])
