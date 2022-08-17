"""Dialogs."""

from __future__ import annotations

import logging
import traceback
from abc import ABCMeta, abstractmethod
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.clipboard import ClipboardData
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.filters import (
    Condition,
    buffer_has_focus,
    has_completions,
    has_focus,
)
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    Float,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets.base import Box, Label, Shadow

from euporie.core.border import HalfBlockOuterGridStyle
from euporie.core.commands import add_cmd
from euporie.core.filters import tab_has_focus
from euporie.core.formatted_text.utils import lex
from euporie.core.key_binding.registry import register_bindings
from euporie.core.tabs.base import Tab
from euporie.core.widgets.decor import Border, FocusedStyle
from euporie.core.widgets.forms import Button, Select, Text

if TYPE_CHECKING:
    from typing import Any, Callable, Optional

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.layout import FocusableElement

    from euporie.core.app import BaseApp
    from euporie.core.tabs.base import KernelTab

log = logging.getLogger(__name__)


class Dialog(Float, metaclass=ABCMeta):
    """A modal dialog which is displayed above the application.

    Returns focus to the previously selected control when closed.
    """

    title: "Optional[AnyFormattedText]" = None
    body_padding_top = 1
    body_padding_bottom = 0

    def __init__(self, app: "BaseApp") -> None:
        """Create a modal dialog.

        title: The title of the dialog. Can be formatted text.
        body: The container to use as the main body of the dialog.
        buttons: A dictionary mapping text to display as dialog buttons to
            callbacks to run when the button is clicked. If the callback is
            `None`, the dialog will be closed without running a callback.
        to_focus: The control to focus when the dialog is displayed.

        Args:
            app: The application the dialog is attached to

        """
        self.app = app
        self.to_focus: "Optional[FocusableElement]" = None
        self.last_focused: "Optional[FocusableElement]" = None
        self._visible = False
        self.visible = Condition(lambda: self._visible)

        # Set default body & buttons
        self.body: "AnyContainer" = Window()
        self.buttons: "dict[str, Optional[Callable]]" = {"OK": None}
        self.button_widgets: "list[AnyContainer]" = []

        # Create key-bindings
        self.kb = KeyBindings()
        self.kb.add("escape")(lambda event: self.hide())
        self.kb.add("tab", filter=~has_completions)(focus_next)
        self.kb.add("s-tab", filter=~has_completions)(focus_previous)
        self.buttons_kb = KeyBindings()

        # Create title row
        title_row = ConditionalContainer(
            VSplit(
                [
                    Window(char=" ", height=1),
                    Window(
                        FormattedTextControl(lambda: self.title),
                        dont_extend_width=True,
                        height=1,
                    ),
                    Window(char=" ", height=1),
                ],
                style="class:dialog,title",
                height=1,
            ),
            filter=Condition(lambda: bool(self.title)),
        )

        # Create body row with collapsible padding around the body.
        body_row = Box(
            body=DynamicContainer(lambda: self.body),
            padding=Dimension(preferred=1, max=1),
            padding_top=self.body_padding_top,
            padding_bottom=self.body_padding_bottom,
        )

        # The buttons.
        buttons_row = ConditionalContainer(
            Box(
                body=DynamicContainer(
                    lambda: VSplit(
                        self.button_widgets, padding=1, key_bindings=self.buttons_kb
                    )
                ),
                height=Dimension(min=1, max=3, preferred=3),
            ),
            filter=Condition(lambda: bool(self.buttons)),
        )

        # Create body
        self.container = ConditionalContainer(
            Shadow(
                Border(
                    HSplit(
                        [
                            title_row,
                            body_row,
                            buttons_row,
                        ],
                        style="class:dialog,body",
                        key_bindings=self.kb,
                        modal=True,
                    ),
                    border=HalfBlockOuterGridStyle,
                    style="class:dialog,border",
                ),
            ),
            filter=self.visible,
        )

        # Set the body as the float's contents
        super().__init__(content=self.container)

    def _button_handler(
        self, button: str = "", event: "Optional[KeyPressEvent]" = None
    ) -> "None":
        if callable(cb := self.buttons.get(button)):
            cb()
        self.hide()

    def _load(self, **params: "Any") -> "None":
        """Load body, create buttons, etc."""
        self.to_focus = None

        # Load body & buttons
        self.load(**params)

        # Create button widgets & callbacks
        self.button_widgets.clear()

        if self.buttons:
            width = max(map(len, self.buttons)) + 2
            used_keys = set()
            # Add each button
            for text in self.buttons:
                # Use the first letter as a key-binding if it's not already used
                if (key := text[0]) not in used_keys:
                    rest = text[1:]
                    used_keys |= {key}
                else:
                    key = ""
                    rest = text
                # Add a button with a handler
                handler = partial(self._button_handler, text)
                self.button_widgets.append(
                    FocusedStyle(
                        Button(
                            [("underline", key), ("", rest)],
                            on_click=handler,
                            width=width,
                            style="class:input",
                        )
                    )
                )
                # Add a key-handler
                if key:
                    self.buttons_kb.add(key, filter=~buffer_has_focus)(handler)
                    self.kb.add("escape", key, filter=~buffer_has_focus)(handler)

        # When a button is selected, handle left/right key bindings.
        if len(self.button_widgets) > 1:
            first_selected = has_focus(self.button_widgets[0])
            last_selected = has_focus(self.button_widgets[-1])
            self.buttons_kb.add("left", filter=~first_selected)(focus_previous)
            self.buttons_kb.add("right", filter=~last_selected)(focus_next)

        # Focus first button by default if nothing else was specified by ``self.load()``
        if self.to_focus is None:
            self.to_focus = self.button_widgets[0]

    @abstractmethod
    def load(self) -> "None":
        """Load the dialog's body etc."""

    def show(self, **params: "Any") -> "None":
        """Displays and focuses the dialog."""
        # Re-draw the body
        self._load(**params)
        self.last_focused = self.app.layout.current_control
        self._visible = True
        if self.to_focus is not None:
            self.app.layout.focus(self.to_focus)
        else:
            try:
                self.app.layout.focus(self.container)
            except ValueError:
                pass
        self.app.layout.focus(self.container)
        self.app.invalidate()

    def hide(self, event: "KeyPressEvent" = None) -> "None":
        """Hides the dialog."""
        self._visible = False
        if self.last_focused is not None:
            try:
                self.app.layout.focus(self.last_focused)
            except ValueError:
                self.app.layout.focus_next()

    def toggle(self) -> "None":
        """Shows or hides the dialog."""
        if self._visible:
            self.hide()
        else:
            self.show()

    def __pt_container__(self) -> "AnyContainer":
        return self.container


