"""Contains the main Application class which runs euporie."""

from __future__ import annotations

import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application import Application, get_app_session
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition, Filter
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.styles import (
    BaseStyle,
    ConditionalStyleTransformation,
    SetDefaultColorStyleTransformation,
    Style,
    SwapLightAndDarkStyleTransformation,
    default_ui_style,
    merge_style_transformations,
    merge_styles,
    style_from_pygments_cls,
)
from pygments.styles import get_style_by_name  # type: ignore

from euporie.config import config
from euporie.graphics import TerminalGraphicsRenderer
from euporie.key_binding import load_key_bindings
from euporie.key_binding.micro_state import MicroState
from euporie.log import setup_logs
from euporie.notebook import Notebook
from euporie.style import color_series
from euporie.tab import Tab
from euporie.terminal import TerminalInfo

if TYPE_CHECKING:
    from collections.abc import MutableSequence
    from typing import Any, Optional, Type

    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.output import Output

    from euporie.graphics import TerminalGraphic

log = logging.getLogger(__name__)


class EuporieApp(Application):
    """The base euporie application class.

    This subclasses the `prompt_toolkit.application.Application` class, so application
    wide methods can be easily added.
    """

    # This configures the logs for euporie
    setup_logs()

    def __init__(self, **kwargs: "Any") -> "None":
        """Instantiates euporie specific application variables.

        After euporie specific application variables are instantiated, the application
        instance is initiated.

        Args:
            **kwargs: The key-word arguments for the :py:class:`Application`

        """
        # Set app super early
        get_app_session().app = self
        self._is_running = False
        # These will be re-applied after superinit
        self.pre_run_callables = []
        # Which notebook class should we use
        self.notebook_class: "Type[Notebook]"
        # Containes the opened tab contianers
        self.tabs: "MutableSequence[Tab]" = []
        self._tab_idx = 0
        # Create conditions
        self.has_tab = Condition(lambda: bool(self.tabs))
        # Load the output
        self.output = self.load_output()
        # Inspect terminal feautres
        self.term_info = TerminalInfo(self.output)

        # Load graphics system
        graphics_system: "Optional[Type[TerminalGraphic]]" = None
        if self.term_info.has_kitty_graphics:
            from euporie.graphics.kitty import KittyTerminalGraphic

            graphics_system = KittyTerminalGraphic
        elif self.term_info.has_sixel_graphics:
            from euporie.graphics.sixel import SixelTerminalGraphic

            graphics_system = SixelTerminalGraphic
        self.graphics_renderer = TerminalGraphicsRenderer(graphics_system)

        # Open any files we need to open
        self.open_files()
        # Load the main app container
        self.layout = Layout(self.load_container())
        # Load key bindings
        self.key_bindings = load_key_bindings()
        # Add state for micro key-bindings
        self.micro_state = MicroState()

        pre_run = self.pre_run_callables[:]
        super().__init__(
            layout=self.layout,
            output=self.output,
            key_bindings=self.key_bindings,
            min_redraw_interval=0.1,
            color_depth=self.term_info.color_depth,
            **kwargs,
        )
        self.pre_run_callables = pre_run

    @classmethod
    def launch(cls) -> "None":
        """Launches the app, opening any command line arguments as files."""
        app = cls()
        app.run()

    def load_container(self) -> "AnyContainer":
        """Loads the root container for this application.

        Returns:
            The root container for this app

        """
        return Window()

    def load_output(self) -> "Output":
        """Creates the output for this application to use.

        Returns:
            A prompt-toolkit output instance

        """
        return create_output()

    def open_files(self) -> "None":
        """Opens the files defined in the configuration."""
        for file in config.files:
            self.open_file(file)

    def open_file(self, path: "Path", read_only: "bool" = False) -> None:
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

    def close_tab(self, tab: "Optional[Tab]" = None) -> None:
        """Closes a notebook tab.

        Args:
            tab: The instance of the tab to close. If `None`, the currently
                selected tab will be closed.

        """
        if tab is None:
            tab = self.tab
        if tab is not None:
            tab.close(cb=partial(self.cleanup_closed_tab, tab))

    def cleanup_closed_tab(self, tab: "Tab") -> None:
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

    def set_edit_mode(self, mode: "EditingMode") -> "None":
        """Sets the keybindings for editing mode.

        Args:
            mode: One of default, vi, or emacs

        """
        config.edit_mode = str(mode)
        self.editing_mode = self.get_edit_mode()
        log.debug("Editing mode set to: %s", self.editing_mode)

    def get_edit_mode(self) -> "EditingMode":
        """Returns the editing mode enum defined in the configuration."""
        return cast(
            EditingMode,
            {
                "micro": "MICRO",
                "vi": EditingMode.VI,
                "emacs": EditingMode.EMACS,
            }.get(str(config.edit_mode), "micro"),
        )

    def update_style(
        self,
        pygments_style: "Optional[str]" = None,
        color_scheme: "Optional[str]" = None,
    ) -> "None":
        """Updates the application's style when the syntax theme is changed."""
        if pygments_style is not None:
            config.syntax_theme = pygments_style
        if color_scheme is not None:
            config.color_scheme = color_scheme
        self.renderer.style = self._create_merged_style()

    def _create_merged_style(
        self, include_default_pygments_style: "Filter" = None
    ) -> "BaseStyle":
        base_colors: "dict[str, str]" = {
            "light": {"fg": "#000000", "bg": "#FFFFFF"},
            "dark": {"fg": "#FFFFFF", "bg": "#000000"},
        }.get(
            config.color_scheme,
            {"fg": self.term_info.fg_color, "bg": self.term_info.bg_color},
        )
        series = color_series(**base_colors, n=10)

        # Actually use default colors if in default mode
        # This is needed for transparent terminals and the like
        if config.color_scheme == "default":
            series["fg"][0] = "default"
            series["bg"][0] = "default"

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

        style_dict = {
            # The default style is merged at this point so full styles can be
            # overridden. For example, this allows us to switch off the underline
            #  status of cursor-line.
            **dict(default_ui_style().style_rules),
            "default": f"fg:{series['bg'][0]} bg:{series['bg'][0]}",
            # Logo
            "logo": "fg:#ff0000",
            # Pattern
            "pattern": f"fg:{config.background_color or series['bg'][1]}",
            # Chrome
            "chrome": f"fg:{series['bg'][1]} bg:{series['bg'][1]}",
            # Statusbar
            "status": f"fg:{series['fg'][1]} bg:{series['bg'][1]}",
            "status.field": f"fg:{series['fg'][2]} bg:{series['bg'][2]}",
            # Menus & Menu bar
            "menu-bar": f"fg:{series['fg'][1]} bg:{series['bg'][1]}",
            "menu-bar.disabled-item": f"fg:{series['bg'][5]}",
            "menu-bar.selected-item": "reverse",
            "menu-bar.shortcut": f"fg:{series['fg'][9]}",
            "menu-bar.selected-item menu-bar.shortcut": (
                f"fg:{series['fg'][1]} bg:{series['bg'][5]}"
            ),
            "menu-bar.disabled-item menu-bar.shortcut": f"fg:{series['bg'][5]}",
            "menu": f"bg:{series['bg'][1]} fg:{series['fg'][1]}",
            # Buffer
            "line-number": f"fg:{series['fg'][1]} bg:{series['bg'][1]}",
            "line-number.current": "bold orange",
            "cursor-line": f"bg:{series['bg'][1]}",
            # Cells
            "cell.border": f"fg:{series['bg'][5]}",
            "cell.border.selected": "fg:#00afff",
            "cell.border.edit": "fg:#00ff00",
            "cell.border.hidden": f"fg:{series['bg'][0]}",
            "cell.input": "fg:default bg:default",
            "cell.output": "fg:default bg:default",
            "cell.input.prompt": "fg:blue",
            "cell.output.prompt": "fg:red",
            # Scrollbars
            "scrollbar": f"fg:{series['fg'][5]} bg:{series['bg'][5]}",
            "scrollbar.background": "",
            "scrollbar.button": "",
            "scrollbar.arrow": "",
            # Dialogs
            "dialog.body scrollbar": "reverse",
            "dialog shadow": "bg:#888888",
            "dialog.body": "bg:#b0b0b0 #000000",
            # Horizontals rule
            "hr": "fg:#666666",
            # Completions menu
            "completion-menu.completion.keyword": "fg:#d700af",
            "completion-menu.completion.current.keyword": "fg:#fff bg:#d700ff",
            "completion-menu.completion.function": "fg:#005faf",
            "completion-menu.completion.current.function": "fg:#fff bg:#005fff",
            "completion-menu.completion.class": "fg:#008700",
            "completion-menu.completion.current.class": "fg:#fff bg:#00af00",
            "completion-menu.completion.statement": "fg:#5f0000",
            "completion-menu.completion.current.statement": "fg:#fff bg:#5f0000",
            "completion-menu.completion.instance": "fg:#d75f00",
            "completion-menu.completion.current.instance": "fg:#fff bg:#d78700",
            "completion-menu.completion.module": "fg:#d70000",
            "completion-menu.completion.current.module": "fg:#fff bg:#d70000",
            # Log
            "log.level.nonset": "fg:grey",
            "log.level.debug": "fg:green",
            "log.level.info": "fg:blue",
            "log.level.warning": "fg:yellow",
            "log.level.error": "fg:red",
            "log.level.critical": "fg:red bold",
            "log.ref": "fg:grey",
            "log.date": "fg:#00875f",
            # "log.msg": "fg:default",
        }

        # Using a dynamic style has serious performance issues, so instead we update
        # the style on the renderer directly when it changes in `self.update_style`
        return merge_styles(
            [
                Style.from_dict(style_dict),
                style_from_pygments_cls(get_style_by_name(config.syntax_theme)),
            ]
        )

    @property
    def notebook(self) -> "Optional[Notebook]":
        """Return the currently active notebook."""
        if isinstance(self.tab, Notebook):
            return self.tab
        return None
