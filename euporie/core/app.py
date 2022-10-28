"""Contains the main Application class which runs euporie.core."""
from __future__ import annotations

import asyncio
import json
import logging
from functools import partial
from typing import TYPE_CHECKING, cast
from weakref import WeakSet

from prompt_toolkit.application.application import Application, _CombinedRegistry
from prompt_toolkit.application.current import create_app_session
from prompt_toolkit.clipboard import InMemoryClipboard
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.cursor_shapes import CursorShape, CursorShapeConfig
from prompt_toolkit.data_structures import Point
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition, buffer_has_focus, to_filter
from prompt_toolkit.formatted_text import to_formatted_text
from prompt_toolkit.input.defaults import create_input
from prompt_toolkit.key_binding.bindings.basic import load_basic_bindings
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
from prompt_toolkit.layout.menus import CompletionsMenu
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
from prompt_toolkit.widgets.base import Shadow
from pygments.styles import STYLE_MAP as pygments_styles
from pygments.styles import get_style_by_name
from pyperclip import determine_clipboard
from upath import UPath

from euporie.core.commands import add_cmd
from euporie.core.config import Config, add_setting
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
from euporie.core.renderer import Renderer
from euporie.core.style import (
    DEFAULT_COLORS,
    HTML_STYLE,
    IPYWIDGET_STYLE,
    LOG_STYLE,
    MIME_STYLE,
    ColorPalette,
    ShadowStyle,
    build_style,
)
from euporie.core.terminal import TerminalInfo
from euporie.core.utils import ChainedList, parse_path

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from os import PathLike
    from typing import (
        Any,
        Callable,
        Dict,
        Literal,
        Optional,
        Sequence,
        Tuple,
        Type,
        Union,
    )

    from prompt_toolkit.clipboard import Clipboard
    from prompt_toolkit.contrib.ssh import PromptToolkitSSHSession
    from prompt_toolkit.filters import Filter, FilterOrBool
    from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.input import Input
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.layout import FocusableElement
    from prompt_toolkit.layout.screen import WritePosition
    from prompt_toolkit.output import Output

    from euporie.core.config import Setting
    from euporie.core.tabs.base import Tab
    from euporie.core.terminal import TerminalQuery
    from euporie.core.widgets.dialog import Dialog
    from euporie.core.widgets.pager import Pager
    from euporie.core.widgets.search_bar import SearchBar

    StatusBarFields = Tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]
    ContainerStatusDict = Dict[
        AnyContainer,
        Callable[[], StatusBarFields],
    ]

log = logging.getLogger(__name__)


_COLOR_DEPTHS = {
    1: ColorDepth.DEPTH_1_BIT,
    4: ColorDepth.DEPTH_4_BIT,
    8: ColorDepth.DEPTH_8_BIT,
    24: ColorDepth.DEPTH_24_BIT,
}