class AboutDialog(Dialog):
    """A dialog which shows an "about" message."""

    title = "About"

    def load(self) -> "None":
        """Load the dialog's body."""
        from euporie.core import (
            __app_name__,
            __copyright__,
            __logo__,
            __strapline__,
            __version__,
        )

        self.body = Window(
            FormattedTextControl(
                [
                    ("class:logo", __logo__),
                    ("", " "),
                    ("bold", __app_name__),
                    ("", f"Version {__version__}\n\n".rjust(23, " ")),
                    ("", __strapline__.center(30)),
                    ("", "\n"),
                    ("class:hr", "─" * 30 + "\n\n"),
                    ("", __copyright__),
                    # ("", "\n"),
                ]
            ),
            dont_extend_height=True,
        )

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd()
    def _about() -> "None":
        """Show the about dialog."""
        from euporie.core.app import get_app

        if dialog := get_app().dialogs.get("about"):
            dialog.toggle()


class FileDialog(Dialog, metaclass=ABCMeta):
    """A base dialog to prompt the user for a file path."""

    title = "Select a File"
    completer = PathCompleter()

    def load(
        self, text: "str" = "", tab: "Optional[Tab]" = None, error: "str" = ""
    ) -> "None":
        """Load the dialog body."""

        def _accept_text(buf: "Buffer") -> "bool":
            """Accepts the text in the file input field and focuses the next field."""
            self.app.layout.focus_next()
            buf.complete_state = None
            return True

        filepath = Text(
            text=text,
            multiline=False,
            completer=self.completer,
            accept_handler=_accept_text,
            style="class:input",
            width=40,
        )

        self.body = HSplit(
            [
                Label("Enter file path:"),
                FocusedStyle(filepath),
                ConditionalContainer(
                    Label(lambda: error, style="red"),
                    filter=Condition(lambda: bool(error)),
                ),
            ]
        )
        self.to_focus = filepath

        self.buttons = {
            "OK": partial(self.validate, filepath.buffer, tab=tab),
            "Cancel": None,
        }

    def validate(self, buffer: "Buffer", tab: "Tab") -> "None":
        """Validate the input."""
        self.hide()


