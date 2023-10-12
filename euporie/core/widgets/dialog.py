"""Dialog."""

from __future__ import annotations

import logging
import traceback
from abc import ABCMeta, abstractmethod
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.clipboard import ClipboardData
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import (
    Condition,
    buffer_has_focus,
    has_completions,
    has_focus,
)
from prompt_toolkit.formatted_text import AnyFormattedText, to_formatted_text
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.key_binding.key_bindings import DynamicKeyBindings, KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    Float,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl, UIContent, UIControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.screen import WritePosition
from prompt_toolkit.mouse_events import MouseButton, MouseEventType
from prompt_toolkit.widgets.base import Box, Label

from euporie.core.app import get_app
from euporie.core.border import (
    FullLine,
    LowerLeftHalfLine,
    UpperRightHalfLine,
)
from euporie.core.commands import add_cmd
from euporie.core.filters import tab_has_focus
from euporie.core.ft.utils import FormattedTextAlign, align, lex
from euporie.core.key_binding.registry import register_bindings
from euporie.core.tabs.base import Tab
from euporie.core.widgets.decor import Border, FocusedStyle, Shadow
from euporie.core.widgets.file_browser import FileBrowser
from euporie.core.widgets.forms import Button, LabelledWidget, Select, Text

if TYPE_CHECKING:
    from typing import Any, Callable, Hashable

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.formatted_text.base import StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.layout import FocusableElement
    from prompt_toolkit.mouse_events import MouseEvent

    from euporie.core.app import BaseApp
    from euporie.core.tabs.base import KernelTab
    from euporie.core.widgets.file_browser import FileBrowserControl

log = logging.getLogger(__name__)


DialogGrid = (
    FullLine.left_edge
    + FullLine.right_edge
    + LowerLeftHalfLine.bottom_edge
    + UpperRightHalfLine.top_edge
)


