"""A text base user interface for euporie."""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app as ptk_get_app
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.filters import Condition, buffer_has_focus
from prompt_toolkit.formatted_text import HTML, fragment_list_to_text
from prompt_toolkit.key_binding.key_bindings import KeyBindings, merge_key_bindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
    to_container,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.widgets import Dialog, Label

from euporie.core import (
    __app_name__,
    __copyright__,
    __logo__,
    __strapline__,
    __version__,
)
from euporie.core.app import BaseApp
from euporie.core.commands import add_cmd, get_cmd
from euporie.core.config import CONFIG_PARAMS, config
from euporie.core.filters import have_black, have_isort, have_ssort
from euporie.core.key_binding.registry import register_bindings
from euporie.core.tabs.log import LogView
from euporie.core.tabs.notebook import EditNotebook
from euporie.core.utils import parse_path
from euporie.core.widgets.decor import FocusedStyle, Pattern
from euporie.core.widgets.formatted_text_area import FormattedTextArea
from euporie.core.widgets.inputs import Button, Text
from euporie.core.widgets.layout import TabBarControl, TabBarTab
from euporie.core.widgets.menu import MenuContainer, MenuItem
from euporie.core.widgets.pager import Pager
from euporie.core.widgets.palette import CommandPalette
from euporie.core.widgets.search_bar import SearchBar
from euporie.core.widgets.status_bar import StatusBar
from euporie.notebook.enums import TabMode

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from os import PathLike
    from typing import Any, Callable, Dict, Generator, List, Optional, Type

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.completion import Completer
    from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.tabs.base import Tab
    from euporie.core.widgets.cell import InteractiveCell

log = logging.getLogger(__name__)


def get_app() -> "NotebookApp":
    """Get the current application."""
    return cast("NotebookApp", ptk_get_app())


