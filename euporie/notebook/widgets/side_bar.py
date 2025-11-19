"""Define a side-bar."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding.key_bindings import (
    KeyBindings,
)
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.screen import WritePosition
from prompt_toolkit.mouse_events import MouseButton, MouseEventType

from euporie.core.app.current import get_app
from euporie.core.key_binding.registry import register_bindings
from euporie.core.layout.decor import FocusedStyle, Line
from euporie.core.widgets.forms import ToggleButton, ToggleButtons

if TYPE_CHECKING:
    from collections.abc import Sequence

    from prompt_toolkit.key_binding.key_bindings import (
        KeyBindingsBase,
        NotImplementedOrNone,
    )
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.mouse_events import MouseEvent


class SidebarResizeHandleControl(UIControl):
    """A draggable vertical bar to resize the sidebar."""

    def __init__(self, sidebar: SideBar) -> None:
        """Initialize the resize handle control.

        Args:
            sidebar: The sidebar instance to resize.
        """
        self.sidebar = sidebar
        self.drag_start_x: int | None = None
        self.start_width = sidebar.sidebar_width
        self.sidebar_resize_window: Window | None = None

    def create_content(self, width: int, height: int | None) -> UIContent:
        """Create the content for the resize handle.

        Args:
            width: The width of the control.
            height: The height of the control.

        Returns:
            The UI content to display.
        """
        return UIContent(
            get_line=lambda i: [("class:side_bar,border", "▏")],
            line_count=height if height is not None else 1,
            show_cursor=False,
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle mouse events for resizing the sidebar.

        Args:
            mouse_event: The mouse event to handle.

        Returns:
            None if the event was handled, NotImplemented otherwise.
        """
        if (
            self.sidebar_resize_window is not None
            and (info := self.sidebar_resize_window.render_info) is not None
        ):
            app = get_app()
            gx, _ = app.mouse_position

            if mouse_event.button == MouseButton.LEFT:
                if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                    # Start the drag event
                    self.drag_start_x = gx
                    self.start_width = self.sidebar.sidebar_width
                    # Send all mouse events to this position
                    y_min, x_min = min(info._rowcol_to_yx.values())
                    y_max, x_max = max(info._rowcol_to_yx.values())
                    app.mouse_limits = WritePosition(
                        xpos=x_min,
                        ypos=y_min,
                        width=x_max - x_min,
                        height=y_max - y_min,
                    )
                    return None
                elif mouse_event.event_type == MouseEventType.MOUSE_MOVE:
                    if self.drag_start_x is not None:
                        # Calculate width change based on global mouse position
                        dx = gx - self.drag_start_x
                        new_width = max(10, self.start_width + dx)
                        self.sidebar.sidebar_width = new_width
                        # change the mouse capture position
                        if app.mouse_limits is not None:
                            app.mouse_limits.xpos = self.drag_start_x + dx
                        return None
            # End the drag event
            self.drag_start_x = None
            # Stop capturing all mouse events
            app.mouse_limits = None
            return None

        return NotImplemented