class CursorConfig(CursorShapeConfig):
    """Determines which cursor mode to use."""

    def get_cursor_shape(self, app: "Application[Any]") -> "CursorShape":
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

    config = Config()
    status_default: "StatusBarFields" = ([], [])
    need_mouse_support: "bool" = False

    def __init__(
        self,
        title: "Optional[str]" = None,
        set_title: "bool" = True,
        leave_graphics: "FilterOrBool" = True,
        extend_renderer_height: "FilterOrBool" = False,
        extend_renderer_width: "FilterOrBool" = False,
        **kwargs: "Any",
    ) -> "None":
        """Instantiates euporie specific application variables.

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
            **kwargs: The key-word arguments for the :py:class:`Application`

        """
        self.loaded = False
        # Initialise the application
        super().__init__(
            **{
                **{
                    "color_depth": self.config.color_depth,
                    "editing_mode": self.get_edit_mode(),
                    "mouse_support": Condition(lambda: self.need_mouse_support),
                    "cursor": CursorConfig(),
                },
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
        self.tabs: "list[Tab]" = []
        # Holds the search bar to pass to cell inputs
        self.search_bar: "Optional[SearchBar]" = None
        # Holds the index of the current tab
        self._tab_idx = 0
        # Add state for micro key-bindings
        self.micro_state = MicroState()
        # Load the terminal information system
        self.term_info = TerminalInfo(self.input, self.output, self.config)
        # Floats at the app level
        self.leave_graphics = to_filter(leave_graphics)
        self.graphics: "WeakSet[Float]" = WeakSet()
        self.dialogs: "dict[str, Dialog]" = {}
        self.menus: "dict[str, Float]" = {
            "completions": Float(
                content=Shadow(
                    CompletionsMenu(
                        max_height=16,
                        scroll_offset=1,
                    )
                ),
                xcursor=True,
                ycursor=True,
            )
        }
        self.floats = ChainedList(
            self.graphics,
            self.dialogs.values(),
            self.menus.values(),
        )
        # Mapping of Containers to status field generating functions
        self.container_statuses: "ContainerStatusDict" = {}
        # Continue loading when the application has been launched
        # and an event loop has been creeated
        self.pre_run_callables = [self.pre_run]
        self.post_load_callables: "list[Callable[[], None]]" = []
        # Set default vi input mode to navigate
        self.vi_state = ViState()
        # Set a long timeout for mappings (e.g. dd)
        self.timeoutlen = 1.0
        # Set a short timeout for flushing input
        self.ttimeoutlen = 0.0
        # Use a custom key-processor which does not wait after escape keys
        self.key_processor = KeyProcessor(_CombinedRegistry(self))
        # List of key-bindings groups to load
        self.bindings_to_load = ["euporie.core.app.BaseApp"]
        # Determines which clipboard mechanism to use
        self.clipboard: "Clipboard" = (
            PyperclipClipboard() if determine_clipboard()[0] else InMemoryClipboard()
        )
        # Allow hiding element when manually redrawing app
        self._redrawing = False
        self.redrawing = Condition(lambda: self._redrawing)
        # Add an optional pager
        self.pager: "Optional[Pager]" = None

        self.focused_element: "Optional[FocusableElement]" = None

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

        self.color_palette = ColorPalette()
        self.color_palette.add_color("fg", "#ffffff" "default")
        self.color_palette.add_color("bg", "#000000" "default")

        # Set to a write position to limit mouse events to a particular region
        self.mouse_limits: "Optional[WritePosition]" = None
        self.mouse_position = Point(0, 0)

    @property
    def title(self) -> "str":
        """The application's title."""
        return self._title

    @title.setter
    def title(self, value: "str") -> "None":
        """Set the terminal title."""
        self._title = value
        if self.set_title():
            self.output.set_title(value)

    def pause_rendering(self) -> "None":
        """Blocks rendering, but allows input to be processed.

        The first line prevents the display being drawn, and the second line means
        the key processor continues to process keys. We need this as we need to
        wait for the results of terminal queries which come in as key events.

        This is used to prevent flicker when we update the styles based on terminal
        feedback.
        """
        self._is_running = False
        self.renderer._waiting_for_cpr_futures.append(asyncio.Future())

    def resume_rendering(self) -> "None":
        """Resume rendering the app."""
        self._is_running = True
        if futures := self.renderer._waiting_for_cpr_futures:
            futures.pop()

    def pre_run(self, app: "Application" = None) -> "None":
        """Called during the 'pre-run' stage of application loading."""
        # Load key bindings
        self.load_key_bindings()
        # Determine what color depth to use
        self._color_depth = _COLOR_DEPTHS.get(
            self.config.color_depth, self.term_info.depth_of_color.value
        )
        # Set the application's style, and update it when the terminal responds
        self.update_style()
        self.term_info.colors.event += self.update_style
        self.pause_rendering()

        def terminal_ready() -> "None":
            """Commands here depend on the result of terminal queries."""
            # Open any files we need to
            self.open_files()
            # Load the layout
            # We delay this until we have terminal responses to allow terminal graphics
            # support to be detected first
            self.layout = Layout(self.load_container(), self.focused_element)
            # Run any additional steps
            self.post_load()
            # Resume rendering
            self.resume_rendering()
            # Request cursor position
            self._request_absolute_cursor_position()
            # Sending a repaint trigger
            self.invalidate()
            # Flag that the app is loaded
            self.loaded = True

        if self.input.closed:
            # If we do not have an interactive input, just get on with loading the app:
            # don't send terminal queries, as we will not get responses
            terminal_ready()
        else:
            # Otherwise, we query the terminal and wait asynchronously to give it
            # a chance to respond

            async def await_terminal_feedback() -> "None":
                try:
                    # Send queries to the terminal if supported
                    if self.input.__class__.__name__ in (
                        "Vt100Input",
                        "PosixPipeInput",
                    ):
                        self.term_info.send_all()
                        # Give the terminal a chance to respond
                        await asyncio.sleep(0.1)
                    # Complete loading the application
                    terminal_ready()
                except Exception as exception:
                    # Log exceptions, as this runs in the event loop and, exceptions may
                    # get hidden from the user
                    log.critical(
                        "An error occurred while trying to load the application",
                        exc_info=True,
                    )
                    self.exit(exception=exception)

            # Waits until the event loop is ready
            self.create_background_task(await_terminal_feedback())

    @classmethod
    def load_input(cls) -> "Input":
        """Creates the input for this application to use.

        Ensures the TUI app always tries to run in a TTY.

        Returns:
            A prompt-toolkit input instance

        """
        input_ = create_input(always_prefer_tty=True)
        if stdin := getattr(input_, "stdin", None):
            if not stdin.isatty():
                from euporie.core.io import IgnoredInput

                input_ = IgnoredInput()

        # Use a custom vt100 parser to allow querying the terminal
        if parser := getattr(input_, "vt100_parser", None):
            setattr(
                input_,
                "vt100_parser",
                Vt100Parser(parser.feed_key_callback),
            )

        return input_

    @classmethod
    def load_output(cls) -> "Output":
        """Creates the output for this application to use.

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

    def post_load(self) -> "None":
        """Allows subclasses to define additional loading steps."""
        # Call extra callables
        for cb in self.post_load_callables:
            cb()

    def load_key_bindings(self) -> "None":
        """Loads the application's key bindings."""
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

    def _on_resize(self) -> "None":
        """Hook the resize event to also query the terminal dimensions."""
        self.term_info.pixel_dimensions.send()
        super()._on_resize()

    @classmethod
    def launch(cls) -> "None":
        """Launches the app."""
        # Load the app's configuration
        cls.config.load(cls)
        # Configure the logs
        setup_logs(cls.config)
        # Run the application
        with create_app_session(input=cls.load_input(), output=cls.load_output()):
            # Create an instance of the app and run it
            return cls().run()

    @classmethod
    async def interact(cls, ssh_session: "PromptToolkitSSHSession") -> None:
        """Function to run the app asynchronously for the ssh hub server."""
        await cls().run_async()

    def load_container(self) -> "FloatContainer":
        """Loads the root container for this application.

        Returns:
            The root container for this app

        """
        return FloatContainer(
            content=Window(),
            floats=cast("list[Float]", self.floats),
        )

    def get_file_tab(self, path: "PathLike") -> "Optional[Type[Tab]]":
        """Returns the tab to use for a file path."""
        return None

    def open_file(self, path: "PathLike", read_only: "bool" = False) -> "None":
        """Creates a tab for a file.

        Args:
            path: The file path of the notebook file to open
            read_only: If true, the file should be opened read_only

        """
        ppath = parse_path(path)
        log.info(f"Opening file {path}")
        for tab in self.tabs:
            if ppath == getattr(tab, "path", ""):
                log.info(f"File {path} already open, activating")
                break
        else:
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

    def open_files(self) -> "None":
        """Opens the files defined in the configuration."""
        for file in self.config.files:
            self.open_file(file)

    @property
    def tab(self) -> "Optional[Tab]":
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
    def tab_idx(self) -> "int":
        """Gets the current tab index."""
        return self._tab_idx

    @tab_idx.setter
    def tab_idx(self, value: "int") -> "None":
        """Sets the current tab by index."""
        self._tab_idx = value % (len(self.tabs) or 1)
        if self.tabs:
            self.layout.focus(self.tabs[self._tab_idx])

    def focus_tab(self, tab: "Tab") -> "None":
        """Makes a tab visible and focuses it."""
        self.tab_idx = self.tabs.index(tab)

    def cleanup_closed_tab(self, tab: "Tab") -> "None":
        """Remove a tab container from the current instance of the app.

        Args:
            tab: The closed instance of the tab container

        """
        # Remove tab
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
            try:
                self.layout.focus_next()
            except ValueError:
                pass

    def close_tab(self, tab: "Optional[Tab]" = None) -> "None":
        """Closes a notebook tab.

        Args:
            tab: The instance of the tab to close. If `None`, the currently
                selected tab will be closed.

        """
        if tab is None:
            tab = self.tab
        if tab is not None:
            tab.close(cb=partial(self.cleanup_closed_tab, tab))

    def get_edit_mode(self) -> "EditingMode":
        """Returns the editing mode enum defined in the configuration."""
        from euporie.core.key_binding.bindings.micro import EditingMode

        return {
            "micro": EditingMode.MICRO,  # type: ignore
            "vi": EditingMode.VI,
            "emacs": EditingMode.EMACS,
        }.get(
            str(self.config.edit_mode), EditingMode.MICRO  # type: ignore
        )

    def update_edit_mode(self, setting: "Optional[Setting]" = None) -> "None":
        """Sets the keybindings for editing mode."""
        self.editing_mode = self.get_edit_mode()
        log.debug("Editing mode set to: %s", self.editing_mode)

    def create_merged_style(self) -> "BaseStyle":
        """Generate a new merged style for the application.

        Using a dynamic style has serious performance issues, so instead we update
        the style on the renderer directly when it changes in `self.update_style`

        Returns:
            Return a combined style to use for the application

        """
        # Get foreground and background colors based on the configured colour scheme
        theme_colors = {
            "light": {"fg": "#202020", "bg": "#F0F0F0"},
            "dark": {"fg": "#F0F0F0", "bg": "#202020"},
            "white": {"fg": "#000000", "bg": "#FFFFFF"},
            "black": {"fg": "#FFFFFF", "bg": "#000000"},
            "default": self.term_info.colors.value,
            # TODO - use config.custom_colors
            "custom": {
                "fg": self.config.custom_foreground_color,
                "bg": self.config.custom_background_color,
            },
        }
        base_colors: "dict[str, str]" = {
            **DEFAULT_COLORS,
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

        return ShadowStyle(
            style=merge_styles(
                [
                    style_from_pygments_cls(
                        get_style_by_name(self.config.syntax_theme)
                    ),
                    Style(MIME_STYLE),
                    Style(HTML_STYLE),
                    Style(LOG_STYLE),
                    Style(IPYWIDGET_STYLE),
                    app_style,
                ]
            ),
            color_palette=self.color_palette,
        )

    def update_style(
        self,
        query: "Optional[Union[TerminalQuery, Setting]]" = None,
    ) -> "None":
        """Updates the application's style when the syntax theme is changed."""
        self.renderer.style = self.create_merged_style()

    def refresh(self) -> "None":
        """Reset all tabs."""
        for tab in self.tabs:
            to_container(tab).reset()

    def _create_merged_style(
        self, include_default_pygments_style: "Filter" = None
    ) -> "BaseStyle":
        """Block default style loading."""
        return DummyStyle()

    def format_status(self, part: "Literal['left', 'right']") -> "StyleAndTextTuples":
        """Formats the fields in the statusbar generated by the current tab.

        Args:
            part: ``'left'`` to return the fields on the left side of the statusbar,
                and ``'right'`` to return the fields on the right

        Returns:
            A list of style and text tuples for display in the statusbar

        """
        entries: "StatusBarFields" = ([], [])
        for container, status_func in self.container_statuses.items():
            if self.layout.has_focus(container):
                entries = status_func()
                break
        else:
            if not self.tabs:
                entries = self.status_default

        output: "StyleAndTextTuples" = []
        # Show the tab's status fields
        for field in entries[0 if part == "left" else 1]:
            if field:
                if isinstance(field, tuple):
                    ft = [field]
                else:
                    ft = to_formatted_text(field, style="class:status.field")
                output += [
                    ("class:status.field", " "),
                    *ft,
                    ("class:status.field", " "),
                    ("class:status", " "),
                ]
        if output:
            output.pop()
        return output

    def draw(self, render_as_done: "bool" = True) -> "None":
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
        self, loop: "AbstractEventLoop", context: "dict[str, Any]"
    ) -> "None":
        exception = context.get("exception")
        # Log observed exceptions to the log
        log.exception("An unhandled exception occurred", exc_info=exception)

    async def cancel_and_wait_for_background_tasks(self) -> None:
        """Cancel all background tasks, and wait for the cancellation to be done.

        Ignore :py:`RuntimeError`s, which result when tasks are attached to a different
        event loop.
        """
        for task in self.background_tasks:
            task.cancel()

        for task in self.background_tasks:
            try:
                await task
            except (asyncio.CancelledError, RuntimeError):
                pass

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd()
    def _quit() -> "None":
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
    def _next_tab() -> "None":
        """Switch to the next tab."""
        get_app().tab_idx += 1

    @staticmethod
    @add_cmd(
        filter=tab_has_focus,
    )
    def _previous_tab() -> "None":
        """Switch to the previous tab."""
        get_app().tab_idx -= 1

    @staticmethod
    @add_cmd(
        filter=~buffer_has_focus,
    )
    def _focus_next() -> "None":
        """Focus the next control."""
        get_app().layout.focus_next()

    @staticmethod
    @add_cmd(
        filter=~buffer_has_focus,
    )
    def _focus_previous() -> "None":
        """Focus the previous control."""
        get_app().layout.focus_previous()

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
        name="log_file",
        flags=["--log-file"],
        nargs="?",
        default="",
        type_=str,
        title="the log file path",
        help_="File path for logs",
        description="""
            When set to a file path, the log output will be written to the given path.
            If no value is given output will be sent to the standard output.
        """,
    )

    add_setting(
        name="log_level",
        flags=["--log-level"],
        type_=str,
        default="",
        title="the log level",
        help_="Set the log level",
        choices=["debug", "info", "warning", "error", "critical"],
        description="""
            When set, logging events at the given level are emitted.
        """,
    )

    add_setting(
        name="log_config",
        flags=["--log-config"],
        type_=str,
        default=None,
        title="additional logging configuration",
        help_="Additional logging configuration",
        description="""
            A JSON string specifying additional logging configuration.
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
            }
        }
    )
