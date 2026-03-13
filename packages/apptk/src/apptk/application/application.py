"""Overrides for prompt_toolkit applications."""

from __future__ import annotations

import asyncio
import io
import logging
import os
from typing import TYPE_CHECKING, Generic

from apptk.application.current import set_app
from apptk.data_structures import Point
from apptk.enums import EditingMode
from apptk.filters import to_filter
from apptk.input.vt100 import Vt100Input
from apptk.key_binding.helix_state import HelixState
from apptk.key_binding.key_bindings import (
    KeyBindingsBase,
)
from apptk.key_binding.micro_state import MicroState
from apptk.output.vt100 import Vt100_Output
from apptk.utils import Event
from prompt_toolkit.application.application import (
    Application as PtkApplication,
)
from prompt_toolkit.application.application import _AppResult
from prompt_toolkit.application.application import (
    _CombinedRegistry as _PtkCombinedRegistry,
)
from prompt_toolkit.enums import EditingMode as PtkEditingMode

if TYPE_CHECKING:
    from collections.abc import Callable

    from apptk.clipboard import Clipboard
    from apptk.cursor_shapes import AnyCursorShapeConfig
    from apptk.filters import FilterOrBool
    from apptk.input.base import Input
    from apptk.key_binding.key_bindings import KeyBindingsBase
    from apptk.layout.layout import Layout
    from apptk.layout.screen import WritePosition
    from apptk.output import ColorDepth, Output
    from apptk.styles import (
        BaseStyle,
        StyleTransformation,
    )
    from prompt_toolkit.application.application import ApplicationEventHandler
    from prompt_toolkit.key_binding import KeyBindingsBase as PtkKeyBindingsBase
    from prompt_toolkit.layout import UIControl as PtkUIControl
    from prompt_toolkit.layout.containers import Window as PtkWindow

log = logging.getLogger(__name__)


class Application(PtkApplication, Generic[_AppResult]):
    """Overrides for application."""

    def __init__(  # noqa: D417
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
        on_color_change: ApplicationEventHandler[_AppResult] | None = None,
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
            editing_mode=PtkEditingMode(editing_mode.value),
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
        # Additional editing mode states
        self.micro_state = MicroState()
        self.helix_state = HelixState()

        # Events
        self.on_color_change = Event(self, on_color_change)

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

    async def run_async(
        self,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
        slow_callback_duration: float = 0.5,
    ) -> _AppResult:
        """Run the application."""
        if isinstance(self.output, Vt100_Output) and isinstance(self.input, Vt100Input):
            from apptk.key_binding.bindings import terminal as terminal_bindings

            with set_app(self):
                # Send terminal feature queries
                self.output.ask_for_colors()
                self.output.ask_for_pixel_size()
                self.output.ask_for_kitty_graphics_status()
                self.output.ask_for_device_attributes()
                self.output.ask_for_iterm_graphics_status()
                self.output.ask_for_sgr_pixel_status()
                self.output.ask_for_csiu_status()
                # Send a DSR sentinel query last — the terminal will respond
                # with ``\x1b[0n``, letting us know all prior responses have
                # been received.
                self.output.ask_for_device_status()

                # Read responses
                kp = self.key_processor
                sentinel = asyncio.Event()
                terminal_bindings._device_status_received = sentinel

                def read_from_input() -> None:
                    kp.feed_multiple(self.input.read_keys())

                try:
                    with self.input.raw_mode(), self.input.attach(read_from_input):
                        # Wait for the sentinel response or a short timeout
                        # for terminals that don't respond
                        try:
                            await asyncio.wait_for(sentinel.wait(), timeout=0.5)
                        except TimeoutError:
                            log.debug("Terminal did not respond to device status query")
                finally:
                    terminal_bindings._device_status_received = None

                kp.process_keys()

        try:
            return await super().run_async(
                pre_run, set_exception_handler, handle_sigint, slow_callback_duration
            )
        finally:
            # Drain pending input after renderer cleanup has disabled mouse tracking etc
            self._drain_pending_input()

    def _drain_pending_input(self) -> None:
        """Drain any pending terminal query responses from stdin.

        When the application sends terminal queries (e.g. for colors, pixel
        size, device attributes), responses may still be in-flight when the app
        exits. If not consumed, these responses appear as garbage text in the
        shell. This method reads and discards any pending bytes from stdin.
        """
        import select

        try:
            fd = self.input.fileno()
        except (AttributeError, io.UnsupportedOperation):
            return
        except NotImplementedError:
            # Occurs when using DummyInput
            return
        try:
            # Read and discard any pending input with a short timeout to allow
            # late-arriving responses to be consumed
            for _ in range(50):  # Safety limit to avoid infinite loop
                readable, _, _ = select.select([fd], [], [], 0.01)
                if not readable:
                    break
                os.read(fd, 4096)
        except (OSError, ValueError):
            pass


class _CombinedRegistry(_PtkCombinedRegistry):
    """The `KeyBindings` of key bindings for a `Application`."""

    def __init__(self, app: Application[_AppResult]) -> None:
        super().__init__(app)
        self.handler_keys = {}

    def _create_key_bindings(
        self, current_window: PtkWindow, other_controls: list[PtkUIControl]
    ) -> PtkKeyBindingsBase:
        key_bindings = super()._create_key_bindings(current_window, other_controls)
        for binding in key_bindings.bindings:
            self.handler_keys.setdefault(binding.handler, []).append(binding.keys)
        return key_bindings