class DialogTitleControl(UIControl):
    """A draggable dialog titlebar."""

    def __init__(self, title: AnyFormattedText, dialog: Dialog, window: Window) -> None:
        """Initialize a new dialog titlebar."""
        self.title = title
        self.dialog = dialog
        self.window = window
        self.drag_start: Point | None = None
        self._content_cache: SimpleCache[Hashable, UIContent] = SimpleCache(maxsize=18)

    def create_content(self, width: int, height: int | None) -> UIContent:
        """Create the title text content."""

        def get_content() -> UIContent:
            lines = list(
                split_lines(
                    align(
                        to_formatted_text(self.title), FormattedTextAlign.CENTER, width
                    )
                )
            )
            return UIContent(
                get_line=lambda i: lines[i],
                line_count=len(lines),
                show_cursor=False,
            )

        return self._content_cache.get((width,), get_content)

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Move the dialog when the titlebar is dragged."""
        if (info := self.window.render_info) is not None:
            # Get the global mouse position
            app = self.dialog.app
            gx, gy = app.mouse_position
            if mouse_event.button == MouseButton.LEFT:
                if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                    # Start the drag event
                    self.drag_start = mouse_event.position
                    # Send all mouse events to this position
                    y_min, x_min = min(info._rowcol_to_yx.values())
                    y_max, x_max = max(info._rowcol_to_yx.values())
                    app.mouse_limits = WritePosition(
                        xpos=x_min,
                        ypos=y_min,
                        width=x_max - x_min,
                        height=y_max - y_min,
                    )
                    return NotImplemented
                elif mouse_event.event_type == MouseEventType.MOUSE_MOVE:
                    if self.drag_start is not None:
                        # Get available space
                        max_y, max_x = app.output.get_size()
                        # Calculate dialog dimensions
                        dl_width = self.dialog.content.preferred_width(max_x).preferred
                        dl_height = self.dialog.content.preferred_height(
                            dl_width, max_y
                        ).preferred
                        # Calculate new dialog position
                        new_x = max(1, min(gx - self.drag_start.x, max_x - dl_width))
                        new_y = max(1, min(gy - self.drag_start.y, max_y - dl_height))
                        # Move dialog
                        self.dialog.left = new_x - 1
                        self.dialog.top = new_y - 1
                        # change the mouse capture position
                        if app.mouse_limits is not None:
                            app.mouse_limits.xpos = new_x
                            app.mouse_limits.ypos = new_y
                        return None

            # End the drag event
            self.drag_start = None
            # Stop capturing all mouse events
            app.mouse_limits = None
        return NotImplemented


class Dialog(Float, metaclass=ABCMeta):
    """A modal dialog which is displayed above the application.

    Returns focus to the previously selected control when closed.
    """

    title: AnyFormattedText | None = None
    body_padding_top = 1
    body_padding_bottom = 0

    def __init__(self, app: BaseApp) -> None:
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
        self.to_focus: FocusableElement | None = None
        self.last_focused: FocusableElement | None = None
        self._visible = False
        self.visible = Condition(lambda: self._visible)

        # Set default body & buttons
        self.body: AnyContainer = Window()
        self.buttons: dict[str, Callable | None] = {"OK": None}
        self.button_widgets: list[AnyContainer] = []

        # Create key-bindings
        kb = KeyBindings()
        kb.add("escape")(lambda event: self.hide())
        kb.add("tab", filter=~has_completions)(focus_next)
        kb.add("s-tab", filter=~has_completions)(focus_previous)

        @kb.add("enter", filter=~has_completions & ~buffer_has_focus)
        def _focus_button(event: KeyPressEvent) -> NotImplementedOrNone:
            if self.button_widgets:
                app.layout.focus(self.button_widgets[0])
                return None
            return NotImplemented

        self.kb = kb
        self.buttons_kb = KeyBindings()

        # Create title row
        title_window = Window(height=1, style="class:dialog,dialog-title")
        title_window.content = DialogTitleControl(
            lambda: self.title, self, title_window
        )
        title_row = ConditionalContainer(
            title_window, filter=Condition(lambda: bool(self.title))
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
                        self.button_widgets,
                        padding=1,
                        key_bindings=DynamicKeyBindings(lambda: self.buttons_kb),
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
                        modal=False,
                    ),
                    border=DialogGrid,
                    style="class:dialog,border",
                ),
            ),
            filter=self.visible,
        )

        # Set the body as the float's contents
        super().__init__(content=self.container)

    def _button_handler(
        self, button: str = "", event: KeyPressEvent | None = None
    ) -> None:
        if callable(cb := self.buttons.get(button)):
            cb()
        else:
            self.hide()

    def _load(self, **params: Any) -> None:
        """Load body, create buttons, etc."""
        self.to_focus = None
        self.buttons_kb = KeyBindings()

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
                    self.buttons_kb.add(f"A-{key.lower()}", is_global=True)(handler)

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
    def load(self) -> None:
        """Load the dialog's body etc."""

    def show(self, **params: Any) -> None:
        """Display and focuses the dialog."""
        # Reset position
        self.top = self.left = None
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

    def hide(self, event: KeyPressEvent | None = None) -> None:
        """Hide the dialog."""
        self._visible = False
        if self.last_focused is not None:
            try:
                self.app.layout.focus(self.last_focused)
            except ValueError:
                self.app.layout.focus_next()
        # Stop any drag events
        self.app.mouse_limits = None

    def toggle(self) -> None:
        """Show or hides the dialog."""
        if self._visible:
            self.hide()
        else:
            self.show()

    def __pt_container__(self) -> AnyContainer:
        """Return the container's content."""
        return self.container


class AboutDialog(Dialog):
    """A dialog which shows an "about" message."""

    title = "About"

    def load(self) -> None:
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
    def _about() -> None:
        """Show the about dialog."""
        from euporie.core.current import get_app

        if dialog := get_app().dialogs.get("about"):
            dialog.toggle()


