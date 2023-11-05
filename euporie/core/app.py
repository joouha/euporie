"""Contain the main Application class which runs euporie.core."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import signal
import sys
from functools import partial
from pathlib import PurePath
from typing import TYPE_CHECKING, cast
from weakref import WeakSet

from prompt_toolkit.application.application import Application, _CombinedRegistry
from prompt_toolkit.application.current import create_app_session, set_app
from prompt_toolkit.cursor_shapes import CursorShape, CursorShapeConfig
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition, buffer_has_focus, to_filter
from prompt_toolkit.input.defaults import create_input
from prompt_toolkit.key_binding.bindings.basic import (
    load_basic_bindings as load_ptk_basic_bindings,
)
from prompt_toolkit.key_binding.bindings.cpr import load_cpr_bindings
from prompt_toolkit.key_binding.bindings.emacs import (
    load_emacs_bindings,
    load_emacs_search_bindings,
    load_emacs_shift_selection_bindings,
)
from prompt_toolkit.key_binding.bindings.mouse import (
    load_mouse_bindings as load_ptk_mouse_bindings,
)
from prompt_toolkit.key_binding.bindings.vi import (
    load_vi_bindings,
    load_vi_search_bindings,
)
from prompt_toolkit.key_binding.key_bindings import (
    ConditionalKeyBindings,
    merge_key_bindings,
)
from prompt_toolkit.layout.containers import Float, FloatContainer, Window, to_container
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.output.vt100 import Vt100_Output as PtkVt100_Output
from prompt_toolkit.styles import (
    BaseStyle,
    ConditionalStyleTransformation,
    DummyStyle,
    SetDefaultColorStyleTransformation,
    Style,
    SwapLightAndDarkStyleTransformation,
    merge_style_transformations,
    merge_styles,
    style_from_pygments_cls,
)
from pygments.styles import STYLE_MAP as pygments_styles
from pygments.styles import get_style_by_name
from upath import UPath

from euporie.core.clipboard import EuporieClipboard
from euporie.core.commands import add_cmd
from euporie.core.config import Config, add_setting
from euporie.core.convert.mime import get_mime
from euporie.core.current import get_app
from euporie.core.filters import in_tmux, insert_mode, replace_mode, tab_has_focus
from euporie.core.io import Vt100_Output, Vt100Parser
from euporie.core.key_binding.key_processor import KeyProcessor
from euporie.core.key_binding.micro_state import MicroState
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.key_binding.vi_state import ViState
from euporie.core.log import setup_logs
from euporie.core.path import parse_path
from euporie.core.renderer import Renderer
from euporie.core.style import (
    DEFAULT_COLORS,
    HTML_STYLE,
    IPYWIDGET_STYLE,
    LOG_STYLE,
    MIME_STYLE,
    ColorPalette,
    build_style,
)
from euporie.core.terminal import TerminalInfo
from euporie.core.utils import ChainedList
from euporie.core.widgets.decor import Shadow
from euporie.core.widgets.menu import CompletionsMenu

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from pathlib import Path
    from types import FrameType
    from typing import Any, Callable, TypeVar

    # from prompt_toolkit.application import _AppResult
    from prompt_toolkit.clipboard import Clipboard
    from prompt_toolkit.contrib.ssh import PromptToolkitSSHSession
    from prompt_toolkit.enums import EditingMode
    from prompt_toolkit.filters import Filter, FilterOrBool
    from prompt_toolkit.input import Input
    from prompt_toolkit.layout.layout import FocusableElement
    from prompt_toolkit.layout.screen import WritePosition
    from prompt_toolkit.output import Output

    from euporie.core.config import Setting
    from euporie.core.tabs.base import Tab
    from euporie.core.terminal import TerminalQuery
    from euporie.core.widgets.dialog import Dialog
    from euporie.core.widgets.pager import Pager
    from euporie.core.widgets.search_bar import SearchBar

    _AppResult = TypeVar("_AppResult")

log = logging.getLogger(__name__)


_COLOR_DEPTHS = {
    1: ColorDepth.DEPTH_1_BIT,
    4: ColorDepth.DEPTH_4_BIT,
    8: ColorDepth.DEPTH_8_BIT,
    24: ColorDepth.DEPTH_24_BIT,
}


class CursorConfig(CursorShapeConfig):
    """Determine which cursor mode to use."""

    def get_cursor_shape(self, app: Application[Any]) -> CursorShape:
        """Return the cursor shape to be used in the current state."""
        if isinstance(app, BaseApp) and app.config.set_cursor_shape:
            if insert_mode():
                if app.config.cursor_blink:
                    return CursorShape.BLINKING_BEAM
                else:
                    return CursorShape.BEAM
            elif replace_mode():
                if app.config.cursor_blink:
                    return CursorShape.BLINKING_UNDERLINE
                else:
                    return CursorShape.UNDERLINE
        return CursorShape.BLOCK

    # ################################### Settings ####################################w

    add_setting(
        name="set_cursor_shape",
        flags=["--set-cursor-shape"],
        type_=bool,
        default=True,
        menu_title="Change cursor shape",
        help_="Whether to set the shape of the cursor depending on the editing mode",
        description="""
            When set to True, the euporie will set the shape of the terminal's cursor
            to a beam in insert mode and and underline in replace mode when editing.
    """,
    )
    add_setting(
        name="cursor_blink",
        flags=["--cursor-blink"],
        type_=bool,
        default=False,
        help_="Whether to blink the cursor",
        description="""
            When set to True, the cursor will blink.
    """,
    )


class BaseApp(Application):
    """All euporie apps.

    The base euporie application class.

    This subclasses the `prompt_toolkit.application.Application` class, so application
    wide methods can be easily added.
    """

    name: str
    color_palette: ColorPalette
    mouse_position: Point

    config = Config()
    need_mouse_support: bool = False
    log_stdout_level: str = "CRITICAL"

    def __init__(
        self,
        title: str | None = None,
        set_title: bool = True,
        leave_graphics: FilterOrBool = True,
        extend_renderer_height: FilterOrBool = False,
        extend_renderer_width: FilterOrBool = False,
        **kwargs: Any,
    ) -> None:
        """Instantiate euporie specific application variables.

        After euporie specific application variables are instantiated, the application
        instance is initiated.

        Args:
            title: The title string to set in the terminal
            set_title: Whether to set the terminal title
            leave_graphics: A filter which determines if graphics should be cleared
                from the display when they are no longer active
            extend_renderer_height: Whether the renderer height should be extended
                beyond the height of the display
            extend_renderer_width: Whether the renderer width should be extended
                beyond the height of the display
            kwargs: The key-word arguments for the :py:class:`Application`

        """
        # Initialise the application
        super().__init__(
            **{
                "color_depth": self.config.color_depth,
                "editing_mode": self.get_edit_mode(),
                "mouse_support": Condition(lambda: self.need_mouse_support),
                "cursor": CursorConfig(),
                **kwargs,
            }
        )
        # Use custom renderer
        self.renderer = Renderer(
            self._merged_style,
            self.output,
            full_screen=self.full_screen,
            mouse_support=self.mouse_support,
            cpr_not_supported_callback=self.cpr_not_supported_callback,
            extend_height=extend_renderer_height,
            extend_width=extend_renderer_width,
        )
        # Contains the opened tab containers
        self.tabs: list[Tab] = []
        # Holds the search bar to pass to cell inputs
        self.search_bar: SearchBar | None = None
        # Holds the index of the current tab
        self._tab_idx = 0
        # Add state for micro key-bindings
        self.micro_state = MicroState()
        # Load the terminal information system
        self.term_info = TerminalInfo(self.input, self.output, self.config)
        # Floats at the app level
        self.leave_graphics = to_filter(leave_graphics)
        self.graphics: WeakSet[Float] = WeakSet()
        self.dialogs: dict[str, Dialog] = {}
        self.menus: dict[str, Float] = {}
        self.floats = ChainedList(
            self.graphics,
            self.dialogs.values(),
            self.menus.values(),
        )
        # Continue loading when the application has been launched
        # and an event loop has been created
        self.pre_run_callables = [self.pre_run]
        self.post_load_callables: list[Callable[[], None]] = []
        # Set default vi input mode to navigate
        self.vi_state = ViState()
        # Set a long timeout for mappings (e.g. dd)
        self.timeoutlen = 1.0
        # Set a short timeout for flushing input
        self.ttimeoutlen = 0.0
        # Use a custom key-processor which does not wait after escape keys
        self.key_processor = KeyProcessor(_CombinedRegistry(self))
        # List of key-bindings groups to load
        self.bindings_to_load = [
            "euporie.core.app.BaseApp",
            "euporie.core.terminal.TerminalInfo",
        ]
        # Determines which clipboard mechanism to use
        self.clipboard: Clipboard = EuporieClipboard(self)
        # Allow hiding element when manually redrawing app
        self._redrawing = False
        self.redrawing = Condition(lambda: self._redrawing)
        # Add an optional pager
        self.pager: Pager | None = None
        # Stores the initially focused element
        self.focused_element: FocusableElement | None = None
        # Set the terminal title
        self.set_title = to_filter(set_title)
        self.title = title or self.__class__.__name__
        # Register config hooks
        self.config.get_item("edit_mode").event += self.update_edit_mode
        self.config.get_item("syntax_theme").event += self.update_style
        self.config.get_item("color_scheme").event += self.update_style
        self.config.get_item("log_level").event += lambda x: setup_logs(self.config)
        self.config.get_item("log_file").event += lambda x: setup_logs(self.config)
        self.config.get_item("log_config").event += lambda x: setup_logs(self.config)
        self.config.get_item("color_depth").event += lambda x: setattr(
            self, "_color_depth", _COLOR_DEPTHS[x.value]
        )
        # Set up the color palette
        self.color_palette = ColorPalette()
        self.color_palette.add_color("fg", "#ffffff", "default")
        self.color_palette.add_color("bg", "#000000", "default")
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

    def pause_rendering(self) -> None:
        """Block rendering, but allows input to be processed.

        The first line prevents the display being drawn, and the second line means
        the key processor continues to process keys. We need this as we need to
        wait for the results of terminal queries which come in as key events.

        This is used to prevent flicker when we update the styles based on terminal
        feedback.
        """
        self._is_running = False
        self.renderer._waiting_for_cpr_futures.append(asyncio.Future())

    def resume_rendering(self) -> None:
        """Reume rendering the app."""
        self._is_running = True
        if futures := self.renderer._waiting_for_cpr_futures:
            futures.pop()

    def pre_run(self, app: Application | None = None) -> None:
        """Call during the 'pre-run' stage of application loading."""
        # Determine what color depth to use
        self._color_depth = _COLOR_DEPTHS.get(
            self.config.color_depth, self.term_info.depth_of_color.value
        )
        # Set the application's style, and update it when the terminal responds
        self.update_style()
        self.term_info.colors.event += self.update_style
        # Load completions menu. This must be done after the app is set, because
        # :py:func:`get_app` is needed to access the config
        self.menus["completions"] = Float(
            content=Shadow(CompletionsMenu()),
            xcursor=True,
            ycursor=True,
        )
        # Open any files we need to
        self.open_files()
        # Load the layout
        # We delay this until we have terminal responses to allow terminal graphics
        # support to be detected first
        self.layout = Layout(self.load_container(), self.focused_element)

    async def run_async(
        self,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
        slow_callback_duration: float = 0.5,
    ) -> _AppResult:
        """Run the application."""
        with set_app(self):
            # Load key bindings
            self.load_key_bindings()

            # Send queries to the terminal
            self.term_info.send_all()

            # Read responses
            kp = self.key_processor

            def read_from_input() -> None:
                kp.feed_multiple(self.input.read_keys())

            with self.input.raw_mode(), self.input.attach(read_from_input):
                # Wait up to half a second for the terminal to respond to queries
                await asyncio.sleep(0.5)

            kp.process_keys()

        return await super().run_async(
            pre_run, set_exception_handler, handle_sigint, slow_callback_duration
        )

    @classmethod
    def load_input(cls) -> Input:
        """Create the input for this application to use.

        Ensures the TUI app always tries to run in a TTY.

        Returns:
            A prompt-toolkit input instance

        """
        input_ = create_input(always_prefer_tty=True)

        if (stdin := getattr(input_, "stdin", None)) and not stdin.isatty():
            from euporie.core.io import IgnoredInput

            input_ = IgnoredInput()

        # Use a custom vt100 parser to allow querying the terminal
        if parser := getattr(input_, "vt100_parser", None):
            setattr(  # noqa B010
                input_, "vt100_parser", Vt100Parser(parser.feed_key_callback)
            )

        return input_

    @classmethod
    def load_output(cls) -> Output:
        """Create the output for this application to use.

        Ensures the TUI app always tries to run in a TTY.

        Returns:
            A prompt-toolkit output instance

        """
        output = create_output(always_prefer_tty=True)

        if isinstance(output, PtkVt100_Output):
            output = Vt100_Output(
                stdout=output.stdout,
                get_size=output._get_size,
                term=output.term,
                default_color_depth=output.default_color_depth,
                enable_bell=output.enable_bell,
            )

        return output

    def post_load(self) -> None:
        """Allow subclasses to define additional loading steps."""
        # Call extra callables
        for cb in self.post_load_callables:
            cb()

    def load_key_bindings(self) -> None:
        """Load the application's key bindings."""
        from euporie.core.key_binding.bindings.basic import load_basic_bindings
        from euporie.core.key_binding.bindings.micro import load_micro_bindings
        from euporie.core.key_binding.bindings.mouse import load_mouse_bindings

        self._default_bindings = merge_key_bindings(
            [
                # Make sure that the above key bindings are only active if the
                # currently focused control is a `BufferControl`. For other controls, we
                # don't want these key bindings to intervene. (This would break "ptterm"
                # for instance, which handles 'Keys.Any' in the user control itself.)
                ConditionalKeyBindings(
                    merge_key_bindings(
                        [
                            # Load basic bindings.
                            load_ptk_basic_bindings(),
                            load_basic_bindings(),
                            # Load micro bindings
                            load_micro_bindings(config=self.config),
                            # Load emacs bindings.
                            load_emacs_bindings(),
                            load_emacs_search_bindings(),
                            load_emacs_shift_selection_bindings(),
                            # Load Vi bindings.
                            load_vi_bindings(),
                            load_vi_search_bindings(),
                        ]
                    ),
                    buffer_has_focus,
                ),
                # Active, even when no buffer has been focused.
                load_ptk_mouse_bindings(),
                load_cpr_bindings(),
                # Load extra mouse bindings
                load_mouse_bindings(),
                # Load terminal query response key bindings
                # load_command_bindings("terminal"),
            ]
        )
        self.key_bindings = load_registered_bindings(
            *self.bindings_to_load, config=self.config
        )

    def _on_resize(self) -> None:
        """Query the terminal dimensions on a resize event."""
        self.term_info.pixel_dimensions.send()
        super()._on_resize()

    @classmethod
    def launch(cls) -> None:
        """Launch the app."""
        # Load default logging
        setup_logs()
        # Load the app's configuration
        cls.config.load(cls)
        # Configure the logs
        setup_logs(cls.config)
        # Warn about unrecognised configuration items
        cls.config.warn()
        # Run the application
        with create_app_session(input=cls.load_input(), output=cls.load_output()):
            # Create an instance of the app and run it

            original_sigterm = signal.getsignal(signal.SIGTERM)
            original_sigint = signal.getsignal(signal.SIGINT)

            app = cls()

            signal.signal(signal.SIGTERM, app.cleanup)
            signal.signal(signal.SIGINT, app.cleanup)

            result = app.run()

            signal.signal(signal.SIGTERM, original_sigterm)
            signal.signal(signal.SIGINT, original_sigint)

            return result

    def cleanup(self, signum: int, frame: FrameType | None) -> None:
        """Restore the state of the terminal on unexpected exit."""
        log.critical("Unexpected exit signal, restoring terminal")
        output = self.output
        self.exit()
        # Reset terminal state
        # output.quit_alternate_screen()
        # output.disable_mouse_support()
        output.reset_cursor_key_mode()
        output.enable_autowrap()
        # output.disable_bracketed_paste()
        output.clear_title()
        # output.reset_cursor_shape()
        output.show_cursor()
        output.reset_attributes()
        self.renderer.reset()
        # Exit the main thread
        sys.exit(1)

    @classmethod
    async def interact(cls, ssh_session: PromptToolkitSSHSession) -> None:
        """Run the app asynchronously for the hub SSH server."""
        await cls().run_async()

    def load_container(self) -> FloatContainer:
        """Load the root container for this application.

        Returns:
            The root container for this app

        """
        return FloatContainer(
            content=self.layout.container or Window(),
            floats=cast("list[Float]", self.floats),
        )

    def get_file_tabs(self, path: Path) -> list[type[Tab]]:
        """Return the tab to use for a file path."""
        from euporie.core.tabs.base import Tab

        path_mime = get_mime(path) or "text/plain"
        log.debug("File %s has mime type: %s", path, path_mime)

        tab_options = set()
        for tab_cls in Tab._registry:
            for mime_type in tab_cls.mime_types:
                if PurePath(path_mime).match(mime_type):
                    tab_options.add(tab_cls)
            if path.suffix in tab_cls.file_extensions:
                tab_options.add(tab_cls)

        return sorted(tab_options, key=lambda x: x.weight, reverse=True)

    def get_file_tab(self, path: Path) -> type[Tab] | None:
        """Return the tab to use for a file path."""
        if tabs := self.get_file_tabs(path):
            return tabs[0]
        return None

    def open_file(
        self, path: Path, read_only: bool = False, tab_class: type[Tab] | None = None
    ) -> None:
        """Create a tab for a file.

        Args:
            path: The file path of the notebook file to open
            read_only: If true, the file should be opened read_only
            tab_class: The tab type to use to open the file

        """
        ppath = parse_path(path)
        log.info("Opening file %s", path)
        for tab in self.tabs:
            if ppath == getattr(tab, "path", "") and (
                tab_class is None or isinstance(tab, tab_class)
            ):
                log.info("File %s already open, activating", path)
                self.layout.focus(tab)
                break
        else:
            if tab_class is None:
                tab_class = self.get_file_tab(path)
            if tab_class is None:
                log.error("Unable to display file %s", path)
            else:
                tab = tab_class(self, ppath)
                self.tabs.append(tab)
                # Ensure the opened tab is focused at app start
                self.focused_element = tab
                # Ensure the newly opened tab is selected
                self.tab_idx = len(self.tabs) - 1

    def open_files(self) -> None:
        """Open the files defined in the configuration."""
        for file in self.config.files:
            self.open_file(file)

    @property
    def tab(self) -> Tab | None:
        """Return the currently selected tab container object."""
        if self.tabs:
            # Detect if focused tab has changed
            # Find index of selected child
            for i, tab in enumerate(self.tabs):
                if self.render_counter > 0 and self.layout.has_focus(tab):
                    self._tab_idx = i
                    break
            self._tab_idx = max(0, min(self._tab_idx, len(self.tabs) - 1))
            return self.tabs[self._tab_idx]
        else:
            return None

    @property
    def tab_idx(self) -> int:
        """Get the current tab index."""
        return self._tab_idx

    @tab_idx.setter
    def tab_idx(self, value: int) -> None:
        """Set the current tab by index."""
        self._tab_idx = value % (len(self.tabs) or 1)
        if self.tabs:
            with contextlib.suppress(ValueError):
                self.layout.focus(self.tabs[self._tab_idx])

    def focus_tab(self, tab: Tab) -> None:
        """Make a tab visible and focuses it."""
        self.tab_idx = self.tabs.index(tab)

    def cleanup_closed_tab(self, tab: Tab) -> None:
        """Remove a tab container from the current instance of the app.

        Args:
            tab: The closed instance of the tab container

        """
        # Remove tab
        if tab in self.tabs:
            self.tabs.remove(tab)
        # Update body container to reflect new tab list
        # assert isinstance(self.body_container.body, HSplit)
        # self.body_container.body.children[0] = VSplit(self.tabs)
        # Focus another tab if one exists
        if self.tab:
            self.layout.focus(self.tab)
        # If a tab is not open, the status bar is not shown, so focus the logo, so
        # pressing tab focuses the menu
        else:
            with contextlib.suppress(ValueError):
                self.layout.focus_next()

    def close_tab(self, tab: Tab | None = None) -> None:
        """Close a notebook tab.

        Args:
            tab: The instance of the tab to close. If `None`, the currently
                selected tab will be closed.

        """
        if tab is None:
            tab = self.tab
        if tab is not None:
            tab.close(cb=partial(self.cleanup_closed_tab, tab))

    def get_edit_mode(self) -> EditingMode:
        """Return the editing mode enum defined in the configuration."""
        from euporie.core.key_binding.bindings.micro import EditingMode

        return {
            "micro": EditingMode.MICRO,  # type: ignore
            "vi": EditingMode.VI,
            "emacs": EditingMode.EMACS,
        }.get(
            str(self.config.edit_mode),
            EditingMode.MICRO,  # type: ignore
        )

    def update_edit_mode(self, setting: Setting | None = None) -> None:
        """Set the keybindings for editing mode."""
        self.editing_mode = self.get_edit_mode()
        log.debug("Editing mode set to: %s", self.editing_mode)

    def create_merged_style(self) -> BaseStyle:
        """Generate a new merged style for the application.

        Using a dynamic style has serious performance issues, so instead we update
        the style on the renderer directly when it changes in `self.update_style`

        Returns:
            Return a combined style to use for the application

        """
        # Get foreground and background colors based on the configured colour scheme
        theme_colors: dict[str, dict[str, str]] = {
            "default": {},
            "light": {"fg": "#202020", "bg": "#F0F0F0"},
            "dark": {"fg": "#F0F0F0", "bg": "#202020"},
            "white": {"fg": "#000000", "bg": "#FFFFFF"},
            "black": {"fg": "#FFFFFF", "bg": "#000000"},
            # TODO - use config.custom_colors
            "custom": {
                "fg": self.config.custom_foreground_color,
                "bg": self.config.custom_background_color,
            },
        }
        base_colors: dict[str, str] = {
            **DEFAULT_COLORS,
            **self.term_info.colors.value,
            **theme_colors.get(self.config.color_scheme, theme_colors["default"]),
        }

        # Build a color palette from the fg/bg colors
        self.color_palette = ColorPalette()
        for name, color in base_colors.items():
            self.color_palette.add_color(
                name,
                color or theme_colors["default"][name],
                "default" if name in ("fg", "bg") else name,
            )
        # Add accent color
        self.color_palette.add_color(
            "hl", base_colors.get(self.config.accent_color, self.config.accent_color)
        )

        # Build app style
        app_style = build_style(self.color_palette)

        # Apply style transformations based on the configured color scheme
        self.style_transformation = merge_style_transformations(
            [
                ConditionalStyleTransformation(
                    SetDefaultColorStyleTransformation(
                        fg=base_colors["fg"], bg=base_colors["bg"]
                    ),
                    self.config.color_scheme != "default",
                ),
                ConditionalStyleTransformation(
                    SwapLightAndDarkStyleTransformation(),
                    self.config.color_scheme == "inverse",
                ),
            ]
        )

        return merge_styles(
            [
                style_from_pygments_cls(get_style_by_name(self.config.syntax_theme)),
                Style(MIME_STYLE),
                Style(HTML_STYLE),
                Style(LOG_STYLE),
                Style(IPYWIDGET_STYLE),
                app_style,
            ]
        )

    def update_style(
        self,
        query: TerminalQuery | Setting | None = None,
    ) -> None:
        """Update the application's style when the syntax theme is changed."""
        self.renderer.style = self.create_merged_style()

    def refresh(self) -> None:
        """Reet all tabs."""
        for tab in self.tabs:
            to_container(tab).reset()

    def _create_merged_style(
        self, include_default_pygments_style: Filter | None = None
    ) -> BaseStyle:
        """Block default style loading."""
        return DummyStyle()

    def draw(self, render_as_done: bool = True) -> None:
        """Draw the app without focus, leaving the cursor below the drawn output."""
        # Hide ephemeral containers
        self._redrawing = True
        # Ensure nothing in the layout has focus
        self.layout._stack.append(Window())
        # Re-draw the app
        self._redraw(render_as_done=render_as_done)
        # Remove the focus block
        self.layout._stack.pop()
        # Show ephemeral containers
        self._redrawing = False
        # Ensure the renderer knows where the cursor is
        self._request_absolute_cursor_position()

    def _handle_exception(
        self, loop: AbstractEventLoop, context: dict[str, Any]
    ) -> None:
        exception = context.get("exception")
        # Log observed exceptions to the log
        log.exception("An unhandled exception occurred", exc_info=exception)

    # async def cancel_and_wait_for_background_tasks(self) -> "None":
    # """Cancel background tasks, ignoring exceptions."""
    # # try:
    # # await super().cancel_and_wait_for_background_tasks()
    # # except ValueError as e:
    # # for task in self._background_tasks:
    # # print(task)
    # # raise e
    #
    # for task in self._background_tasks:
    # print(task)
    # print(task.get_loop())
    # await asyncio.wait([task])

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd()
    def _quit() -> None:
        """Quit euporie."""
        get_app().exit()

    @staticmethod
    @add_cmd(
        name="close-tab",
        filter=tab_has_focus,
        menu_title="Close File",
    )
    def _close_tab() -> None:
        """Close the current tab."""
        get_app().close_tab()

    @staticmethod
    @add_cmd(
        filter=tab_has_focus,
    )
    def _next_tab() -> None:
        """Switch to the next tab."""
        get_app().tab_idx += 1

    @staticmethod
    @add_cmd(
        filter=tab_has_focus,
    )
    def _previous_tab() -> None:
        """Switch to the previous tab."""
        get_app().tab_idx -= 1

    @staticmethod
    @add_cmd(
        filter=~buffer_has_focus,
    )
    def _focus_next() -> None:
        """Focus the next control."""
        get_app().layout.focus_next()

    @staticmethod
    @add_cmd(
        filter=~buffer_has_focus,
    )
    def _focus_previous() -> None:
        """Focus the previous control."""
        get_app().layout.focus_previous()

    @staticmethod
    @add_cmd()
    def _clear_screen() -> None:
        """Clear the screen."""
        get_app().renderer.clear()

    # ################################### Settings ####################################w

    add_setting(
        name="files",
        default=[],
        flags=["files"],
        nargs="*",
        type_=UPath,
        help_="List of file names to open",
        schema={
            "type": "array",
            "items": {
                "description": "File path",
                "type": "string",
            },
        },
        description="""
            A list of file paths to open when euporie is launched.
        """,
    )

    add_setting(
        name="edit_mode",
        flags=["--edit-mode"],
        type_=str,
        choices=["micro", "emacs", "vi"],
        title="Editor key bindings",
        help_="Key-binding mode for text editing",
        default="micro",
        description="""
            Key binding style to use when editing cells.
        """,
    )

    add_setting(
        name="tab_size",
        flags=["--tab-size"],
        type_=int,
        help_="Spaces per indentation level",
        default=4,
        schema={
            "minimum": 1,
        },
        description="""
            The number of spaces to use per indentation level. Should be set to 4.
        """,
    )

    add_setting(
        name="terminal_polling_interval",
        flags=["--terminal-polling-interval"],
        type_=int,
        help_="Time between terminal colour queries",
        default=0,
        schema={
            "min": 0,
        },
        description="""
            Determine how frequently the terminal should be polled for changes to the
            background / foreground colours. Set to zero to disable terminal polling.
        """,
    )

    add_setting(
        name="autoformat",
        flags=["--autoformat"],
        type_=bool,
        help_="Automatically re-format code cells when run",
        default=False,
        description="""
            Whether to automatically reformat code cells before they are run.
        """,
    )

    add_setting(
        name="format_black",
        flags=["--format-black"],
        type_=bool,
        help_="Use black when re-formatting code cells",
        default=True,
        description="""
            Whether to use :py:mod:`black` when reformatting code cells.
        """,
    )

    add_setting(
        name="format_isort",
        flags=["--format-isort"],
        type_=bool,
        help_="Use isort when re-formatting code cells",
        default=True,
        description="""
            Whether to use :py:mod:`isort` when reformatting code cells.
        """,
    )

    add_setting(
        name="format_ssort",
        flags=["--format-ssort"],
        type_=bool,
        help_="Use ssort when re-formatting code cells",
        default=True,
        description="""
            Whether to use :py:mod:`ssort` when reformatting code cells.
        """,
    )

    add_setting(
        name="syntax_theme",
        flags=["--syntax-theme"],
        type_=str,
        help_="Syntax highlighting theme",
        default="euporie",
        schema={
            # Do not want to print all theme names in `--help` screen as it looks messy
            # so we only add them in the scheme, not as setting choices
            "enum": list(pygments_styles.keys()),
        },
        description="""
            The name of the pygments style to use for syntax highlighting.
        """,
    )

    add_setting(
        name="color_depth",
        flags=["--color-depth"],
        type_=int,
        choices=[1, 4, 8, 24],
        default=None,
        help_="The color depth to use",
        description="""
            The number of bits to use to represent colors displayable on the screen.
            If set to None, the supported color depth of the terminal will be detected
            automatically.
        """,
    )

    add_setting(
        name="tmux_graphics",
        flags=["--tmux-graphics"],
        type_=bool,
        help_="Enable terminal graphics in tmux (experimental)",
        default=False,
        hidden=~in_tmux,
        description="""
            If set, terminal graphics will be used if :program:`tmux` is running by
            performing terminal escape sequence pass-through. You must restart euporie
            for this to take effect.

            You will also need to ensure that ``allow-passthrough`` is set to ``on`` in
            your :program:`tmux` configuration.

            .. warning::

               Terminal graphics in :program:`tmux` is experimental, and is not
               guaranteed to work. Use at your own risk!
        """,
    )

    add_setting(
        name="color_scheme",
        flags=["--color-scheme"],
        type_=str,
        choices=["default", "inverse", "light", "dark", "black", "white", "custom"],
        help_="The color scheme to use",
        default="default",
        description="""
            The color scheme to use: `auto` means euporie will try to use your
            terminal's color scheme, `light` means black text on a white background,
            and `dark` means white text on a black background.
        """,
    )

    add_setting(
        name="custom_background_color",
        flags=["--custom-background-color", "--custom-bg-color", "--bg"],
        type_=str,
        help_='Background color for "Custom" color theme',
        default="",
        schema={
            "maxLength": 7,
        },
        description="""
            The hex code of the color to use for the background in the "Custom" color
            scheme.
        """,
    )

    add_setting(
        name="custom_foreground_color",
        flags=["--custom-foreground-color", "--custom-fg-color", "--fg"],
        type_=str,
        help_='Foreground color for "Custom" color theme',
        default="",
        schema={
            "maxLength": 7,
        },
        description="""
            The hex code of the color to use for the foreground in the "Custom" color
            scheme.
        """,
    )

    add_setting(
        name="accent_color",
        flags=["--accent-color"],
        type_=str,
        help_="Accent color to use in the app",
        default="ansiblue",
        description="""
            The hex code of a color to use for the accent color in the application.
        """,
    )

    add_setting(
        name="key_bindings",
        flags=["--key-bindings"],
        type_=json.loads,
        help_="Additional key binding definitions",
        default={},
        description="""
            A mapping of component names to mappings of command name to key-binding lists.
    """,
        schema={
            "type": "object",
        },
    )

    add_setting(
        name="graphics",
        flags=["--graphics"],
        choices=["none", "sixel", "kitty", "iterm"],
        type_=str,
        default=None,
        help_="The preferred graphics protocol",
        description="""
            The graphics protocol to use, if supported by the terminal.
            If set to "none", terminal graphics will not be used.
    """,
    )

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.app.BaseApp": {
                "quit": "c-q",
                "close-tab": "c-w",
                "next-tab": "c-pagedown",
                "previous-tab": "c-pageup",
                "focus-next": "s-tab",
                "focus-previous": "tab",
                "clear-screen": "c-l",
            }
        }
    )
