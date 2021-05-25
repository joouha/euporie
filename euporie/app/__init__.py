# -*- coding: utf-8 -*-
"""Contains the main Application class which runs euporie."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional, Union

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import _current_app_session
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition, Filter
from prompt_toolkit.input import DummyInput
from prompt_toolkit.layout import to_container
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import BaseStyle, Style, default_ui_style, merge_styles
from prompt_toolkit.styles.pygments import style_from_pygments_cls
from pygments.styles import get_style_by_name  # type: ignore

from euporie.app.dump import DumpMixin
from euporie.app.interface import InterfaceMixin
from euporie.app.term import TermMixin
from euporie.config import config
from euporie.notebook import Notebook

if TYPE_CHECKING:
    from prompt_toolkit.output.base import Output

log = logging.getLogger(__name__)


class App(TermMixin, Application):
    """The main euporie application class.

    This subclasses the `prompt_toolkit.application.Application` class, so application
    wide methods can be easily added.
    """

    output: "Output"
    load_key_bindings: "Callable"
    setup: "Callable"
    layout_container: "Callable"
    dialog: "Callable"

    def __init__(self) -> "None":
        """Instantiates euporie specific application variables.

        After euporie specific application variables are instantiated, the application
        instance is initiated.
        """
        # Attributes
        self.open_paths: "list[Path]" = []
        self.files: "list[Notebook]" = []
        self.last_selected_index: int = 0
        # self.file_container = VSplit([])

        # Application properties
        self.include_default_pygments_style = False
        self.ttimeoutlen = 0.1
        self.pre_run: "list[Callable]" = []
        # Create an empty layout - we will add a real container to it later
        self.layout = Layout(Window())

        # Conditions
        self.is_file_open = Condition(lambda: bool(self.files))

        # Process config
        self.configure()

    def configure(self) -> "None":
        """Configures the application according to the configuration."""
        kwargs: "dict[str, Any]" = {}

        if config.dump:
            # Add  methods for file dumping to this class
            self.mix_in_mixin(DumpMixin)
            # Configure the application
            kwargs.update(
                input=DummyInput(),
            )

        else:
            # Add methods for file dumping to this class
            self.mix_in_mixin(InterfaceMixin)
            # Configure the application
            kwargs.update(
                mouse_support=True,
                key_bindings=self.load_key_bindings(),
                full_screen=True,
                style=None,
                editing_mode=self.get_edit_mode(),
                clipboard=PyperclipClipboard(),
            )

        # Create an output early so it can terminal attribute detection
        self.setup()

        # Set this app as the currently ap in the current app session
        # This is necessary for calls to get_app in UI elements
        _current_app_session.get().app = self

        # Open files
        for file in config.files:
            self.open_file(file)

        # Update the container in the layout
        self.layout.container = to_container(self.layout_container())

        # Finilize initiate of the application, ensuring already configured attributes
        # are retained
        super().__init__(
            layout=self.layout,
            output=self.output,
            **kwargs,
        )

        # Retain the configured pre-run commands
        self.pre_run_callables = self.pre_run

    def mix_in_mixin(self, *mixins: "type") -> "None":
        """Adds a mixin to an App instance.

        Args:
            *mixins: The mixin classes to add.

        """
        base_cls = self.__class__
        base_cls_name = self.__class__.__name__
        self.__class__ = type(base_cls_name, (*mixins, base_cls), {})

    @classmethod
    def launch(cls) -> None:
        """Launches the app, opening any command line arguments as files."""
        app = cls()
        app.run()

    @property
    def selected_index(self) -> "int":
        """Returns the index of the selected file."""
        # Detect if focused file has changed
        # Find index of selected child
        index = 0
        for i, file in enumerate(self.files):
            if self.layout.has_focus(file):
                index = i
                break
        else:
            index = self.last_selected_index
        # This will perform change the position when the new child is selected
        self.last_selected_index = index
        return self.last_selected_index

    @property
    def file(self) -> "Optional[Notebook]":
        """Return the currently selected file container object."""
        if self.files:
            index = min(self.selected_index, len(self.files) - 1)
            return self.files[index]
        else:
            return None

    def set_edit_mode(self, mode: "str") -> "None":
        """Sets the keybindings for editing mode.

        Args:
            mode: 'vi' or 'emacs'

        """
        config.editing_mode = mode
        self.editing_mode = self.get_edit_mode()

    def get_edit_mode(self) -> "EditingMode":
        """Returns the editing mode enum defined in the configuration."""
        return {"emacs": EditingMode.EMACS, "vi": EditingMode.VI}.get(
            str(config.editing_mode), EditingMode.EMACS
        )

    def _create_merged_style(
        self, include_default_pygments_style: Filter = None
    ) -> BaseStyle:

        # Calculate colors based on terminal background colour if we can
        if self.bg_color:
            from prompt_toolkit.styles import (
                DEFAULT_ATTRS,
                AdjustBrightnessStyleTransformation,
            )

            tr = AdjustBrightnessStyleTransformation(
                min_brightness=0.05, max_brightness=0.92
            )
            dim_bg = "#{}".format(
                tr.transform_attrs(
                    DEFAULT_ATTRS._replace(color=self.bg_color.lstrip("#"))
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
            "background": "fg:#888888",
            "menu-bar": "fg:#ffffff bg:#222222",
            "menu-bar.item": "bg:#444444",
            "menu": "fg:#ffffff bg:#222222",
            "cell-border": "fg:#4e4e4e",
            "cell-border-selected": "fg:#00afff",
            "cell-border-edit": "fg:#00ff00",
            "cell-input": "fg:default",
            "line-number": f"fg:#888888 bg:{dim_bg}",
            "line-number.current": "bold",
            "cursor-line": f"bg:{dim_bg}",
            "cell-output": "fg:default",
            "cell-input-prompt": "fg:darkblue",
            "cell-output-prompt": "fg:darkred",
            "scrollbar.background": "fg:#aaaaaa bg:#444444",
            "scrollbar.button": "fg:#444444 bg:#aaaaaa",
            "scrollbar.arrow": "fg: #aaaaaa bg:#444444",
            "dialog.body scrollbar": "reverse",
            "dialog shadow": "bg:#888888",
            "dialog.body": "bg:#b0b0b0 #000000",
            "hr": "fg:#666666",
        }

        # Using a dynamic style has serious performance issues, so instead we update
        # the style on the renderer directly when it changes in `self.update_style`
        return merge_styles(
            [
                Style.from_dict(style_dict),
                style_from_pygments_cls(get_style_by_name(config.pygments_style)),
            ]
        )

    def update_style(self, pygments_style: "str") -> "None":
        """Updates the application's style when the syntax theme is changed."""
        config.pygments_style = pygments_style
        self.renderer.style = self._create_merged_style()

    def open_file(self, path: "Union[str, Path]", read_only: "bool" = False) -> None:
        """Opens a notebook file.

        Args:
            path: The file path of the notebook file to open
            read_only: If true, the file should be opened read_only

        """
        path = Path(path).expanduser()
        log.info(f"Opening file {path}")
        open_paths = [x.path for x in self.files]
        if path in open_paths:
            log.info(f"File {path} already open, activating")
            file = self.files[open_paths.index(path)]
        else:
            self.open_paths.append(path)
            file = Notebook(
                path,
                interactive=not config.dump,
                # execute=config.execute,
                scroll=not bool(config.dump),
            )
            self.files.append(file)
        file.focus()

    def file_op(
        self,
        operation: "str",
        file: "Optional[Notebook]" = None,
        args: "Optional[list[Any]]" = None,
        kwargs: "Optional[Mapping[str, Any]]" = None,
    ) -> None:
        """Call a function from the a file object.

        Args:
            operation: The name of the function to attempt to call.
            file: The instance of the file to close. If `None`, the currently
                selected file will be closed.
            args: List of parameter arguments to pass to the function
            kwargs: Mapping of keyword arguments to pass to the function

        """
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        if file is None:
            file = self.file
        if file and hasattr(file, operation):
            func = getattr(self.file, operation)
            if callable(func):
                func(*args, **kwargs)

    def close_file(self, file: "Optional[Notebook]" = None) -> None:
        """Closes a notebook file.

        Args:
            file: The instance of the file to close. If `None`, the currently
                selected file will be closed.

        """
        if file is None:
            file = self.file
        if file is not None:
            self.file_op(
                "close",
                file=file,
                kwargs={"cb": lambda: self.cleanup_closed_file(file)},
            )

    def cleanup_closed_file(self, file: "Notebook") -> None:
        """Remove a file container from the current instance of the app.

        Args:
            file: The closed instance of the file container

        """
        # Remove file
        self.files.remove(file)
        # Update body container to reflect new file list
        # assert isinstance(self.body_container.body, HSplit)
        # self.body_container.body.children[0] = VSplit(self.files)
        # Focus another file if one exists
        if self.files:
            self.file_op("focus")
        # If a file is not open, the status bar is not shown, so focus the logo, so
        # pressing tab focuses the menu
        # else:
        # self.layout.focus(self.logo)
