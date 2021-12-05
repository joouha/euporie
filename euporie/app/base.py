# -*- coding: utf-8 -*-
"""Contains the main Application class which runs euporie."""
from __future__ import annotations

import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional, Union

from prompt_toolkit.application import Application, get_app_session
from prompt_toolkit.filters import Condition, Filter
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.styles import (
    BaseStyle,
    Style,
    default_ui_style,
    merge_styles,
    style_from_pygments_cls,
)
from pygments.styles import get_style_by_name  # type: ignore

from euporie.config import config
from euporie.keys import KeyBindingsInfo
from euporie.log import setup_logs
from euporie.notebook import Notebook
from euporie.term import TerminalQuery

log = logging.getLogger(__name__)


class BaseApp(Application):
    """The base euporie application class.

    This subclasses the `prompt_toolkit.application.Application` class, so application
    wide methods can be easily added.
    """

    setup_logs()

    def __init__(self, **kwargs: "Any") -> "None":
        """Instantiates euporie specific application variables.

        After euporie specific application variables are instantiated, the application
        instance is initiated.
        """
        # Set app super early
        get_app_session().app = self
        self._is_running = False
        # These will be re-applied after superinit
        self.pre_run_callables = []
        # How notebooks should be configured
        self.notebook_kwargs = kwargs.pop("notebook_kwargs", {})
        # Containes the opened tab contianers
        self.tabs = []
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
            **kwargs,
        )
        self.pre_run_callables = pre_run

    @classmethod
    def launch(cls) -> None:
        """Launches the app, opening any command line arguments as files."""
        app = cls()
        app.run()

    def load_container(self) -> "AnyContainer":
        return Window()

    def load_output(self):
        return create_output()

    def open_files(self):
        for file in config.files:
            self.open_file(file)

    def open_file(self, path: "Union[str, Path]", read_only: "bool" = False) -> None:
        """Creates a tab for a file

        Args:
            path: The file path of the notebooknotebook file to open
            read_only: If true, the file should be opened read_only

        """
        path = Path(path).expanduser()
        log.info(f"Opening file {path}")
        for tab in self.tabs:
            if path == tab.path:
                log.info(f"File {path} already open, activating")
                break
        else:
            tab = Notebook(path, **self.notebook_kwargs, app=self)
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
            self.layout.focus_next()

    def _create_merged_style(
        self, include_default_pygments_style: "Filter" = None
    ) -> "BaseStyle":
        # Calculate colors based on terminal background colour if we can
        if self.term.bg_color:
            from prompt_toolkit.styles import (
                DEFAULT_ATTRS,
                AdjustBrightnessStyleTransformation,
            )

            tr = AdjustBrightnessStyleTransformation(
                min_brightness=0.05, max_brightness=0.92
            )
            dim_bg = "#{}".format(
                tr.transform_attrs(
                    DEFAULT_ATTRS._replace(color=self.term.bg_color.lstrip("#"))
                ).color
            )
        else:
            dim_bg = "default"

        style_dict = {
            # The default style is merged at this point so full styles can be
            # overridden. For example, this allows us to switch off the underline
            #  status of cursor-line.
            **dict(default_ui_style().style_rules),
            "logo": "fg:#ff0000",
            "background-pattern": f"fg:{config.background_color}",
            "chrome": "bg:#222222",
            "menu-bar": "fg:#ffffff bg:#222222",
            "menu-bar.item": "bg:#444444",
            "menu": "fg:#ffffff bg:#222222",
            # Statusbar
            "status": "bg:#222222 fg:#cccccc",
            "status.field": "bg:#303030",
            # Cells
            "cell-border": "fg:#4e4e4e",
            "cell-border-selected": "fg:#00afff",
            "cell-border-edit": "fg:#00ff00",
            "cell-input": "fg:default",
            "line-number": f"fg:#888888 bg:{dim_bg}",
            "line-number.current": "bold",
            "cursor-line": f"bg:{dim_bg}",
            "cell-output": "fg:default",
            "cell-input-prompt": "fg:blue",
            "cell-output-prompt": "fg:red",
            # Scrollbars
            "scrollbar": "fg:#aaaaaa bg:#444444",
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
            "log.msg": "fg:default",
        }

        # Using a dynamic style has serious performance issues, so instead we update
        # the style on the renderer directly when it changes in `self.update_style`
        return merge_styles(
            [
                Style.from_dict(style_dict),
                style_from_pygments_cls(get_style_by_name(config.syntax_theme)),
            ]
        )

    def update_style(self, pygments_style: "str") -> "None":
        """Updates the application's style when the syntax theme is changed."""
        config.syntax_theme = pygments_style
        self.renderer.style = self._create_merged_style()

    def load_key_bindings(self) -> "KeyBindings":
        """Define application-wide keybindings."""
        kb = KeyBindingsInfo()

        @kb.add("c-q", group="Application", desc="Quit euporie")
        def exit(event: "KeyPressEvent") -> None:
            self.exit()

        return kb