class OpenFileDialog(FileDialog):
    """A dialog which prompts the user for a filepath to open."""

    title = "Select a File to Open"

    def validate(self, buffer: "Buffer", tab: "Tab") -> "None":
        """Validate the the file to open exists."""
        from euporie.core.utils import parse_path

        path = parse_path(buffer.text)
        if path is not None and path.exists():
            self.app.open_file(path)
        else:
            self.show(error="The file path specified does not exist")

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(menu_title="Open File…")
    def _open_file() -> "None":
        """Open a file."""
        from euporie.core.app import get_app

        if dialog := get_app().dialogs.get("open-file"):
            dialog.show()

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.app.BaseApp": {
                "open-file": "c-o",
            }
        }
    )


class SaveAsDialog(FileDialog):
    """A dialog which prompts the user for a filepath to save the current tab."""

    title = "Select a Path to Save"

    def validate(self, buffer: "Buffer", tab: "Tab") -> "None":
        """Validate the the file to open exists."""
        from euporie.core.utils import parse_path

        path = parse_path(buffer.text)
        if tab and path is not None:
            tab.save(path=path)

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(
        menu_title="Save As…",
        filter=tab_has_focus,
    )
    def _save_as() -> None:
        """Save the current file at a new location."""
        from euporie.core.app import get_app

        app = get_app()
        if dialog := app.dialogs.get("save-as"):
            dialog.show(tab=app.tab)

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.app.BaseApp": {
                "save-as": ("escape", "s"),
            }
        }
    )


class NoKernelsDialog(Dialog):
    """Dialog to warn the user that no installed kernels were found."""

    title = "No Kernels Found"

    def load(self) -> "None":
        """Load the dialog body."""
        self.body = Window(
            FormattedTextControl(
                [
                    ("bold", "No Jupyter kernels were found.\n\n"),
                    ("", "You can view and edit the notebook,\n"),
                    ("", "but will not be able to run any code.\n\n"),
                    ("", "Try installing "),
                    ("class:md.code.inline", "ipykernel"),
                    ("", " by running:"),
                    ("", "\n\n"),
                    (
                        "class:md.code.inline",
                        "$ pip install --user ipykernel",
                    ),
                    ("", "\n"),
                ]
            )
        )


class SelectKernelDialog(Dialog):
    """A dialog which allows the user to select a kernel."""

    title = "Select Kernel"

    def load(
        self,
        kernel_specs: "Optional[dict[str, Any]]" = None,
        tab: "Optional[KernelTab]" = None,
        message: "str" = "",
    ) -> "None":
        """Load dialog body & buttons."""
        kernel_specs = kernel_specs or {}

        options = Select(
            options=list(kernel_specs.keys()),
            labels=[
                kernel_spec.get("spec", {}).get("display_name", kernel_name)
                for kernel_name, kernel_spec in kernel_specs.items()
            ],
            style="class:radio-buttons,input",
            prefix=("○", "◉"),
            multiple=False,
            border=None,
            rows=5,
        )

        msg_ft = (f"{message}\n" if message else "") + "Please select a kernel:\n"

        self.body = HSplit(
            [
                Label(msg_ft),
                FocusedStyle(Box(options, padding_left=0)),
            ]
        )

        def _change_kernel() -> "None":
            assert tab is not None
            name = options.options[options.index or 0]
            tab.kernel.change(name, cb=tab.kernel_started)

        self.buttons = {
            "Select": _change_kernel,
            "Cancel": None,
        }


class MsgBoxDialog(Dialog):
    """A dialog which shows the user a message."""

    title = "Message"

    def load(self, title: "str" = "Message", message: "str" = "") -> "None":
        """Load dialog body & buttons."""
        self.title = title
        self.body = Label(message)


class ConfirmDialog(Dialog):
    """A dialog which allows the user to confirm an action."""

    title = "Are you sure?"

    def load(
        self,
        message: "str" = "Please confirm",
        cb: "Optional[Callable[[], None]]" = None,
    ) -> "None":
        """Load dialog body & buttons."""
        self.body = Label(message)

        def _callback() -> "None":
            if callable(cb):
                cb()

        self.buttons = {
            "Yes": _callback,
            "No": None,
        }


