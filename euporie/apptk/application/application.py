"""Overrides for prompt_toolkit applications."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Generic

from euporie.apptk.key_binding.key_bindings import (
    KeyBindingsBase,
)
from prompt_toolkit.application.application import (
    Application as PtkApplication,
)
from prompt_toolkit.application.application import _AppResult
from prompt_toolkit.application.application import (
    _CombinedRegistry as _PtkCombinedRegistry,
)

from euporie.apptk.data_structures import Point
from euporie.apptk.enums import EditingMode
from euporie.apptk.filters import to_filter
from euporie.apptk.key_binding.micro_state import MicroState
from euporie.apptk.layout.containers import Window
from euporie.apptk.layout.controls import UIControl

if TYPE_CHECKING:
    from collections.abc import Callable

    from euporie.apptk.cursor_shapes import AnyCursorShapeConfig
    from euporie.apptk.key_binding.key_bindings import KeyBindingsBase
    from euporie.apptk.layout.layout import Layout
    from prompt_toolkit.application.application import ApplicationEventHandler

    from euporie.apptk.clipboard import Clipboard
    from euporie.apptk.filters import FilterOrBool
    from euporie.apptk.input.base import Input
    from euporie.apptk.layout.containers import Window
    from euporie.apptk.layout.controls import UIControl
    from euporie.apptk.layout.screen import WritePosition
    from euporie.apptk.output import ColorDepth, Output
    from euporie.apptk.styles import (
        BaseStyle,
        StyleTransformation,
    )

log = logging.getLogger(__name__)


class Application(PtkApplication, Generic[_AppResult]):
    def __init__(
        self,
        layout: Layout | None = None,
        style: BaseStyle | None = None,
        include_default_pygments_style: FilterOrBool = True,
        style_transformation: StyleTransformation | None = None,
        key_bindings: KeyBindingsBase | None = None,
        clipboard: Clipboard | None = None,
        full_screen: bool = False,
        color_depth: (ColorDepth | Callable[[], ColorDepth | None] | None) = None,
        mouse_support: FilterOrBool = False,
        enable_page_navigation_bindings: None
        | (FilterOrBool) = None,  # Can be None, True or False.
        paste_mode: FilterOrBool = False,
        editing_mode: EditingMode = EditingMode.MICRO,
        erase_when_done: bool = False,
        reverse_vi_search_direction: FilterOrBool = False,
        min_redraw_interval: float | int | None = None,
        max_render_postpone_time: float | int | None = 0.01,
        refresh_interval: float | None = None,
        terminal_size_polling_interval: float | None = 0.5,
        cursor: AnyCursorShapeConfig = None,
        on_reset: ApplicationEventHandler[_AppResult] | None = None,
        on_invalidate: ApplicationEventHandler[_AppResult] | None = None,
        before_render: ApplicationEventHandler[_AppResult] | None = None,
        after_render: ApplicationEventHandler[_AppResult] | None = None,
        # I/O.
        input: Input | None = None,
        output: Output | None = None,
        title: str | None = None,
        set_title: bool = True,
        leave_graphics: FilterOrBool = True,
    ) -> None:
        """Extensions to the prompt_toolkit Application class.

        Args:
            title: The title string to set in the terminal
            set_title: Whether to set the terminal title
            leave_graphics: A filter which determines if graphics should be cleared
                from the display when they are no longer active
        """
        super().__init__(
            layout=layout,
            style=style,
            include_default_pygments_style=include_default_pygments_style,
            style_transformation=style_transformation,
            key_bindings=key_bindings,
            clipboard=clipboard,
            full_screen=full_screen,
            color_depth=color_depth,
            mouse_support=mouse_support,
            enable_page_navigation_bindings=enable_page_navigation_bindings,
            paste_mode=paste_mode,
            editing_mode=editing_mode,
            erase_when_done=erase_when_done,
            reverse_vi_search_direction=reverse_vi_search_direction,
            min_redraw_interval=min_redraw_interval,
            max_render_postpone_time=max_render_postpone_time,
            refresh_interval=refresh_interval,
            terminal_size_polling_interval=terminal_size_polling_interval,
            cursor=cursor,
            on_reset=on_reset,
            on_invalidate=on_invalidate,
            before_render=before_render,
            after_render=after_render,
            input=input,
            output=output,
        )
        self.micro_state = MicroState()

        # Graphics
        self.leave_graphics = to_filter(leave_graphics)

        # Set the terminal title
        self.set_title = to_filter(set_title)
        if title:
            self.title = title

        # Set up a write position to limit mouse events to a particular region
        self.mouse_limits: WritePosition | None = None
        self.mouse_position = Point(0, 0)

    @property
    def title(self) -> str:
        """The application's title."""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        """Set the terminal title."""
        self._title = value
        if self.set_title():
            self.output.set_title(value)


class _CombinedRegistry(_PtkCombinedRegistry):
    """The `KeyBindings` of key bindings for a `Application`."""

    def __init__(self, app: Application[_AppResult]) -> None:
        super().__init__(app)
        self.handler_keys = {}

    def _create_key_bindings(
        self, current_window: Window, other_controls: list[UIControl]
    ) -> KeyBindingsBase:
        key_bindings = super()._create_key_bindings(current_window, other_controls)
        for binding in key_bindings.bindings:
            self.handler_keys.setdefault(binding.handler, []).append(binding.keys)
        return key_bindings