class FileDialog(Dialog, metaclass=ABCMeta):
    """A base dialog to prompt the user for a file path."""

    title = "Select a File"

    def __init__(self, app: BaseApp) -> None:
        """Set up the dialog components on dialog initialization."""
        super().__init__(app)

        def _accept_text(buf: Buffer) -> bool:
            """Accept the text in the file input field and focuses the next field."""
            self.app.layout.focus_next()
            buf.complete_state = None
            return True

        completer = PathCompleter()
        self.filepath = Text(
            multiline=False,
            completer=completer,
            accept_handler=_accept_text,
            style="class:input",
            width=30,
        )
        self.file_browser = FileBrowser(
            height=Dimension(preferred=20),
            show_address_bar=False,
            on_select=lambda path: setattr(self.filepath, "text", path.name),
        )
        completer.get_paths = lambda: [str(self.file_browser.control.dir)]
        self.error = ""

        self.body = HSplit(
            [
                self.file_browser,
                FocusedStyle(LabelledWidget(self.filepath, "File name:")),
                ConditionalContainer(
                    Label(lambda: self.error, style="red"),
                    filter=Condition(lambda: bool(self.error)),
                ),
            ]
        )

    def load(
        self,
        text: str = "",
        tab: Tab | None = None,
        error: str = "",
        cb: Callable | None = None,
    ) -> None:
        """Load the dialog body."""
        self.filepath.text = text
        self.buttons = {
            "OK": partial(self.validate, self.filepath.buffer, tab=tab, cb=cb),
            "Cancel": None,
        }
        self.file_browser.control.on_open._handlers.clear()
        self.file_browser.control.on_open += lambda path: self.validate(
            self.filepath.buffer, tab=tab, cb=cb
        )
        self.file_browser.control.selected = None
        self.error = error
        self.to_focus = self.filepath

    def validate(
        self, buffer: Buffer, tab: Tab | None, cb: Callable | None = None
    ) -> None:
        """Validate the input."""
        self.hide()


class OpenFileDialog(FileDialog):
    """A dialog which prompts the user for a filepath to open."""

    title = "Select a File to Open"

    def __init__(self, app: BaseApp) -> None:
        """Additional body components."""
        from euporie.core.widgets.forms import Dropdown

        super().__init__(app)

        self.tab_dd = tab_dd = Dropdown(options=[])

        def _update_options(fb: FileBrowserControl) -> None:
            tabs = get_app().get_file_tabs(path) if (path := fb.path).is_file() else []
            tab_dd.options = tabs
            tab_dd.labels = [tab.name for tab in tabs]

        self.file_browser.control.on_select += _update_options

        if isinstance(self.body, HSplit):
            self.body.children.append(
                ConditionalContainer(
                    FocusedStyle(LabelledWidget(tab_dd, "Open with:")),
                    filter=Condition(lambda: len(tab_dd.options) > 1),
                )
            )

    def load(
        self,
        text: str = "",
        tab: Tab | None = None,
        error: str = "",
        cb: Callable | None = None,
    ) -> None:
        """Load the dialog body."""
        super().load(text=text, tab=tab, error=error, cb=cb)
        self.tab_dd.options = []
        self.tab_dd.labels = []

    def validate(
        self, buffer: Buffer, tab: Tab | None, cb: Callable | None = None
    ) -> None:
        """Validate the the file to open exists."""
        from upath import UPath

        from euporie.core.path import parse_path

        path = parse_path(self.file_browser.control.dir / buffer.text)
        if path is not None:
            if not path.exists():
                path = UPath(buffer.text)

            if path.exists():
                if path.is_dir():
                    self.file_browser.control.dir = path
                elif path.is_file():
                    self.hide()
                    self.app.open_file(path, tab_class=self.tab_dd.value)
                return
            else:
                self.show(
                    error="The file path specified does not exist", text=buffer.text
                )

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(menu_title="Open File…")
    def _open_file() -> None:
        """Open a file."""
        from euporie.core.current import get_app

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

    def validate(
        self, buffer: Buffer, tab: Tab | None, cb: Callable | None = None
    ) -> None:
        """Validate the the file to open exists."""
        from euporie.core.path import parse_path

        path = parse_path(self.file_browser.control.dir / buffer.text)
        if tab and path is not None:
            if path.is_dir():
                self.file_browser.control.dir = path
            else:
                tab.save(path=path)
                self.hide()
                if callable(cb):
                    cb()

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(
        menu_title="Save As…",
        filter=tab_has_focus,
    )
    def _save_as() -> None:
        """Save the current file at a new location."""
        from euporie.core.current import get_app

        app = get_app()
        if dialog := app.dialogs.get("save-as"):
            dialog.show(tab=app.tab)

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.app.BaseApp": {
                "save-as": ("A-s"),
            }
        }
    )


