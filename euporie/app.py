# -*- coding: utf-8 -*-
"""Contains the main Application class which runs euporie."""
from __future__ import annotations

import logging
import sys
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional, Union

from prompt_toolkit.application import Application
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition, Filter
from prompt_toolkit.formatted_text import fragment_list_to_text, to_formatted_text
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.layout import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
    to_container,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.styles import BaseStyle, Style, default_ui_style, merge_styles
from prompt_toolkit.styles.pygments import style_from_pygments_cls
from prompt_toolkit.widgets import (
    Button,
    Dialog,
    Label,
    MenuContainer,
    MenuItem,
    TextArea,
)
from pygments.styles import get_all_styles, get_style_by_name  # type: ignore

from euporie import __version__, _app_name, logo
from euporie.config import config
from euporie.keys import KeyBindingsInfo
from euporie.log import log_memory
from euporie.menu import SmartMenuItem
from euporie.notebook import Notebook
from euporie.term import TermAppMixin
from euporie.text import ANSI, FormatTextProcessor

if TYPE_CHECKING:
    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer

log = logging.getLogger(__name__)


class App(Application, TermAppMixin):
    """The main euporie application class.

    This subclasses the `prompt_toolkit.application.Application` class, so application
    wide methods can be easily added.
    """

    def __init__(self) -> "None":
        """Instantiates euporie specific application variables.

        After euporie specific application variables are instantiated, the application
        instance is initiated.
        """
        self.open_paths: "list[Path]" = []
        self.files: "list[Notebook]" = []
        self.last_selected_index: int = 0

        self.include_default_pygments_style = False

        self.ttimeoutlen = 0.1

        self.file_open = Condition(lambda: bool(self.files))

        super().__init__(
            layout=self.build_layout(),
            enable_page_navigation_bindings=True,
            mouse_support=True,
            key_bindings=self.load_key_bindings(),
            full_screen=True,
            style=None,
            editing_mode=self.get_edit_mode(),
        )

        # Ensure a file is focused if one has been opened
        self.pre_run_callables = [lambda: self.file_op("focus")]

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
            "scrollbar.background": "bg:#444444",
            "scrollbar.button": "bg:#aaaaaa",
            "scrollbar.arrow": "fg: #aaaaaa bg:#444444",
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

    def build_layout(self) -> "Layout":
        """Builds the main application layout."""
        kernel_status_repr = {
            "starting": "◍",
            "idle": "○",
            "busy": "●",
            "error": "☹",
        }

        def get_statusbar_text() -> "list[tuple[str, str]]":
            """Generates the formatted text for the statusbar."""
            file = self.file
            assert isinstance(file, Notebook)
            kernel_status = kernel_status_repr.get(file.kernel_status, "◌")
            selected_cell = file.page.selected_index + 1
            dirt = "*" if file.dirty else ""
            return [
                ("class:menu-bar.item", f" Cell {selected_cell} "),
                ("", " "),
                ("class:menu-bar.item bold", f" {dirt}{file.path.name} "),
                ("", " "),
                ("class:menu-bar.item", f" {file.kernel_name} {kernel_status} "),
            ]

        status_bar_text = FormattedTextControl(
            get_statusbar_text, focusable=True, show_cursor=False
        )
        self.status_bar = ConditionalContainer(
            Window(
                content=status_bar_text,
                height=D.exact(1),
                style="class:menu-bar",
                dont_extend_width=True,
                align=WindowAlign.RIGHT,
            ),
            filter=self.file_open,
        )

        self.body_container = MenuContainer(
            body=HSplit([VSplit(self.files)]),
            menu_items=[
                MenuItem(
                    " File ",
                    children=[
                        MenuItem(
                            "New", handler=lambda: self.ask_open_file(validate=False)
                        ),
                        MenuItem("Open", handler=self.ask_open_file),
                        MenuItem("-", disabled=True),
                        SmartMenuItem(
                            "Save",
                            handler=lambda: self.file_op("save"),
                            disabler=~self.file_open,
                        ),
                        SmartMenuItem(
                            "Close", handler=self.close_file, disabler=~self.file_open
                        ),
                        MenuItem("-", disabled=True),
                        MenuItem("Exit", handler=self.try_to_exit),
                    ],
                ),
                MenuItem(
                    " Edit ",
                    children=[
                        SmartMenuItem(
                            "Cut Cell",
                            handler=lambda: self.file_op("cut"),
                            disabler=~self.file_open,
                        ),
                        SmartMenuItem(
                            "Copy Cell",
                            handler=lambda: self.file_op("copy"),
                            disabler=~self.file_open,
                        ),
                        SmartMenuItem(
                            "Paste Cell",
                            handler=lambda: self.file_op("paste"),
                            disabler=~self.file_open,
                        ),
                    ],
                ),
                MenuItem(
                    " Kernel ",
                    children=[
                        MenuItem(
                            "Restart Kernel",
                            handler=lambda: self.file_op("restart_kernel"),
                        ),
                        MenuItem(
                            "Change Kernel...",
                            handler=lambda: self.file_op("change_kernel"),
                        ),
                    ],
                ),
                MenuItem(
                    " Settings ",
                    children=[
                        MenuItem(
                            "Syntax Theme",
                            children=[
                                SmartMenuItem(
                                    style,
                                    handler=partial(self.update_style, style),
                                    toggler=Condition(
                                        partial(
                                            lambda x: config.pygments_style == x, style
                                        )
                                    ),
                                )
                                for style in sorted(get_all_styles())
                            ],
                        ),
                        MenuItem(
                            "Editing Key Bindings",
                            children=[
                                SmartMenuItem(
                                    "Emacs",
                                    handler=lambda: self.set_edit_mode("emacs"),
                                    toggler=Condition(
                                        lambda: config.editing_mode == "emacs"
                                    ),
                                ),
                                SmartMenuItem(
                                    "Vi",
                                    handler=lambda: self.set_edit_mode("vi"),
                                    toggler=Condition(
                                        lambda: config.editing_mode == "vi"
                                    ),
                                ),
                            ],
                        ),
                        MenuItem(
                            "Switch Background Pattern",
                            handler=lambda: config.toggle("background"),
                        ),
                        SmartMenuItem(
                            "Run cell after external edit",
                            toggler=Condition(
                                lambda: bool(config.execute_after_external_edit)
                            ),
                            handler=lambda: config.toggle(
                                "execute_after_external_edit"
                            ),
                        ),
                    ],
                ),
                MenuItem(
                    " Help ",
                    children=[
                        MenuItem("Keyboard Shortcuts", handler=self.help_keys),
                        MenuItem("Logs", handler=self.help_logs),
                        MenuItem("About", handler=self.help_about),
                    ],
                ),
            ],
        )

        self.logo = FormattedTextControl(
            [("", f" {logo} ")],
            focusable=True,
            show_cursor=False,
            style="class:menu-bar.item,logo",
        )

        # Add logo and status bar into menubar
        assert isinstance(self.body_container.container.content, HSplit)
        self.body_container.container.content.children = [
            VSplit(
                [
                    Window(self.logo, height=D.exact(1), dont_extend_width=True),
                    self.body_container.window,
                    self.status_bar,
                ]
            ),
            self.body_container.container.content.children[1],
        ]

        self.root_container = FloatContainer(
            content=self.body_container,
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=16, scroll_offset=1),
                )
            ],
        )

        return Layout(self.root_container)

    def load_key_bindings(self) -> "KeyBindings":
        """Define application-wide keybindings."""
        kb = KeyBindingsInfo()

        in_edit_mode = Condition(
            lambda: bool(self.file and self.file.cell and self.file.cell.is_editing())
        )

        @kb.add("c-n", group="Application", desc="Create a new notebook file")
        def new(event: "KeyPressEvent") -> None:
            self.ask_open_file(validate=False)

        @kb.add("c-o", group="Application", desc="Open file")
        def open(event: "KeyPressEvent") -> None:
            self.ask_open_file()

        @kb.add("c-w", group="Application", desc="Close the current file")
        def close(event: "KeyPressEvent") -> None:
            self.close_file(self.file)

        @kb.add("c-q", group="Application", desc="Quit euporie")
        def exit(event: "KeyPressEvent") -> None:
            self.try_to_exit()

        kb.add(
            "tab", filter=~in_edit_mode, group="Navigation", desc="Focus next element"
        )(focus_next)
        kb.add(
            "s-tab",
            filter=~in_edit_mode,
            group="Navigation",
            desc="Focus previous element",
        )(focus_previous)

        return kb

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

    def try_to_exit(self) -> "None":
        """Check for unsaved files before closing.

        Creates a chain of close file commands, where the callback for each triggers
        the closure of the next. The closing process can be cancelled anywhere along
        the chain.
        """
        if self.files:

            def final_cb() -> "None":
                """Really exit after the last file in the chain is closed."""
                self.cleanup_closed_file(self.files[0])
                self.exit()

            def create_cb(
                close_file: "Notebook", cleanup_file: "Notebook", cb: "Callable"
            ) -> "Callable":
                """Generate a file close chaining callbacks.

                Cleans up after the previously closed file, and requests to close the
                next file in the chain.

                Args:
                    close_file: The file to close
                    cleanup_file: The previously closed file to cleanup
                    cb: The callback to call when work is complete

                Returns:
                    A callback function which cleans up `cleanup_file` and closes
                        `close_file`.

                """

                def inner() -> None:
                    self.cleanup_closed_file(cleanup_file)
                    close_file.close(cb=cb)

                return inner

            cb = final_cb
            for close_file, cleanup_file in zip(self.files, self.files[1:]):
                cb = create_cb(close_file, cleanup_file, cb)
            self.files[-1].close(cb)
        else:
            self.exit()

    def ask_open_file(
        self,
        default: "str" = "",
        validate: "bool" = True,
        error: "Optional[str]" = None,
    ) -> None:
        """Display a dialog asking for file name input.

        Args:
            default: The default filename to display in the text entry box
            validate: Whether to disallow files which do not exist
            error: An optional error message to display below the file name

        """

        def _open_cb() -> None:
            path = filepath.text
            if not validate or Path(path).expanduser().exists():
                self.open_file(filepath.text)
            else:
                self.ask_open_file(
                    default=filepath.text, validate=validate, error="File not found"
                )

        filepath = TextArea(text=default, multiline=False)
        body_contents: "list[AnyContainer]" = [
            Label("Enter file name:"),
            filepath,
        ]
        if error:
            body_contents.append(to_container(Label(error, style="red")))
        self.dialog(
            title="Select file",
            body=HSplit(body_contents),
            buttons={
                "OK": _open_cb,
                "Cancel": None,
            },
            to_focus=filepath,
        )

    def open_file(self, path: "Union[str, Path]") -> None:
        """Opens a notebook file.

        Args:
            path: The file path of the notebook file to open

        """
        path = Path(path).expanduser()
        log.info(f"Opening file {path}")
        open_paths = [x.path for x in self.files]
        if path in open_paths:
            log.info(f"File {path} already open, activating")
            file = self.files[open_paths.index(path)]
        else:
            self.open_paths.append(path)
            file = Notebook(path)
            self.files.append(file)
        assert isinstance(self.body_container.body, HSplit)
        self.body_container.body.children[0] = VSplit(self.files)
        # Focus newly opened file
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
        assert isinstance(self.body_container.body, HSplit)
        self.body_container.body.children[0] = VSplit(self.files)
        # Focus another file if one exists
        if self.files:
            self.file_op("focus")
        # If a file is not open, the status bar is not shown, so focus the logo, so
        # pressing tab focuses the menu
        else:
            self.layout.focus(self.logo)

    @property
    def file(self) -> "Optional[Notebook]":
        """Return the currently selected file container object."""
        if self.files:
            index = min(self.selected_index, len(self.files) - 1)
            return self.files[index]
        else:
            return None

    def dialog(
        self,
        title: "AnyFormattedText",
        body: "AnyContainer",
        buttons: "dict[str, Optional[Callable]]",
        to_focus: "Optional[AnyContainer]" = None,
    ) -> None:
        """Display a modal dialog above the application.

        Returns focus to the previously selected control when closed.

        Args:
            title: The title of the dialog. Can be formatted text.
            body: The container to use as the main body of the dialog.
            buttons: A dictionary mapping text to display as dialog buttons to
                callbacks to run when the button is clicked. If the callback is
                `None`, the dialog will be closed without running a callback.
            to_focus: The control to focus when the dialog is displayed.

        """

        def _make_handler(cb: "Optional[Callable]") -> "Callable":
            def inner() -> "None":
                self.root_container.floats.remove(dialog)
                self.layout.focus(focused)
                if cb:
                    cb()

            return inner

        focused = self.layout.current_control

        button_widgets = [
            Button(text, _make_handler(cb), left_symbol="[", right_symbol="]")
            for text, cb in buttons.items()
        ]

        dialog = Float(
            Dialog(
                title=title,
                body=body,
                buttons=button_widgets,
                modal=True,
                with_background=True,
            )
        )
        self.root_container.floats.append(
            dialog,
        )
        if to_focus is None:
            to_focus = button_widgets[0]
        self.layout.focus(to_focus)

    def help_keys(self) -> None:
        """Displays details of registered key-bindings in a dialog."""
        key_details = KeyBindingsInfo.to_formatted_text()
        plain_key_details = fragment_list_to_text(key_details)
        body = TextArea(
            text=plain_key_details,
            multiline=True,
            focusable=True,
            wrap_lines=False,
            input_processors=[FormatTextProcessor(key_details)],
            width=D(
                preferred=max([len(line) for line in plain_key_details.split("\n")]) + 2
            ),
            scrollbar=True,
        )

        self.dialog(
            title="Keyboard Shortcuts",
            body=body,
            buttons={"OK": None},
        )

    def help_logs(self) -> None:
        """Displays a dialog with logs."""
        log_memory.seek(0)
        log_data = to_formatted_text(ANSI(log_memory.read()))
        plain_log_data = fragment_list_to_text(log_data)

        body = TextArea(
            text=plain_log_data,
            multiline=True,
            focusable=True,
            wrap_lines=False,
            input_processors=[FormatTextProcessor(log_data)],
            width=D(preferred=120),
            scrollbar=True,
        )
        self.dialog(
            title="Logs",
            body=body,
            buttons={"OK": None},
        )

    def help_about(self) -> None:
        """Displays an about dialog."""
        self.dialog(
            title="About",
            body=Window(
                FormattedTextControl(
                    [
                        ("class:logo", logo),
                        ("bold", f" {_app_name}"),
                        ("", f"Version {__version__}\n\n".rjust(27, " ")),
                        ("", "A TUI editor for Jupyter notebooks\n"),
                        ("class:hr", "─" * 34 + "\n\n"),
                        ("", "© 2021 Josiah Outram Halstead"),
                    ]
                ),
                dont_extend_height=True,
            ),
            buttons={"OK": None},
        )

    @classmethod
    def launch(cls) -> None:
        """Launches the app, opening any command line arguments as files."""
        app = cls()
        for path in sys.argv[1:]:
            app.open_file(path)
        app.run()