class NotebookApp(BaseApp):
    """Interactively edit a notebook file.

    Launches the interactive TUI notebook editor, allowing you to run and edit Jupyter
    notebooks in the terminal.
    """

    status_default = (
        [HTML("Press <b>Ctrl+n</b> to start a new notebook")],
        [HTML("Press <b>Ctrl+q</b> to quit")],
    )

    def __init__(self, **kwargs: "Any") -> "None":
        """Create a new euporie text user interface application instance."""
        super().__init__(
            **{
                **{
                    "full_screen": True,
                    "erase_when_done": True,
                    "mouse_support": True,
                },
                **kwargs,
            }
        )
        self.bindings_to_load.append("app.notebook")
        self.has_dialog = False

    def get_file_tab(self, path: "PathLike") -> "Type[Tab]":
        """Returns the tab to use for a file path."""
        return EditNotebook

    async def _poll_terminal_colors(self) -> "None":
        """Repeatedly query the terminal for its background and foreground colours."""
        while config.terminal_polling_interval:
            await asyncio.sleep(config.terminal_polling_interval)
            self.term_info.colors.send()

    def post_load(self) -> "None":
        """Continues loading the app."""
        super().post_load()
        # Ensure an opened tab is focused
        if self.tab:
            self.tab.focus()

        # Load style hooks and start polling terminal style
        if self.using_vt100:
            self.create_background_task(self._poll_terminal_colors())

    def format_title(self) -> "StyleAndTextTuples":
        """Formats the tab's title for display in the top right of the app."""
        if self.tab:
            return [("bold class:status.field", f" {self.tab.title} ")]
        else:
            return []

    def tab_container(self) -> "AnyContainer":
        """Returns a container with all opened tabs.

        Returns:
            A vertical split containing the opened tab containers.

        """
        if self.tabs:
            if TabMode(config.tab_mode) == TabMode.TILE_HORIZONTALLY:
                return HSplit(
                    children=self.tabs,
                    padding=1,
                    padding_style="class:tab-padding",
                    padding_char="─",
                )
            elif TabMode(config.tab_mode) == TabMode.TILE_VERTICALLY:
                return VSplit(
                    children=self.tabs,
                    padding=1,
                    padding_style="class:tab-padding",
                    padding_char="│",
                )
            else:
                return DynamicContainer(lambda: self.tabs[self._tab_idx])
        else:
            return Pattern(config.background_character)

    def load_container(self) -> "FloatContainer":
        """Builds the main application layout."""
        have_tabs = Condition(lambda: bool(self.tabs))

        self.logo = Window(
            FormattedTextControl(
                [("", f" {__logo__} ")],
                focusable=~have_tabs,
                show_cursor=False,
                style="class:menu-bar,logo",
            ),
            height=1,
            dont_extend_width=True,
        )

        self.title_bar = ConditionalContainer(
            Window(
                content=FormattedTextControl(self.format_title, show_cursor=False),
                height=1,
                style="class:menu.item",
                dont_extend_width=True,
                align=WindowAlign.RIGHT,
            ),
            filter=have_tabs,
        )

        self.search_bar = SearchBar()

        self.tab_bar_control = TabBarControl(
            tabs=self.tab_bar_tabs,
            active=lambda: self._tab_idx,
            closeable=True,
        )
        tab_bar = ConditionalContainer(
            Window(
                self.tab_bar_control,
                height=2,
                style="class:app-tab-bar",
            ),
            filter=Condition(
                lambda: (len(self.tabs) > 1 or config.always_show_tab_bar)
                and TabMode(config.tab_mode) == TabMode.STACK
            ),
        )

        self.pager = Pager()

        body = HSplit(
            [
                tab_bar,
                DynamicContainer(self.tab_container),
                self.pager,
                self.search_bar,
                StatusBar(),
            ],
            style="class:body",
        )

        self.command_palette = CommandPalette()

        self.dialogs.extend(
            [
                Float(self.command_palette, top=4),
                Float(
                    content=CompletionsMenu(
                        max_height=16,
                        scroll_offset=1,
                        extra_filter=~self.command_palette.visible,
                    ),
                    xcursor=True,
                    ycursor=True,
                ),
            ]
        )

        self.menu_container = MenuContainer(
            body=body,
            menu_items=self.load_menu_items(),  # type: ignore
            floats=self.floats,
            left=[self.logo],
            right=[self.title_bar],
        )

        return cast("FloatContainer", to_container(self.menu_container))

    def tab_bar_tabs(self) -> "List[TabBarTab]":
        """Return a list of the current tabs for the tab-bar."""
        return [
            TabBarTab(
                title=partial(lambda x: x.title, tab),
                on_activate=partial(setattr, self, "tab_idx", i),
                on_close=partial(self.close_tab, tab),
            )
            for i, tab in enumerate(self.tabs)
        ]

    def dialog(
        self,
        title: "AnyFormattedText",
        body: "AnyContainer",
        buttons: "Dict[str, Optional[Callable]]",
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
        # Only show one dialog at a time
        if self.has_dialog:
            return

        focused = self.layout.current_control

        def _make_handler(cb: "Optional[Callable]" = None) -> "Callable":
            def inner(event: "Optional[KeyPressEvent]" = None) -> "None":
                self.dialogs.remove(dialog_float)
                self.has_dialog = False
                if focused in self.layout.find_all_controls():
                    try:
                        self.layout.focus(focused)
                    except ValueError:
                        pass
                if callable(cb):
                    cb()

            return inner

        kb = KeyBindings()
        kb.add("escape")(lambda event: _make_handler()())
        button_widgets = []

        width = max(map(len, buttons)) + 2
        for text, cb in buttons.items():
            handler = _make_handler(cb)
            button_widgets.append(
                FocusedStyle(
                    Button(text, on_click=handler, width=width, style="class:input")
                )
            )
            kb.add(text[:1].lower(), filter=~buffer_has_focus)(handler)
        # TODO - replace dialog with own widget
        dialog = Dialog(
            title=title,
            body=body,
            buttons=button_widgets,  # type: ignore [arg-type]
            modal=True,
            with_background=False,
        )
        # Add extra key-bindings
        dialog_innards = dialog.container.container
        if (
            isinstance(dialog_innards, FloatContainer)
            and isinstance(dialog_innards.content, HSplit)
            and dialog_innards.content.key_bindings is not None
        ):
            dialog_innards.content.key_bindings = merge_key_bindings(
                [dialog_innards.content.key_bindings, kb]
            )
        dialog_float = Float(content=dialog)
        # Add to top of the float stack
        self.dialogs.insert(0, dialog_float)
        self.has_dialog = True

        if to_focus is None:
            to_focus = button_widgets[0]
        self.layout.focus(to_focus)

        self.invalidate()

    def ask_file(
        self,
        callback: "Callable[[Buffer, bool, Optional[Completer]], None]",
        default: "str" = "",
        validate: "bool" = True,
        error: "Optional[str]" = None,
        completer: "Optional[Completer]" = None,
        title: "str" = "Select file",
    ) -> None:
        """Display a dialog asking for file name input.

        Args:
            callback: The callback to run when the filepath is accepted
            default: The default filename to display in the text entry box
            validate: Whether to disallow files which do not exist
            error: An optional error message to display below the file name
            completer: The completer to use for the input field
            title: The dialog title

        """

        def _accept_text(buf: "Buffer") -> "bool":
            """Accepts the text in the file input field and focuses the next field."""
            self.layout.focus_next()
            buf.complete_state = None
            return True

        filepath = Text(
            text=default,
            multiline=False,
            completer=completer,
            accept_handler=_accept_text,
            style="class:input",
            width=40,
        )

        root_contents: "list[AnyContainer]" = [
            Label("Enter file path:"),
            FocusedStyle(filepath),
        ]
        if error:
            root_contents.append(Label(error, style="red"))
        self.dialog(
            title=title,
            body=HSplit(root_contents),
            buttons={
                "OK": partial(callback, filepath.buffer, validate, completer),
                "Cancel": None,
            },
            to_focus=filepath,
        )

    def _open_file_cb(
        self,
        buffer: "Buffer",
        validate: "bool",
        completer: "Optional[Completer]" = None,
    ) -> "None":
        """Open a file from the "open" or "new" dialogs."""
        path = parse_path(buffer.text)
        if path is not None and (not validate or path.exists()):
            self.open_file(path)
        else:
            self.ask_file(
                callback=self._open_file_cb,
                default=buffer.text,
                validate=validate,
                error="File not found",
                completer=completer,
                title="Open File",
            )

    def ask_new_file(self) -> "None":
        """Prompts the user to name a file."""
        return self.ask_file(
            callback=self._open_file_cb,
            validate=False,
            completer=PathCompleter(),
            title="New File",
        )

    def ask_open_file(self) -> "None":
        """Prompts the user to open a file."""
        self.ask_file(
            callback=self._open_file_cb,
            completer=PathCompleter(),
            title="Open File",
        )

    def _save_as_cb(
        self,
        buffer: "Buffer",
        validate: "bool",
        completer: "Optional[Completer]" = None,
    ) -> "None":
        """Change the notebook's path and save it."""
        if self.notebook:
            self.notebook.path = parse_path(buffer.text)
            self.notebook.save()

    def save_as(self) -> "None":
        """Prompts the user to save the notebook under a new path."""
        self.ask_file(
            callback=self._save_as_cb,
            completer=PathCompleter(),
            title="Save As",
        )

    @staticmethod
    def _kb_info() -> "Generator":
        from euporie.core.formatted_text.commands import format_command_attrs

        data = format_command_attrs(
            attrs=["title", "keys"],
            groups=[
                "app",
                "config",
                "notebook",
                "cell",
                "completion",
                "suggestion",
                "micro-edit-mode",
            ],
        )
        for group, info in data.items():
            if info:
                total_w = len(info[0]["title"]) + len(info[0]["keys"][0]) + 4
                yield ("class:shortcuts.group", f"{group.center(total_w)}\n")
                for i, rec in enumerate(info):
                    for j, key in enumerate(rec["keys"]):
                        key_str = key.strip().rjust(len(key))
                        title_str = rec["title"] if j == 0 else " " * len(rec["title"])
                        style = "class:shortcuts.row" + (" class:alt" if i % 2 else "")
                        yield (style + " class:key", f" {key_str} ")
                        yield (style, f" {title_str} \n")

    def help_keys(self) -> None:
        """Displays details of registered key-bindings in a dialog."""
        key_details = list(self._kb_info())
        max_line_width = max(
            [len(line) for line in fragment_list_to_text(key_details).split("\n")]
        )
        body = FormattedTextArea(
            formatted_text=key_details,
            multiline=True,
            focusable=True,
            wrap_lines=False,
            width=Dimension(preferred=max_line_width + 1),
            scrollbar=True,
        )

        self.dialog(
            title="Keyboard Shortcuts",
            body=body,
            buttons={"OK": None},
        )

    def help_logs(self) -> None:
        """Displays a dialog with logs."""
        for tab in self.tabs:
            if isinstance(tab, LogView):
                break
        else:
            tab = LogView()
            self.tabs.append(tab)
        tab.focus()

    def help_about(self) -> None:
        """Displays an about dialog."""
        self.dialog(
            title="About",
            body=Window(
                FormattedTextControl(
                    [
                        ("class:logo", __logo__),
                        ("", " "),
                        ("bold", __app_name__),
                        ("", f"Version {__version__}\n\n".rjust(27, " ")),
                        ("", __strapline__),
                        ("", "\n"),
                        ("class:hr", "─" * 34 + "\n\n"),
                        ("", __copyright__),
                        ("", "\n"),
                    ]
                ),
                dont_extend_height=True,
            ),
            buttons={"OK": None},
        )

    def _handle_exception(
        self, loop: "AbstractEventLoop", context: "Dict[str, Any]"
    ) -> "None":
        exception = context.get("exception")
        # Log observed exceptions to the log
        log.exception("An unhandled exception occurred", exc_info=exception)
        # Also display a dialog to the user
        self.dialog(
            title="Error",
            body=Window(
                FormattedTextControl(
                    [
                        ("bold", "An error occurred:\n\n"),
                        ("", exception.__repr__()),
                    ]
                )
            ),
            buttons={"OK": None},
        )

    def exit(self, **kwargs: "Any") -> "None":
        """Check for unsaved files before closing.

        Creates a chain of close file commands, where the callback for each triggers
        the closure of the next. The closing process can be cancelled anywhere along
        the chain.

        Args:
            **kwargs: Unused key word arguments

        """
        really_close = super().exit
        if self.tabs:

            def final_cb() -> "None":
                """Really exit after the last tab in the chain is closed."""
                self.cleanup_closed_tab(self.tabs[0])
                really_close()

            def create_cb(
                close_tab: "Tab", cleanup_tab: "Tab", cb: "Callable"
            ) -> "Callable":
                """Generate a tab close chaining callbacks.

                Cleans up after the previously closed tab, and requests to close the
                next tab in the chain.

                Args:
                    close_tab: The tab to close
                    cleanup_tab: The previously closed tab to cleanup
                    cb: The callback to call when work is complete

                Returns:
                    A callback function which cleans up `cleanup_tab` and closes
                        `close_tab`.

                """

                def inner() -> None:
                    self.cleanup_closed_tab(cleanup_tab)
                    close_tab.close(cb=cb)

                return inner

            cb = final_cb
            for close_tab, cleanup_tab in zip(self.tabs, self.tabs[1:]):
                cb = create_cb(close_tab, cleanup_tab, cb)
            self.tabs[-1].close(cb)
        else:
            really_close()

    @property
    def notebook(self) -> "Optional[EditNotebook]":
        """Return the currently active notebook."""
        if isinstance(self.tab, EditNotebook):
            return self.tab
        return None

    @property
    def cell(self) -> "Optional[InteractiveCell]":
        """Return the currently active cell."""
        if isinstance(self.tab, EditNotebook):
            return self.tab.cell
        return None

    def load_menu_items(self) -> "list[MenuItem]":
        """Loads the list of menu items to display in the menu."""
        separator = MenuItem(separator=True)
        return [
            MenuItem(
                "File",
                children=[
                    get_cmd("new-notebook").menu,
                    get_cmd("open-file").menu,
                    separator,
                    get_cmd("save-notebook").menu,
                    get_cmd("save-as").menu,
                    get_cmd("close-tab").menu,
                    separator,
                    get_cmd("quit").menu,
                ],
            ),
            MenuItem(
                "Edit",
                children=[
                    get_cmd("undelete-cells").menu,
                    separator,
                    get_cmd("cut-cells").menu,
                    get_cmd("copy-cells").menu,
                    get_cmd("paste-cells").menu,
                    separator,
                    get_cmd("copy-outputs").menu,
                    separator,
                    get_cmd("find").menu,
                    separator,
                    get_cmd("reformat-cells").menu,
                    get_cmd("reformat-notebook").menu,
                ],
            ),
            MenuItem(
                "Run",
                children=[
                    get_cmd("run-selected-cells").menu,
                    get_cmd("run-all-cells").menu,
                ],
            ),
            MenuItem(
                "Kernel",
                children=[
                    get_cmd("interrupt-kernel").menu,
                    get_cmd("restart-kernel").menu,
                    get_cmd("change-kernel").menu,
                ],
            ),
            MenuItem(
                "Tabs",
                children=[
                    get_cmd("next-tab").menu,
                    get_cmd("previous-tab").menu,
                    separator,
                    MenuItem(
                        "Tab mode",
                        children=[
                            get_cmd(f"set-tab-mode-{choice}").menu
                            for choice in config.choices("tab_mode")
                        ],
                    ),
                ],
            ),
            MenuItem(
                "Settings",
                children=[
                    MenuItem(
                        "Editor key bindings",
                        children=[
                            get_cmd(f"set-edit-mode-{choice}").menu
                            for choice in config.choices("edit_mode")
                        ],
                    ),
                    separator,
                    MenuItem(
                        "Color scheme",
                        children=[
                            get_cmd(f"set-color-scheme-{choice}").menu
                            for choice in config.choices("color_scheme")
                        ],
                    ),
                    MenuItem(
                        "Syntax theme",
                        children=[
                            get_cmd(f"set-syntax-theme-{choice}").menu
                            for choice in sorted(
                                CONFIG_PARAMS["syntax_theme"]["schema_"]["enum"]
                            )
                        ],
                    ),
                    get_cmd("switch-background-pattern").menu,
                    get_cmd("show-cell-borders").menu,
                    get_cmd("tmux-terminal-graphics").menu,
                    separator,
                    get_cmd("use-full-width").menu,
                    get_cmd("show-line-numbers").menu,
                    get_cmd("show-status-bar").menu,
                    get_cmd("show-scroll-bar").menu,
                    get_cmd("always-show-tab-bar").menu,
                    separator,
                    MenuItem(
                        "Cell formatting",
                        children=[
                            get_cmd("autoformat").menu,
                            separator,
                            get_cmd("format-black").menu,
                            get_cmd("format-isort").menu,
                            get_cmd("format-ssort").menu,
                        ],
                    ),
                    get_cmd("autocomplete").menu,
                    get_cmd("autosuggest").menu,
                    get_cmd("autoinspect").menu,
                    get_cmd("run-after-external-edit").menu,
                ],
            ),
            MenuItem(
                "Help",
                children=[
                    get_cmd("show-command-palette").menu,
                    get_cmd("keyboard-shortcuts").menu,
                    get_cmd("view-documentation").menu,
                    separator,
                    get_cmd("view-logs").menu,
                    separator,
                    get_cmd("about").menu,
                ],
            ),
        ]


# Commands


@add_cmd()
def new_notebook() -> "None":
    """Create a new file."""
    get_app().ask_new_file()


@add_cmd()
def open_file() -> "None":
    """Open a file."""
    get_app().ask_open_file()


@add_cmd()
def keyboard_shortcuts() -> "None":
    """Show the currently bound keyboard shortcuts."""
    get_app().help_keys()


@add_cmd()
def view_logs() -> "None":
    """Open the logs in a new tab."""
    get_app().help_logs()


@add_cmd()
def view_documentation() -> "None":
    """Open the documentation in the browser."""
    import webbrowser

    webbrowser.open("https://euporie.readthedocs.io/")


@add_cmd()
def about() -> "None":
    """Show the about dialog."""
    get_app().help_about()


for choice in config.choices("tab_mode"):
    add_cmd(
        name=f"set-tab-mode-{choice.lower()}",
        title=f'Set tab mode to "{choice.title()}"',
        menu_title=choice.replace("_", " ").capitalize(),
        groups="config",
        description=f"Set the tab mode to '{choice}'.",
        toggled=Condition(
            partial(lambda x: config.tab_mode == x, choice),
        ),
    )(partial(setattr, config, "tab_mode", choice))


@add_cmd(
    filter=~buffer_has_focus,
    groups="config",
)
def switch_background_pattern() -> "None":
    """Switch between different background patterns."""
    config.toggle("background_pattern")


@add_cmd(
    filter=~buffer_has_focus,
    groups="config",
    toggled=Condition(lambda: config.show_cell_borders),
)
def show_cell_borders() -> "None":
    """Toggle the visibility of the borders of unselected cells."""
    config.toggle("show_cell_borders")
    get_app().refresh()


@add_cmd(
    filter=~buffer_has_focus,
    groups="config",
    toggled=Condition(lambda: config.expand),
)
def use_full_width() -> "None":
    """Toggle whether cells should extend across the full width of the screen."""
    config.toggle("expand")


@add_cmd(
    groups="config",
    toggled=Condition(lambda: bool(config.show_scroll_bar)),
)
def show_scroll_bar() -> "None":
    """Toggle the visibility of the scroll bar."""
    config.toggle("show_scroll_bar")


@add_cmd(
    groups="config",
    toggled=Condition(lambda: bool(config.always_show_tab_bar)),
)
def always_show_tab_bar() -> "None":
    """Toggle the visibility of the tab bar."""
    config.toggle("always_show_tab_bar")


@add_cmd(
    filter=~buffer_has_focus,
    groups="config",
    toggled=Condition(lambda: config.line_numbers),
)
def show_line_numbers() -> "None":
    """Toggle the visibility of line numbers."""
    config.toggle("line_numbers")
    get_app().refresh()


@add_cmd(
    title="Autoformat code cells",
    filter=~buffer_has_focus,
    toggled=Condition(lambda: bool(config.autoformat)),
)
def autoformat() -> "None":
    """Toggle whether code cells are formatted before they are run."""
    config.toggle("autoformat")


@add_cmd(
    title="Format code cells using black",
    menu_title="Use black",
    filter=~buffer_has_focus & have_black,
    toggled=Condition(lambda: bool(config.format_black)),
)
def format_black() -> "None":
    """Toggle whether code cells are formatted using black."""
    config.toggle("format_black")


@add_cmd(
    title="Format code cells using isort",
    menu_title="Use isort",
    filter=~buffer_has_focus & have_isort,
    toggled=Condition(lambda: bool(config.format_isort)),
)
def format_isort() -> "None":
    """Toggle whether code cells are formatted using isort."""
    config.toggle("format_isort")


@add_cmd(
    title="Format code cells using ssort",
    menu_title="Use ssort",
    filter=~buffer_has_focus & have_ssort,
    toggled=Condition(lambda: bool(config.format_ssort)),
)
def format_ssort() -> "None":
    """Toggle whether code cells are formatted using ssort."""
    config.toggle("format_ssort")


@add_cmd(
    title="Completions as you type",
    filter=~buffer_has_focus,
    toggled=Condition(lambda: bool(config.autocomplete)),
)
def autocomplete() -> "None":
    """Toggle whether completions should be shown automatically."""
    config.toggle("autocomplete")


@add_cmd(
    title="Suggest lines from history",
    groups="config",
    toggled=Condition(lambda: bool(config.autosuggest)),
)
def autosuggest() -> "None":
    """Toggle whether to suggest line completions from the kernel's history."""
    config.toggle("autosuggest")


@add_cmd(
    title="Automatic contextual help",
    groups="config",
    toggled=Condition(lambda: bool(config.autoinspect)),
)
def autoinspect() -> "None":
    """Toggle whether to automatically show contextual help when navigating code cells."""
    config.toggle("autoinspect")


@add_cmd(
    title="Run cell after external edit",
    groups="config",
    toggled=Condition(lambda: bool(config.run_after_external_edit)),
)
def run_after_external_edit() -> "None":
    """Toggle whether cells should run automatically after editing externally."""
    config.toggle("run_after_external_edit")


register_bindings(
    {
        "app.notebook": {
            "new-notebook": "c-n",
            "open-file": "c-o",
            "use-full-width": "w",
            "show-line-numbers": "l",
        }
    }
)