class NoKernelsDialog(Dialog):
    """Dialog to warn the user that no installed kernels were found."""

    title = "No Kernels Found"

    def load(self) -> None:
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
        kernel_specs: dict[str, Any] | None = None,
        runtime_dirs: dict[str, Path] | None = None,
        tab: KernelTab | None = None,
        message: str = "",
    ) -> None:
        """Load dialog body & buttons."""
        from jupyter_core.paths import jupyter_runtime_dir

        from euporie.core.widgets.layout import TabbedSplit

        kernel_specs = kernel_specs or {}
        runtime_dirs = runtime_dirs or {}

        options_specs = Select(
            options=list(kernel_specs.keys()),
            labels=[
                kernel_spec.get("spec", {}).get("display_name", kernel_name)
                for kernel_name, kernel_spec in kernel_specs.items()
            ],
            style="class:input,radio-buttons",
            prefix=("○", "◉"),
            multiple=False,
            border=None,
            rows=5,
            dont_extend_width=False,
        )
        self.to_focus = options_specs

        connection_files = {
            path.name: path
            for path in Path(jupyter_runtime_dir()).glob("kernel-*.json")
        }
        options_files = Select(
            options=list(connection_files.values()),
            labels=list(connection_files.keys()),
            style="class:input,radio-buttons",
            prefix=("○", "◉"),
            multiple=False,
            border=None,
            rows=5,
            dont_extend_width=False,
        )

        msg_ft = (f"{message}\n\n" if message else "") + "Please select a kernel:"

        self.body = HSplit(
            [
                Label(msg_ft),
                tabs := TabbedSplit(
                    [
                        FocusedStyle(options_specs),
                        FocusedStyle(options_files),
                    ],
                    titles=["New", "Existing"],
                    width=Dimension(min=30),
                ),
            ]
        )

        def _change_kernel() -> None:
            self.hide()
            assert tab is not None
            if tabs.active == 0:
                name = options_specs.value
                connection_file = None
            else:
                name = None
                connection_file = options_files.value
            tab.kernel.change(
                name=name, connection_file=connection_file, cb=tab.kernel_started
            )

        self.buttons = {
            "Select": _change_kernel,
            "Cancel": None,
        }


class MsgBoxDialog(Dialog):
    """A dialog which shows the user a message."""

    title = "Message"

    def load(self, title: str = "Message", message: str = "") -> None:
        """Load dialog body & buttons."""
        self.title = title
        self.body = Label(message)


class ConfirmDialog(Dialog):
    """A dialog which allows the user to confirm an action."""

    def load(
        self,
        title: str = "Are you sure?",
        message: str = "Please confirm",
        cb: Callable[[], None] | None = None,
    ) -> None:
        """Load dialog body & buttons."""
        self.title = title
        self.body = Label(message)

        def _callback() -> None:
            if callable(cb):
                cb()
            self.hide()

        self.buttons = {
            "Yes": _callback,
            "No": None,
        }


