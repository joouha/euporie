"""Contains the main Application class which runs euporie."""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.application import Application, _CombinedRegistry
from prompt_toolkit.application.current import create_app_session
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import buffer_has_focus
from prompt_toolkit.input.defaults import create_input
from prompt_toolkit.key_binding.bindings.basic import load_basic_bindings
from prompt_toolkit.key_binding.bindings.cpr import load_cpr_bindings
from prompt_toolkit.key_binding.bindings.emacs import (
    load_emacs_bindings,
    load_emacs_search_bindings,
    load_emacs_shift_selection_bindings,
)
from prompt_toolkit.key_binding.bindings.mouse import load_mouse_bindings
from prompt_toolkit.key_binding.bindings.vi import (
    load_vi_bindings,
    load_vi_search_bindings,
)
from prompt_toolkit.key_binding.key_bindings import (
    ConditionalKeyBindings,
    merge_key_bindings,
)
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import FloatContainer, Window, to_container
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.output.defaults import create_output
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
from pygments.styles import get_style_by_name  # type: ignore

from euporie.config import config
from euporie.enums import TabMode
from euporie.key_binding.bindings.commands import load_command_bindings
from euporie.key_binding.bindings.micro import load_micro_bindings
from euporie.key_binding.key_processor import KeyProcessor
from euporie.key_binding.micro_state import MicroState
from euporie.log import setup_logs
from euporie.style import LOG_STYLE, MARKDOWN_STYLE, ColorPalette, build_style
from euporie.tabs.base import Tab
from euporie.tabs.notebook import Notebook
from euporie.terminal import TerminalInfo, Vt100Parser

if TYPE_CHECKING:
    from typing import Any, Callable, Dict, List, Optional, Tuple, Type

    from prompt_toolkit.filters import Filter
    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.input import Input
    from prompt_toolkit.input.vt100 import Vt100Input
    from prompt_toolkit.layout.containers import AnyContainer, Float
    from prompt_toolkit.output import Output
    from prompt_toolkit.widgets import SearchToolbar

    from euporie.tabs.notebook import EditNotebook
    from euporie.terminal import TerminalQuery
    from euporie.widgets.cell import InteractiveCell
    from euporie.widgets.palette import CommandPalette

    StatusBarFields = Tuple[List[AnyFormattedText], List[AnyFormattedText]]
    ContainerStatusDict = Dict[
        AnyContainer,
        Callable[..., StatusBarFields],
    ]

log = logging.getLogger(__name__)


_COLOR_DEPTHS = {
    1: ColorDepth.DEPTH_1_BIT,
    4: ColorDepth.DEPTH_4_BIT,
    8: ColorDepth.DEPTH_8_BIT,
    24: ColorDepth.DEPTH_24_BIT,
}


