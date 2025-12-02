"""Contain the main Application class which runs euporie.core."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from abc import ABC, abstractmethod
from enum import Enum
from functools import partial
from pathlib import PurePath
from typing import TYPE_CHECKING, cast, overload
from weakref import WeakSet, WeakValueDictionary

from prompt_toolkit.application.application import Application, _CombinedRegistry
from prompt_toolkit.application.current import create_app_session, set_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.enums import EditingMode
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
from prompt_toolkit.key_binding.bindings.vi import load_vi_search_bindings
from prompt_toolkit.key_binding.key_bindings import (
    ConditionalKeyBindings,
    merge_key_bindings,
)
from prompt_toolkit.layout.containers import Float, FloatContainer, to_container
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
from prompt_toolkit.utils import Event

from euporie.core.app.base import ConfigurableApp
from euporie.core.app.cursor import CursorConfig
from euporie.core.clipboard import CONFIGURED_CLIPBOARDS
from euporie.core.filters import has_toolbar
from euporie.core.format import CliFormatter
from euporie.core.io import COLOR_DEPTHS, Vt100_Output, Vt100Parser
from euporie.core.key_binding.key_processor import KeyProcessor
from euporie.core.key_binding.micro_state import MicroState
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.key_binding.vi_state import ViState
from euporie.core.layout.containers import Window
from euporie.core.log import setup_logs
from euporie.core.lsp import KNOWN_LSP_SERVERS, LspClient
from euporie.core.renderer import Renderer
from euporie.core.style import (
    DEFAULT_COLORS,
    DIAGNOSTIC_STYLE,
    HTML_STYLE,
    IPYWIDGET_STYLE,
    LOG_STYLE,
    MIME_STYLE,
    ColorPalette,
    build_style,
    get_style_by_name,
)
from euporie.core.utils import ChainedList
from euporie.core.widgets.decor import Shadow
from euporie.core.widgets.menu import CompletionsMenu

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from collections.abc import Callable
    from pathlib import Path
    from types import FrameType
    from typing import Any, ClassVar, TypeVar

    # from prompt_toolkit.application import _AppResult
    from prompt_toolkit.contrib.ssh import PromptToolkitSSHSession
    from prompt_toolkit.filters import Filter, FilterOrBool
    from prompt_toolkit.input import Input
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.layout import FocusableElement
    from prompt_toolkit.layout.screen import WritePosition
    from prompt_toolkit.output import Output

    from euporie.core.bars.command import CommandBar
    from euporie.core.bars.search import SearchBar
    from euporie.core.config import Setting
    from euporie.core.format import Formatter
    from euporie.core.tabs import TabRegistryEntry
    from euporie.core.tabs.base import Tab
    from euporie.core.widgets.dialog import Dialog
    from euporie.core.widgets.pager import Pager

    _AppResult = TypeVar("_AppResult")

log = logging.getLogger(__name__)


class ExtraEditingMode(str, Enum):
    """Additional editing modes."""

    MICRO = "MICRO"


class BaseApp(ConfigurableApp, Application, ABC):
    """All euporie apps.

    The base euporie application class.

    This subclasses the `prompt_toolkit.application.Application` class, so application
    wide methods can be easily added.
    """

    color_palette: ColorPalette
    mouse_position: Point

    _config_defaults: ClassVar[dict[str, Any]] = {"log_level_stdout": "critical"}

    def __init__(
        self,
        title: str | None = None,
        set_title: bool = True,
        leave_graphics: FilterOrBool = True,
        extend_renderer_height: FilterOrBool = False,
        extend_renderer_width: FilterOrBool = False,
        enable_page_navigation_bindings: FilterOrBool | None = True,
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
            enable_page_navigation_bindings: Determines if page navigation keybindings
                should be loaded
            kwargs: The key-word arguments for the :py:class:`Application`

        """
        # Initialise the application
        super().__init__(
            **{
                "clipboard": CONFIGURED_CLIPBOARDS.get(
                    self.config.clipboard, lambda: None
                )(),
                "color_depth": COLOR_DEPTHS.get(self.config.color_depth),
                "editing_mode": self.get_edit_mode(),
                "mouse_support": True,
                "cursor": CursorConfig(),
                "enable_page_navigation_bindings": enable_page_navigation_bindings,
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
        self.on_tabs_change = Event(self)
        # Holds the optional toolbars
        self.search_bar: SearchBar | None = None
        self.command_bar: CommandBar | None = None
        # Holds the index of the current tab
        self._tab_idx = 0
        # Add state for micro key-bindings
        self.micro_state = MicroState()
        # Default terminal info values
        self.term_colors = dict(DEFAULT_COLORS)
        self.term_graphics_sixel = False
        self.term_graphics_iterm = False
        self.term_graphics_kitty = False
        self.term_sgr_pixel = False
        self.term_osc52_clipboard = False
        self._term_size_px: tuple[int, int]
        # Floats at the app level
        self.leave_graphics = to_filter(leave_graphics)
        self.graphics: WeakSet[Float] = WeakSet()
        self.dialog_classes: dict[str, type[Dialog]] = {}
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
            "euporie.core.app.app:BaseApp",
            "euporie.core.key_binding.bindings.terminal:TerminalQueries",
        ]

        if enable_page_navigation_bindings:
            from euporie.core.key_binding.bindings.page_navigation import (
                load_page_navigation_bindings,
            )

            self._page_navigation_bindings = load_page_navigation_bindings(self.config)
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
        self.config.events.edit_mode += self.update_edit_mode
        self.config.events.syntax_theme += self.update_style
        self.config.events.color_scheme += self.update_style
        self.config.events.log_level += lambda x: setup_logs(self.config)
        self.config.events.log_file += lambda x: setup_logs(self.config)
        self.config.events.log_config += lambda x: setup_logs(self.config)
        self.config.events.color_depth += lambda x: setattr(
            self, "_color_depth", COLOR_DEPTHS[self.config.color_depth]
        )
        self.config.events.clipboard += lambda x: setattr(
            self, "clipboard", CONFIGURED_CLIPBOARDS[self.config.clipboard]
        )
        # Set up the color palette
        self.color_palette = ColorPalette()
        self.color_palette.add_color("fg", "#ffffff", "default")
        self.color_palette.add_color("bg", "#000000", "default")
        # Set up a write position to limit mouse events to a particular region
        self.mouse_limits: WritePosition | None = None
        self.mouse_position = Point(0, 0)
        # Set up style update triggers
        self.style_invalid = False
        self.before_render += self.do_style_update

        # Store LSP client instances
        self.lsp_clients: WeakValueDictionary[str, LspClient] = WeakValueDictionary()

        # Build list of configured external formatters
        self.formatters: list[Formatter] = [
            CliFormatter(**info) for info in self.config.formatters
        ]

    @property
    def term_size_px(self) -> tuple[int, int]:
        """The dimensions of the terminal in pixels."""
        try:
            return self._term_size_px
        except AttributeError:
            from euporie.core.io import _tiocgwinsz

            _rows, _cols, px, py = _tiocgwinsz()
            self._term_size_px = (px, py)
        return self._term_size_px

    @term_size_px.setter
    def term_size_px(self, value: tuple[int, int]) -> None:
        self._term_size_px = value

    @property
    def cell_size_px(self) -> tuple[int, int]:
        """Get the pixel size of a single terminal cell."""
        px, py = self.term_size_px
        rows, cols = self.output.get_size()
        # If we can't get the pixel size, just guess wildly
        return px // cols or 10, py // rows or 20

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
        # Set the application's style
        self.update_style()
        # Load completions menu.
        self.menus["completions"] = Float(
            content=Shadow(CompletionsMenu(extra_filter=~has_toolbar)),
            xcursor=True,
            ycursor=True,
        )
        # Load the layout
        # We delay this until we have terminal responses to allow terminal graphics
        # support to be detected first
        self.layout = Layout(self.load_container(), self.focused_element)
        # Open any files we need to
        self.open_files()
        # Start polling terminal style if configured
        if self.config.terminal_polling_interval and hasattr(
            self.input, "vt100_parser"
        ):
            self.create_background_task(self._poll_terminal_colors())

    async def _poll_terminal_colors(self) -> None:
        """Repeatedly query the terminal for its background and foreground colours."""
        if isinstance(output := self.output, Vt100_Output):
            while self.config.terminal_polling_interval:
                await asyncio.sleep(self.config.terminal_polling_interval)
                output.get_colors()

    async def run_async(
        self,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
        slow_callback_duration: float = 0.5,
    ) -> _AppResult:
        """Run the application."""
        with set_app(self):
            # Use a custom vt100 parser to allow querying the terminal
            if parser := getattr(self.input, "vt100_parser", None):
                setattr(  # noqa B010
                    self.input, "vt100_parser", Vt100Parser(parser.feed_key_callback)
                )

            # Load key bindings
            self.load_key_bindings()

            if isinstance(self.output, Vt100_Output):
                # Send terminal queries
                self.output.get_colors()
                self.output.get_pixel_size()
                self.output.get_kitty_graphics_status()
                self.output.get_device_attributes()
                self.output.get_iterm_graphics_status()
                self.output.get_sgr_pixel_status()
                self.output.get_csiu_status()
                self.output.flush()

                # Read responses
                kp = self.key_processor

                def read_from_input() -> None:
                    kp.feed_multiple(self.input.read_keys())

                with self.input.raw_mode(), self.input.attach(read_from_input):
                    # Give the terminal time to respond and allow the event loop to read
                    # the terminal responses from the input
                    await asyncio.sleep(0.1)
                kp.process_keys()

        return await super().run_async(
            pre_run, set_exception_handler, handle_sigint, slow_callback_duration
        )

    @classmethod
    async def interact(cls, ssh_session: PromptToolkitSSHSession) -> None:
        """Run the app asynchronously for the hub SSH server."""
        try:
            await cls().run_async()
        except EOFError:
            pass

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
        from euporie.core.key_binding.bindings.terminal import load_terminal_bindings
        from euporie.core.key_binding.bindings.vi import load_vi_bindings

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
                load_terminal_bindings(),
            ]
        )
        self.key_bindings = load_registered_bindings(
            *self.bindings_to_load, config=self.config
        )

    def _on_resize(self) -> None:
        """Query the terminal dimensions on a resize event."""
        if isinstance(output := self.output, Vt100_Output):
            output.get_pixel_size()
        super()._on_resize()

    @classmethod
    def launch(cls) -> None:
        """Launch the app."""
        from prompt_toolkit.utils import in_main_thread

        super().launch()
        # Run the application
        with create_app_session(input=cls.load_input(), output=cls.load_output()):
            # Create an instance of the app and run it
            app = cls()
            if in_main_thread():
                # Handle SIGTERM while the app is running
                original_sigterm = signal.getsignal(signal.SIGTERM)
                signal.signal(signal.SIGTERM, app.cleanup)
            # Set and run the app
            with set_app(app):
                try:
                    result = app.run()
                except (EOFError, KeyboardInterrupt):
                    result = None
                finally:
                    if in_main_thread():
                        signal.signal(signal.SIGTERM, original_sigterm)
        return result

    @overload
    def exit(self) -> None: ...
    @overload
    def exit(self, *, result: _AppResult, style: str = "") -> None: ...
    @overload
    def exit(
        self, *, exception: BaseException | type[BaseException], style: str = ""
    ) -> None: ...
    def exit(
        self,
        result: _AppResult | None = None,
        exception: BaseException | type[BaseException] | None = None,
        style: str = "",
    ) -> None:
        """Shut down any remaining LSP clients at exit."""
        self.shutdown_lsps()
        if exception is not None:
            super().exit(exception=exception, style=style)
        elif result is not None:
            super().exit(result=result, style=style)
        else:
            super().exit()

    def cleanup(self, signum: int, frame: FrameType | None) -> None:
        """Restore the state of the terminal on unexpected exit."""
        log.critical("Unexpected exit signal, restoring terminal")
        output = self.output
        if self.is_running:
            self.exit()
        self.shutdown_lsps()
        # Reset terminal state
        output.reset_cursor_key_mode()
        output.enable_autowrap()
        output.clear_title()
        output.show_cursor()
        output.reset_attributes()
        self.renderer.reset()
        # Exit the main thread
        sys.exit(1)

    def get_dialog(self, name: str) -> Dialog | None:
        """Return a dialog instance, creating it if it does not exist."""
        if name not in self.dialogs and (dialog_class := self.dialog_classes.get(name)):
            self.dialogs[name] = dialog_class(self)
        return self.dialogs.get(name)

    @abstractmethod
    def load_container(self) -> AnyContainer:
        """Load the root container for this application.

        Returns:
            The root container for this app

        """
        return FloatContainer(
            content=self.layout.container or Window(),
            floats=cast("list[Float]", self.floats),
        )

    @property
    def tab_registry(self) -> list[TabRegistryEntry]:
        """Return the tab registry."""
        from euporie.core.tabs import _TAB_REGISTRY

        return _TAB_REGISTRY

    def get_file_tabs(self, path: Path) -> list[TabRegistryEntry]:
        """Return the tab to use for a file path."""
        from euporie.core.convert.mime import get_mime

        path_mime = get_mime(path) or "text/plain"
        log.debug("File %s has mime type: %s", path, path_mime)

        # Use a set to automatically handle duplicates
        tab_options: set[TabRegistryEntry] = set()
        for entry in self.tab_registry:
            for mime_type in entry.mime_types:
                if PurePath(path_mime).match(mime_type):
                    tab_options.add(entry)
            if path.suffix in entry.file_extensions:
                tab_options.add(entry)

        # Sort by weight (TabRegistryEntry.__lt__ handles this)
        return sorted(tab_options, reverse=True)

    def get_file_tab(self, path: Path) -> type[Tab] | None:
        """Return the tab to use for a file path."""
        if tabs := self.get_file_tabs(path):
            return tabs[0].tab_class
        return None

    def get_language_lsps(self, language: str) -> list[LspClient]:
        """Return the approprrate LSP clients for a given language."""
        clients = []
        if self.config.enable_language_servers:
            from shutil import which

            lsps = {**KNOWN_LSP_SERVERS, **self.config.language_servers}
            for name, kwargs in lsps.items():
                if kwargs:
                    client = None
                    if (
                        (
                            not (lsp_langs := kwargs.get("languages"))
                            or language in lsp_langs
                        )
                        and not (client := self.lsp_clients.get(name))
                        and which(kwargs["command"][0])
                    ):
                        client = LspClient(name, **kwargs)
                        self.lsp_clients[name] = client
                        client.start()
                    if client:
                        clients.append(client)
        return clients

    def shutdown_lsps(self) -> None:
        """Shut down all the remaining LSP servers."""
        # Wait for all LSP exit calls to complete
        # The exit calls occur in the LSP event loop thread
        for lsp in list(self.lsp_clients.values()):
            try:
                lsp.exit().result()  # block until exit completes
            except Exception:
                log.exception("Error shutting down LSP client %s", lsp)

    def open_file(
        self, path: Path, read_only: bool = False, tab_class: type[Tab] | None = None
    ) -> None:
        """Create a tab for a file.

        Args:
            path: The file path of the notebook file to open
            read_only: If true, the file should be opened read_only
            tab_class: The tab type to use to open the file

        """
        from euporie.core.path import parse_path

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
                self.add_tab(tab)
                # Ensure the opened tab is focused at app start
                self.focused_element = tab
                # Ensure the newly opened tab is selected
                self.tab_idx = len(self.tabs) - 1
                # Save 20 most recent files, deduplicating while keeping order
                if ppath.exists():
                    self.config.recent_files = list(
                        dict.fromkeys([ppath, *self.config.recent_files]).keys()
                    )[:20]

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
            container = to_container(self.tabs[self._tab_idx])
            try:
                self.layout.focus(container)
            except ValueError:
                log.exception("Cannot focus tab")

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
            self.on_tabs_change()
        # Focus the next active tab if one exists
        if next_tab := self.tab:
            next_tab.focus()
        # If no tab is open, ensure something is focused
        else:
            try:
                self.layout.focus_next()
            except ValueError:
                pass

    def add_tab(self, tab: Tab) -> None:
        """Add a tab to the current tabs list."""
        self.tabs.append(tab)
        self.on_tabs_change()

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
        micro_mode = cast("EditingMode", ExtraEditingMode.MICRO)

        return {
            "micro": micro_mode,
            "vi": EditingMode.VI,
            "emacs": EditingMode.EMACS,
        }.get(str(self.config.edit_mode), micro_mode)

    def update_edit_mode(self, setting: Setting | None = None) -> None:
        """Set the keybindings for editing mode."""
        self.editing_mode = self.get_edit_mode()
        log.debug("Editing mode set to: %s", self.editing_mode)

    @property
    def color_depth(self) -> ColorDepth:
        """The active :class:`.ColorDepth`.

        The current value is determined as follows:

        - If a color depth was given explicitly to this application, use that
          value.
        - Otherwise, fall back to the color depth that is reported by the
          :class:`.Output` implementation. If the :class:`.Output` class was
          created using `output.defaults.create_output`, then this value is
          coming from the $PROMPT_TOOLKIT_COLOR_DEPTH environment variable.
        """
        # Detect terminal color depth
        if self._color_depth is None:
            if os.environ.get("NO_COLOR", "") or os.environ.get("TERM", "") == "dumb":
                self._color_depth = ColorDepth.DEPTH_1_BIT
            colorterm = os.environ.get("COLORTERM", "")
            if "truecolor" in colorterm or "24bit" in colorterm:
                self._color_depth = ColorDepth.DEPTH_24_BIT
            elif "256" in os.environ.get("TERM", ""):
                self._color_depth = ColorDepth.DEPTH_8_BIT

        return super().color_depth

    @property
    def syntax_theme(self) -> str:
        """Calculate the current syntax theme."""
        syntax_theme = self.config.syntax_theme
        if syntax_theme == self.config.defaults.syntax_theme:
            syntax_theme = "tango" if self.color_palette.bg.is_light else "euporie"
        return syntax_theme

    base_styles = (
        Style(MIME_STYLE),
        Style(HTML_STYLE),
        Style(LOG_STYLE),
        Style(IPYWIDGET_STYLE),
        Style(DIAGNOSTIC_STYLE),
    )

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
            **self.term_colors,
            **theme_colors.get(self.config.color_scheme, theme_colors["default"]),
        }

        # Build a color palette from the fg/bg colors
        self.color_palette = cp = ColorPalette()
        for name, color in base_colors.items():
            cp.add_color(
                name,
                color or theme_colors["default"][name],
                "default" if name in ("fg", "bg") else name,
            )
        # Add accent color
        # self.color_palette.add_color(
        #     "hl",
        #     (bg := self.color_palette.bg)
        #     .adjust(
        #         hue=(bg.hue + (bg.hue - 0.036)) % 1,
        #         saturation=(0.88 - bg.saturation),
        #         brightness=0.4255 - bg.brightness,
        #     )
        #     .base_hex,
        # )
        cp.add_color(
            "hl", base_colors.get(self.config.accent_color, self.config.accent_color)
        )

        # Build app style
        styles: list[BaseStyle] = [
            style_from_pygments_cls(get_style_by_name(self.syntax_theme)),
            *self.base_styles,
            build_style(cp),
        ]

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

        # Add user style customizations
        if custom_style_dict := self.config.custom_styles:
            styles.append(Style.from_dict(custom_style_dict))

        return merge_styles(styles)

    def update_style(self, query: Setting | None = None) -> None:
        """Tell the application the style is out of date."""
        self.style_invalid = True

    def do_style_update(self, caller: Application | None = None) -> None:
        """Update the application's style when the syntax theme is changed."""
        if self.style_invalid:
            self.style_invalid = False
            self.renderer.style = self.create_merged_style()
            # self.invalidate()
            # self.renderer.reset()

    def refresh(self) -> None:
        """Reset all tabs."""
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
        self.layout.current_window = Window()
        # Re-draw the app
        self._redraw(render_as_done=render_as_done)
        # Remove the focus block
        self.layout.focus_last()
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

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.app.app:BaseApp": {
                "quit": ["c-q", "<sigint>"],
                "close-tab": "c-w",
                "next-tab": "c-pagedown",
                "previous-tab": "c-pageup",
                "focus-next": "tab",
                "focus-previous": "s-tab",
                "clear-screen": "c-l",
                "open-file": "c-o",
                "save-as": "A-s",
            }
        }
    )