class ErrorDialog(Dialog):
    """A dialog to show unhandled exceptions."""

    title = "Error"

    def load(self, exception: Exception | None = None, when: str = "") -> None:
        """Load dialog body & buttons."""
        from euporie.core.margins import MarginContainer, ScrollbarMargin
        from euporie.core.widgets.formatted_text_area import FormattedTextArea
        from euporie.core.widgets.forms import Checkbox

        if exception is None:
            exception = Exception("Unspecified Error")

        checkbox = Checkbox(
            text="Show traceback",
            prefix=("▶", "▼"),
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
                        ],
                    )
                ),
                FocusedStyle(
                    Box(checkbox, padding_left=0),
                ),
                ConditionalContainer(
                    VSplit(
                        [
                            fta := FormattedTextArea(
                                lex([("", tb_text)], "pytb"),
                                width=80,
                                height=Dimension(min=10),
                                wrap_lines=False,
                                style="",
                                focus_on_click=True,
                            ),
                            MarginContainer(ScrollbarMargin(), target=fta.window),
                        ]
                    ),
                    filter=Condition(lambda: checkbox.selected),
                ),
            ]
        )

        def _copy_traceback() -> None:
            self.app.clipboard.set_data(ClipboardData(tb_text))

        self.buttons = {"Close": None, "Copy Traceback": _copy_traceback}


class UnsavedDialog(Dialog):
    """A dialog prompting the user to save unsaved changes."""

    title = "Unsaved Changes"

    def load(
        self, tab: Tab | None = None, cb: Callable[[], None] | None = None
    ) -> None:
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

        def yes_cb() -> None:
            assert tab is not None
            self.hide()
            tab.save(cb=partial(tab.close, cb))

        def no_cb() -> None:
            assert tab is not None
            self.hide()
            Tab.close(tab, cb)

        self.buttons = {
            "Yes": yes_cb,
            "No": no_cb,
            "Cancel": None,
        }


class ShortcutsDialog(Dialog):
    """Display details of registered key-bindings in a dialog."""

    title = "Keyboard Shortcuts"

    def __init__(self, app: BaseApp) -> None:
        """Create a new shortcuts dialog instance."""
        super().__init__(app)
        self.details: StyleAndTextTuples | None = None

    def load(self, *args: Any, **kwargs: Any) -> None:
        """Load the dialog body."""
        from euporie.core.ft.utils import max_line_width
        from euporie.core.margins import MarginContainer, ScrollbarMargin
        from euporie.core.widgets.formatted_text_area import FormattedTextArea

        if not self.details:
            self.details = self.format_key_info()
        assert self.details is not None

        width = max_line_width(self.details)

        fta = FormattedTextArea(
            formatted_text=self.details,
            multiline=True,
            focusable=True,
            wrap_lines=False,
            width=width - 2,
        )
        self.body = VSplit([fta, MarginContainer(ScrollbarMargin(), target=fta.window)])

    def format_key_info(self) -> StyleAndTextTuples:
        """Generate a table with the current key bindings."""
        import importlib
        from textwrap import dedent

        from prompt_toolkit.formatted_text.base import to_formatted_text

        from euporie.core.border import InvisibleLine
        from euporie.core.commands import get_cmd
        from euporie.core.data_structures import DiInt
        from euporie.core.ft.table import Table
        from euporie.core.ft.utils import FormattedTextAlign
        from euporie.core.key_binding.registry import BINDINGS
        from euporie.core.key_binding.utils import format_keys, parse_keys

        table = Table(padding=0)

        for group, bindings in BINDINGS.items():
            if any(not get_cmd(cmd_name).hidden() for cmd_name in bindings):
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
                    colspan=2,
                    style="class:shortcuts.group",
                    border_visibility=True,
                    border_line=InvisibleLine,
                )
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
                            border_visibility=False,
                            border_line=InvisibleLine,
                        )
                        row.new_cell(
                            cmd.title,
                            border_visibility=False,
                            border_line=InvisibleLine,
                        )
        table.padding = DiInt(0, 1, 0, 1)

        return to_formatted_text(table)

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd()
    def _keyboard_shortcuts() -> None:
        """Display details of registered key-bindings in a dialog."""
        from euporie.core.current import get_app

        if dialog := get_app().dialogs.get("shortcuts"):
            dialog.toggle()