class ErrorDialog(Dialog):
    """A dialog to show unhandled exceptions."""

    title = "Error"

    def load(self, exception: "Optional[Exception]" = None, when: "str" = "") -> "None":
        """Load dialog body & buttons."""
        from euporie.core.widgets.formatted_text_area import FormattedTextArea
        from euporie.core.widgets.forms import Checkbox

        if exception is None:
            exception = Exception("Unspecified Error")

        checkbox = Checkbox(
            text="Show traceback",
            prefix=("⮞", "⮟"),
        )

        tb_text = "".join(
            traceback.format_exception(None, exception, exception.__traceback__)
        )

        self.body = HSplit(
            [
                Window(
                    FormattedTextControl(
                        [
                            ("bold", "An error occurred"),
                            ("bold", f" when {when}" if when else ""),
                            ("bold", ":"),
                            ("", "\n\n"),
                            ("fg:ansired", exception.__repr__()),
                            ("", "\n"),
                        ]
                    )
                ),
                FocusedStyle(
                    Box(checkbox, padding_left=0),
                ),
                ConditionalContainer(
                    FormattedTextArea(
                        lex([("", tb_text)], "pytb"),
                        width=80,
                        height=Dimension(min=10),
                        wrap_lines=False,
                        style="",
                    ),
                    filter=Condition(lambda: checkbox.selected),
                ),
            ]
        )

        def _copy_traceback() -> "None":
            self.app.clipboard.set_data(ClipboardData(tb_text))

        self.buttons = {"Close": None, "Copy Traceback": _copy_traceback}


class UnsavedDialog(Dialog):
    """A dialog prompting the user to save unsaved changes."""

    title = "Unsaved Changes"

    def load(
        self, tab: "Optional[Tab]" = None, cb: "Optional[Callable[[], None]]" = None
    ) -> "None":
        """Load the dialog body."""
        tab = tab or self.app.tab
        assert tab is not None

        self.body = Window(
            FormattedTextControl(
                [
                    ("bold", tab.path.name if tab.path else tab.__class__.__name__),
                    ("", " has unsaved changes\n"),
                    ("", "Do you want to save your changes?"),
                ]
            ),
        )

        def yes_cb() -> "None":
            assert tab is not None
            tab.save()
            tab.close(cb)

        def no_cb() -> "None":
            assert tab is not None
            Tab.close(tab, cb)

        self.buttons = {
            "Yes": yes_cb,
            "No": no_cb,
            "Cancel": None,
        }


class ShortcutsDialog(Dialog):
    """Displays details of registered key-bindings in a dialog."""

    title = "Keyboard Shortcuts"

    def __init__(self, app: "BaseApp") -> None:
        """Create a new shortcuts dialog instance."""
        super().__init__(app)
        self.details: "Optional[StyleAndTextTuples]" = None

    def load(self, *args: "Any", **kwargs: "Any") -> "None":
        """Load the dialog body."""
        from euporie.core.formatted_text.utils import max_line_width
        from euporie.core.widgets.formatted_text_area import FormattedTextArea

        if not self.details:
            self.details = self.format_key_info()
        assert self.details is not None

        width = max_line_width(self.details) + 1

        self.body = FormattedTextArea(
            formatted_text=self.details,
            multiline=True,
            focusable=True,
            wrap_lines=False,
            width=width,
        )

    def format_key_info(self) -> "StyleAndTextTuples":
        """Generate a table with the current key bindings."""
        import importlib
        from textwrap import dedent

        from prompt_toolkit.formatted_text.base import to_formatted_text

        from euporie.core.border import Invisible, Padding
        from euporie.core.commands import get_cmd
        from euporie.core.formatted_text.table import Table
        from euporie.core.formatted_text.utils import FormattedTextAlign
        from euporie.core.key_binding.registry import BINDINGS
        from euporie.core.key_binding.utils import format_keys, parse_keys

        table = Table(padding=0, border=Invisible, border_collapse=True)

        for group, bindings in BINDINGS.items():
            log.info(group)
            if bindings:
                mod_name, cls_name = group.rsplit(".", maxsplit=1)
                mod = importlib.import_module(mod_name)
                app_cls = getattr(mod, cls_name)
                section_title = (
                    dedent(app_cls.__doc__).strip().split("\n")[0].rstrip(".")
                )

                row = table.new_row()
                row.new_cell(
                    section_title,
                    align=FormattedTextAlign.CENTER,
                    col_span=2,
                    style="class:shortcuts.group",
                )
                row.new_cell("")
                for i, (cmd_name, keys) in enumerate(bindings.items()):
                    cmd = get_cmd(cmd_name)
                    if not cmd.hidden():
                        key_strs = format_keys(parse_keys(keys))
                        row = table.new_row(
                            style="class:shortcuts.row" + (",alt" if i % 2 else "")
                        )
                        row.new_cell(
                            "\n".join(key_strs),
                            align=FormattedTextAlign.RIGHT,
                            style="class:key",
                        )
                        row.new_cell(cmd.title)
        table.padding = Padding(0, 1, 0, 1)

        return to_formatted_text(table)

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd()
    def _keyboard_shortcuts() -> "None":
        """Displays details of registered key-bindings in a dialog."""
        from euporie.core.app import get_app

        if dialog := get_app().dialogs.get("shortcuts"):
            dialog.toggle()