class SideBarButtons(ToggleButtons):
    """Vertical toggle-buttons with additional styling for the side-bar."""

    def _get_sep_style(self, i: int) -> str:
        if self.index == i:
            return "class:side_bar,buttons,separator,selection,after"
        elif self.index == i - 1:
            return "class:side_bar,buttons,separator,selection,before"
        else:
            return "class:side_bar,buttons,separator"

    def _get_sep_char(self, i: int) -> str:
        if self.index in {i, i - 1}:
            return "▄"
        return ""

    def key_bindings(self) -> KeyBindingsBase:
        """Return key-bindings for the drop-down widget."""
        kb = KeyBindings()

        @kb.add("up")
        def _(event: KeyPressEvent) -> None:
            self.hovered = max(0, min((self.hovered or 0) - 1, len(self.options) - 1))
            get_app().layout.focus(self.buttons[self.hovered])

        @kb.add("down")
        def _(event: KeyPressEvent) -> None:
            self.hovered = max(0, min((self.hovered or 0) + 1, len(self.options) - 1))
            get_app().layout.focus(self.buttons[self.hovered])

        @kb.add("home")
        def _(event: KeyPressEvent) -> None:
            self.hovered = 0
            get_app().layout.focus(self.buttons[self.hovered])

        @kb.add("end")
        def _(event: KeyPressEvent) -> None:
            self.hovered = len(self.options) - 1
            get_app().layout.focus(self.buttons[self.hovered])

        return kb

    def load_container(self) -> AnyContainer:
        """Load the widget's container."""
        self.buttons: list[ToggleButton] = []
        children: list[AnyContainer] = []
        for i, (label, selected) in enumerate(zip(self.labels, self.mask)):
            children.append(
                Window(
                    char=partial(self._get_sep_char, i),
                    height=1,
                    style=partial(self._get_sep_style, i),
                )
            )
            button = ToggleButton(
                text=label,
                selected=selected,
                on_click=partial(lambda index, button: self.toggle_item(index), i),
                border=None,
                style=self.get_button_style(i),
                disabled=self.disabled,
            )
            self.buttons.append(button)
            children.append(FocusedStyle(button))
        children.extend(
            [
                Window(
                    char=partial(self._get_sep_char, i),
                    height=1,
                    style=partial(self._get_sep_style, len(self.options)),
                ),
                Window(),
            ]
        )
        self.on_change += self.update_buttons
        return HSplit(
            children,
            style="class:toggle-buttons",
            key_bindings=self.key_bindings(),
        )


class SideBar:
    """A side-bar for the notebook application."""

    def __init__(
        self,
        titles: Sequence[str],
        icons: Sequence[str],
        panels: Sequence[AnyContainer],
    ) -> None:
        """Initialize a new side-bar object.

        Args:
            titles: Titles for each panel.
            icons: Icons for each panel button.
            panels: The panel containers to display.
        """
        from euporie.core.app.current import get_app

        self.sidebar_width = 25
        self.side_bar_buttons = SideBarButtons(
            options=list(icons),
            style="class:buttons",
            vertical=True,
            border=None,
            multiple=True,
            max_count=1,
        )
        pane_hidden = Condition(lambda: bool(self.side_bar_buttons.index is None))

        # Create the resize handle for the sidebar border
        resize_handle_control = SidebarResizeHandleControl(self)
        resize_handle = Window(
            content=resize_handle_control,
            width=1,
            style="class:side_bar,border",
        )
        # Give the control a reference to its window for render_info
        resize_handle_control.sidebar_resize_window = resize_handle

        self.container = ConditionalContainer(
            VSplit(
                [
                    VSplit(
                        [
                            self.side_bar_buttons,
                            ConditionalContainer(
                                Line(
                                    char="▏",
                                    width=1,
                                    collapse=False,
                                    style="class:side_bar,border,outer",
                                ),
                                filter=pane_hidden,
                            ),
                        ],
                    ),
                    ConditionalContainer(
                        VSplit(
                            [
                                Line(
                                    char="▏",
                                    width=1,
                                    style="class:side_bar,border",
                                ),
                                HSplit(
                                    [
                                        DynamicContainer(
                                            lambda: panels[
                                                self.side_bar_buttons.index or 0
                                            ]
                                        ),
                                    ],
                                    width=lambda: Dimension(
                                        preferred=self.sidebar_width
                                    ).preferred,
                                ),
                                resize_handle,
                            ],
                        ),
                        filter=~pane_hidden,
                    ),
                ],
                style="class:side_bar",
            ),
            filter=get_app().config.filters.show_side_bar,
        )

    def toggle_pane(self) -> None:
        """Toggle the visibility of the side-bar."""
        if self.side_bar_buttons.index is None:
            self.side_bar_buttons.index = 0
        else:
            self.side_bar_buttons.index = None

    def __pt_container__(self) -> AnyContainer:
        """Return the side_bar's main container."""
        return self.container

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.notebook.app:NotebookApp": {
                "toggle-side-bar-pane": "c-b",
            }
        }
    )