class EuporieApp(Application):
    """The base euporie application class.

    This subclasses the `prompt_toolkit.application.Application` class, so application
    wide methods can be easily added.
    """

    # Defines which notebook class should we use
    notebook_class: "Type[Notebook]"
    tab_mode: "TabMode"

    def __init__(self, **kwargs: "Any") -> "None":
        """Instantiates euporie specific application variables.

        After euporie specific application variables are instantiated, the application
        instance is initiated.

        Args:
            **kwargs: The key-word arguments for the :py:class:`Application`

        """
        # Initialise the application
        super().__init__(
            **{
                **{
                    "color_depth": config.color_depth,
                },
                **kwargs,
            }
        )
        # Use a custom vt100 parser to allow querying the terminal
        self.using_vt100 = self.input.__class__.__name__ in (
            "Vt100Input",
            "PosixPipeInput",
        )
        if self.using_vt100:
            self.input = cast("Vt100Input", self.input)
            self.input.vt100_parser = Vt100Parser(
                self.input.vt100_parser.feed_key_callback
            )
        # Contains the opened tab containers
        self.tabs: "List[Tab]" = []
        # Holds the search bar to pass to cell inputs
        self.search_bar: "Optional[SearchToolbar]" = None
        # Holds the index of the current tab
        self._tab_idx = 0
        # Add state for micro key-bindings
        self.micro_state = MicroState()
        # Load the terminal information system
        self.term_info = TerminalInfo(self.input, self.output)
        # Floats at the app level
        self.floats: "list[Float]" = []
        # If a dialog is showing
        self.has_dialog = False
        # Mapping of Containers to status field generating functions
        self.container_statuses: "ContainerStatusDict" = {}
        # Assign command palette variable
        self.command_palette: "Optional[CommandPalette]" = None
        # Continue loading when the application has been launched
        # and an event loop has been creeated
        self.pre_run_callables = [self.pre_run]
        # Set a long timeout for mappings (e.g. dd)
        self.timeoutlen = 1.0
        # Set a short timeout for flushing input
        self.ttimeoutlen = 0.0
        # Use a custom key-processor which does not wait after escape keys
        self.key_processor = KeyProcessor(_CombinedRegistry(self))

    def pre_run(self, app: "Application" = None) -> "None":
        """Called during the 'pre-run' stage of application loading."""
        # Load key bindings
        self.load_key_bindings()
        # Determine what color depth to use
        self._color_depth = _COLOR_DEPTHS.get(
            config.color_depth, self.term_info.depth_of_color.value
        )
        # Set the application's style, and update it when the terminal responds
        self.update_style()
        self.term_info.foreground_color.event += self.update_style
        self.term_info.background_color.event += self.update_style
        # Blocks rendering, but allows input to be processed
        # The first line prevents the display being drawn, and the second line means
        # the key processor continues to process keys. We need this as we need to
        # wait for the results of terminal queries which come in as key events
        # This prevents flicker when we update the styles based on terminal feedback
        self._is_running = False
        self.renderer._waiting_for_cpr_futures.append(asyncio.Future())

        def terminal_ready() -> "None":
            """Commands here depend on the result of terminal queries."""
            # Load the layout
            # We delay this until we have terminal responses to allow terminal graphics
            # support to be detected first
            self.layout = Layout(self.load_container())
            # Open any files we need to
            self.open_files()
            # Run any additional steps
            self.post_load()
            # Resume rendering
            self._is_running = True
            self.renderer._waiting_for_cpr_futures.pop()
            # Sending a repaint trigger
            self.invalidate()

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
                    if self.using_vt100:
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
        from prompt_toolkit.input.base import DummyInput

        input_ = create_input(always_prefer_tty=True)
        if stdin := getattr(input_, "stdin", None):
            if not stdin.isatty():
                input_ = DummyInput()
        return input_

    @classmethod
    def load_output(cls) -> "Output":
        """Creates the output for this application to use.

        Ensures the TUI app always tries to run in a TTY.

        Returns:
            A prompt-toolkit output instance

        """
        return create_output(always_prefer_tty=True)

    def post_load(self) -> "None":
        """Allows subclasses to define additional loading steps."""
        pass

    def load_key_bindings(self) -> "None":
        """Loads the application's key bindings."""
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
                            load_micro_bindings(),
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
                load_mouse_bindings(),
                load_cpr_bindings(),
                # Load terminal query response key bindings
                load_command_bindings("terminal"),
            ]
        )

        self.key_bindings = load_command_bindings(
            "app", "config", "completion", "suggestion"
        )
        # dict_bindings(config.key_bindings or {})

    def _on_resize(self) -> "None":
        """Hook the resize event to also query the terminal dimensions."""
        self.term_info.pixel_dimensions.send()
        super()._on_resize()

    @classmethod
    def launch(cls) -> "None":
        """Launches the app."""
        # This configures the logs for euporie
        setup_logs()
        with create_app_session(input=cls.load_input(), output=cls.load_output()):
            # Create an instance of the app and run it
            return cls().run()

    def load_container(self) -> "FloatContainer":
        """Loads the root container for this application.

        Returns:
            The root container for this app

        """
        return FloatContainer(content=Window(), floats=[])

    def open_file(self, path: "Path", read_only: "bool" = False) -> "None":
        """Creates a tab for a file.

        Args:
            path: The file path of the notebooknotebook file to open
            read_only: If true, the file should be opened read_only

        """
        path = Path(path).expanduser()
        log.info(f"Opening file {path}")
        for tab in self.tabs:
            if path == getattr(tab, "path", ""):
                log.info(f"File {path} already open, activating")
                break
        else:
            tab = self.notebook_class(path, app=self)
            self.tabs.append(tab)
            tab.focus()

    def open_files(self) -> "None":
        """Opens the files defined in the configuration."""
        for file in config.files:
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
        self._tab_idx = value % len(self.tabs)
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
        return {
            "micro": EditingMode.MICRO,  # type: ignore
            "vi": EditingMode.VI,
            "emacs": EditingMode.EMACS,
        }.get(
            str(config.edit_mode), EditingMode.MICRO  # type: ignore
        )

    def set_edit_mode(self, mode: "EditingMode") -> "None":
        """Sets the keybindings for editing mode.

        Args:
            mode: One of default, vi, or emacs

        """
        config.edit_mode = str(mode)
        self.editing_mode = self.get_edit_mode()
        log.debug("Editing mode set to: %s", self.editing_mode)

    def create_merged_style(self) -> "BaseStyle":
        """Generate a new merged style for the application."""
        # Get foreground and background colors based on the configured colour scheme
        theme_colors = {
            "light": {"fg": "#202020", "bg": "#F0F0F0"},
            "dark": {"fg": "#F0F0F0", "bg": "#202020"},
            "white": {"fg": "#000000", "bg": "#FFFFFF"},
            "black": {"fg": "#FFFFFF", "bg": "#000000"},
            "default": {
                "fg": self.term_info.foreground_color.value,
                "bg": self.term_info.background_color.value,
            },
            "custom": {
                "fg": config.custom_foreground_color,
                "bg": config.custom_background_color,
            },
        }
        base_colors: "dict[str, str]" = theme_colors.get(
            config.color_scheme, theme_colors["default"]
        )

        # Build a color palette from the fg/bg colors
        self.color_palette = ColorPalette()
        base_override = "default" if config.color_scheme == "default" else ""
        for name, color in base_colors.items():
            self.color_palette.add_color(
                name, color or theme_colors["default"][name], base_override
            )

        # Build app style
        app_style = build_style(
            self.color_palette,
            # have_term_colors=bool(self.term_info.foreground_color.value),
        )

        # Apply style transformations based on the configured color scheme
        self.style_transformation = merge_style_transformations(
            [
                ConditionalStyleTransformation(
                    SetDefaultColorStyleTransformation(**base_colors),
                    config.color_scheme != "default",
                ),
                ConditionalStyleTransformation(
                    SwapLightAndDarkStyleTransformation(),
                    config.color_scheme == "inverse",
                ),
            ]
        )

        # Using a dynamic style has serious performance issues, so instead we update
        # the style on the renderer directly when it changes in `self.update_style`
        return merge_styles(
            [
                style_from_pygments_cls(get_style_by_name(config.syntax_theme)),
                Style(MARKDOWN_STYLE),
                Style(LOG_STYLE),
                app_style,
            ]
        )

    def update_style(
        self,
        query: "Optional[TerminalQuery]" = None,
        pygments_style: "Optional[str]" = None,
        color_scheme: "Optional[str]" = None,
    ) -> "None":
        """Updates the application's style when the syntax theme is changed."""
        if pygments_style is not None:
            config.syntax_theme = pygments_style
        if color_scheme is not None:
            config.color_scheme = color_scheme
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

    @property
    def notebook(self) -> "Optional[EditNotebook]":
        """Return the currently active notebook."""
        return None

    @property
    def cell(self) -> "Optional[InteractiveCell]":
        """Return the currently active cell."""
        return None

    def add_float(self, float_container: "Float") -> "None":
        """Adds a float to the application."""
        if float_container not in self.floats:
            self.floats.append(float_container)
        root = self.layout.container
        assert isinstance(root, FloatContainer)
        for float_ in self.floats:
            if root.floats is not None and float_ not in root.floats:
                root.floats.insert(-1, float_)

    def remove_float(self, float_container: "Float") -> "None":
        """Removes a float to the application."""
        if float_container in self.floats:
            self.floats.remove(float_container)
        root = self.layout.container
        assert isinstance(root, FloatContainer)
        if root.floats is not None and float_container in root.floats:
            root.floats.remove(float_container)
