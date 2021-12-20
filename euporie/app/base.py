# -*- coding: utf-8 -*-
"""Contains the main Application class which runs euporie."""
from __future__ import annotations

import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit.application import Application, get_app_session
from prompt_toolkit.filters import Condition, Filter
from prompt_toolkit.key_binding import KeyPressEvent
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.output import ColorDepth
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
from euporie.keys import KeyBindingsInfo
from euporie.log import setup_logs
from euporie.notebook import Notebook
from euporie.style import color_series
from euporie.tab import Tab
from euporie.term import TerminalQuery

if TYPE_CHECKING:
    from collections.abc import MutableSequence
    from typing import Any, Optional, Type

    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.output import Output

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
        self.term = TerminalQuery(self.output)
        # Open any files we need to open
        self.open_files()
        # Load the main app container
        self.layout = Layout(self.load_container())
        # Load key bindings
        self.key_bindings = self.load_key_bindings()

        pre_run = self.pre_run_callables[:]
        super().__init__(
            layout=self.layout,
            output=self.output,
            key_bindings=self.key_bindings,
            color_depth=ColorDepth.DEPTH_24_BIT,
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
                if self.layout.has_focus(tab):
                    self._tab_idx = i
                    break
            self._tab_idx = min(self._tab_idx, len(self.tabs) - 1)
            return self.tabs[self._tab_idx]
        else:
            return None

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

    def load_key_bindings(self) -> "KeyBindingsInfo":
        """Define application-wide keybindings."""
        kb = KeyBindingsInfo()

        @kb.add("c-q", group="Application", desc="Quit euporie")
        def exit(event: "KeyPressEvent") -> None:
            self.exit()

        return kb

    def _create_merged_style(
        self, include_default_pygments_style: "Filter" = None
    ) -> "BaseStyle":
        base_colors: "dict[str, str]" = {
            "light": {"fg": "#000000", "bg": "#FFFFFF"},
            "dark": {"fg": "#FFFFFF", "bg": "#000000"},
        }.get(config.color_scheme, {"fg": self.term.fg_color, "bg": self.term.bg_color})
        series = color_series(**base_colors)

        self.style_transformation = merge_style_transformations(
            [
                SetDefaultColorStyleTransformation(**base_colors),
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
            "menu-bar.selected-item": "reverse",
            "menu": f"bg:{series['bg'][1]} fg:{series['fg'][1]}",
            # Buffer
            "line-number": f"fg:{series['fg'][1]} bg:{series['bg'][1]}",
            "line-number.current": "bold",
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
