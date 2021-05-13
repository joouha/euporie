# -*- coding: utf-8 -*-
import logging
import sys
from functools import partial
from pathlib import Path

from prompt_toolkit.application import Application
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition, Filter
from prompt_toolkit.formatted_text import fragment_list_to_text
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.layout import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
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
from pygments.styles import get_all_styles, get_style_by_name

from euporie import logo
from euporie.config import config
from euporie.keys import KeyBindingsInfo
from euporie.notebook import Notebook
from euporie.term import TermAppMixin
from euporie.text import FormatTextProcessor

log = logging.getLogger(__name__)


class App(Application, TermAppMixin):
    def __init__(self, *args, **kwargs):

        self.open_paths = []
        self.files = []
        self.last_selected_index: int = 0

        self.include_default_pygments_style = False

        self.ttimeoutlen = 0.1

        self.file_open = Condition(lambda: self.files)

        self.key_binding_details = []

        super().__init__(
            layout=self.layout(),
            enable_page_navigation_bindings=True,
            mouse_support=True,
            key_bindings=self.load_key_bindings(),
            full_screen=True,
            style=None,
            editing_mode=self.get_edit_mode,
            *args,
            **kwargs,
        )

    def set_edit_mode(self, mode):
        config.editing_mode = mode
        self.editing_mode = self.get_edit_mode

    @property
    def get_edit_mode(self):
        return {"emacs": EditingMode.EMACS, "vi": EditingMode.VI}.get(
            config.editing_mode, EditingMode.EMACS
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

    def update_style(self, pygments_style):
        config.pygments_style = pygments_style
        self.renderer.style = self._create_merged_style()

    def layout(self):

        kernel_status_repr = {
            "starting": "◍",
            "idle": "○",
            "busy": "●",
            "error": "☹",
        }

        def get_statusbar_text():
            kernel_status = kernel_status_repr.get(self.file.kernel_status, "◌")
            selected_cell = self.file.page.selected_index + 1
            dirt = "*" if self.file.dirty else ""
            return [
                ("class:menu-bar.item", f" Cell {selected_cell} "),
                ("", " "),
                ("class:menu-bar.item bold", f" {dirt}{self.file.path.name} "),
                ("", " "),
                ("class:menu-bar.item", f" {self.file.kernel_name} {kernel_status} "),
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
                        MenuItem("Save", handler=lambda: self.file.save()),
                        MenuItem("Close", handler=self.close_file),
                        MenuItem("-", disabled=True),
                        MenuItem("Exit", handler=self.try_to_exit),
                    ],
                ),
                MenuItem(
                    " Edit ",
                    children=[
                        MenuItem("Cut", handler=lambda: self.file.cut()),
                        MenuItem("Copy", handler=lambda: self.file.copy()),
                        MenuItem("Paste", handler=lambda: self.file.paste()),
                    ],
                ),
                MenuItem(
                    " Kernel ",
                    children=[
                        MenuItem(
                            "Restart Kernel", handler=lambda: self.file.restart_kernel()
                        ),
                        MenuItem(
                            "Change Kernel...",
                            handler=lambda: self.file.change_kernel(),
                        ),
                    ],
                ),
                MenuItem(
                    " Settings ",
                    children=[
                        MenuItem(
                            "Syntax Theme",
                            children=[
                                MenuItem(
                                    style, handler=partial(self.update_style, style)
                                )
                                for style in sorted(get_all_styles())
                            ],
                        ),
                        MenuItem(
                            "Editing Key Bindings",
                            children=[
                                MenuItem(
                                    "Emacs", handler=lambda: self.set_edit_mode("emacs")
                                ),
                                MenuItem(
                                    "Vi", handler=lambda: self.set_edit_mode("vi")
                                ),
                            ],
                        ),
                        MenuItem(
                            "Toggle Background",
                            handler=lambda: config.toggle("background"),
                        ),
                    ],
                ),
                MenuItem(
                    " Help ",
                    children=[
                        MenuItem("Keyboard Shortcuts", handler=self.help_keys),
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

        # Focus status_bar_text so notebook is selected on tab
        return Layout(self.root_container, focused_element=status_bar_text)

    def register_key_binding(self, kb, scope, desc, *keys, **kwargs):
        self.key_binding_details.append((scope, desc, keys))
        return kb.add(*keys, **kwargs)

    def load_key_bindings(self):
        kb = KeyBindingsInfo()

        in_edit_mode = Condition(
            lambda: self.file and self.file.cell and self.file.cell.is_editing()
        )

        @kb.add("c-n", group="Application", desc="Create a new notebook file")
        def new(event):
            self.ask_open_file(validate=False)

        @kb.add("c-o", group="Application", desc="Open file")
        def open(event):
            self.ask_open_file()

        @kb.add("c-w", group="Application", desc="Close the current file")
        def close(event):
            self.close_file(self.file)

        @kb.add("c-q", group="Application", desc="Quit euporie")
        def exit(event):
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
    def selected_index(self):
        # Detect if focused file has changed
        # Find index of selected child
        for i, file in enumerate(self.files):
            if self.layout.has_focus(file):
                break
        else:
            i = self.last_selected_index
        # This will perform change the position when the new child is selected
        self.last_selected_index = i
        return self.last_selected_index

    @selected_index.setter
    def selected_index(self, new_index):
        # Only update the selected file if it was not selected before
        if new_index != self.last_selected_index:
            # Ensure selected index is a valid child
            new_index = min(max(new_index, 0), len(self.files) - 1)
            self.select_notebook(new_index)

            # Focus new child if not already focused
            child = self.get_child(new_index)
            if not self.layout.has_focus(child):
                self.layout.focus(child)

            # Track which child was selected
            self.last_selected_index = new_index

    def try_to_exit(self):
        """
        Check for unsaved files before closing.

        Creates a chain of close file commands, where the callback for each triggers
        the closure of the next. The closing process can be cancelled anywhere along
        the chain.
        """

        if self.files:

            def final_cb():
                """Really exit after the last file in the chain is closed."""
                self.cleanup_closed_file(self.files[0])
                self.exit()

            def create_cb(close_file, cleanup_file, cb):
                """Generate a file close chaining callbacks.

                Cleans up after the previously closed file, and requests to close the
                next file in the chain.
                """

                def inner():
                    self.cleanup_closed_file(cleanup_file)
                    close_file.close(cb=cb)

                return inner

            cb = final_cb
            for close_file, cleanup_file in zip(self.files, self.files[1:]):
                cb = create_cb(close_file, cleanup_file, cb)
            self.files[-1].close(cb)
        else:
            self.exit()

    def ask_open_file(self, default="", validate=True, error=None):
        def open_cb():
            path = filepath.text
            if not validate or Path(path).expanduser().exists():
                self.open_file(filepath.text)
            else:
                self.ask_open_file(
                    default=filepath.text, validate=validate, error="File not found"
                )

        filepath = TextArea(text=default, multiline=False)
        self.dialog(
            title="Select file",
            body=HSplit(
                [
                    Label("Enter file name:"),
                    filepath,
                ]
                + ([Label(error, style="red")] if error else [])
            ),
            buttons={
                "OK": open_cb,
                "Cancel": None,
            },
            to_focus=filepath,
        )

    def open_file(self, path):
        path = Path(path).expanduser()
        log.info(f"Opening file {path}")
        open_paths = [x.path for x in self.files]
        if path in open_paths:
            log.info(f"File {path} already open, activating")
            self.active_notebook = open_paths.index(path)
        else:
            self.open_paths.append(path)
            self.files.append(Notebook(path))
            self.active_notebook_index = len(self.files)

        self.body_container.body.children[0] = VSplit(self.files)

    def close_file(self, file=None):
        if file is None:
            file = self.file
        if file:
            self.file.close(lambda: self.cleanup_closed_file(file))

    def cleanup_closed_file(self, file):
        # Remove file
        self.files.remove(file)
        # Update body container to reflect new file list
        self.body_container.body.children[0] = VSplit(self.files)
        # Focus another file if one exists
        if self.files:
            self.file.page.focus()
        # If a file is not open, the status bar is not shown, so focus the logo, so
        # pressing tab focuses the menu
        else:
            self.layout.focus(self.logo)

    @property
    def file(self):
        if self.files:
            index = min(self.selected_index, len(self.files) - 1)
            return self.files[index]

    def dialog(self, title, body, buttons, to_focus=None):
        def make_handler(cb):
            def inner():
                self.root_container.floats.remove(dialog)
                self.layout.focus(focused)
                if cb:
                    cb()

            return inner

        focused = self.layout.current_control

        button_widgets = [
            Button(text, make_handler(cb), left_symbol="[", right_symbol="]")
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

    def help_keys(self):

        key_details = {
            group: {
                " / ".join(
                    [
                        " ".join(
                            (
                                part.replace("c-", "ctrl-").replace("s-", "shift-")
                                for part in key
                            )
                        )
                        for key in keys
                    ]
                ): desc
                for desc, keys in info.items()
            }
            for group, info in KeyBindingsInfo.details.items()
        }
        max_key_len = (
            max([len(key) for group in key_details.values() for key in group]) + 1
        )

        fragment_list = []
        for group, item in key_details.items():
            fragment_list.append(("", " " * (max(0, max_key_len - len(group)))))
            fragment_list.append(("bold underline", f"{group}\n"))
            for key, desc in item.items():
                fragment_list.append(("bold", key.rjust(max_key_len)))
                fragment_list.append(("", f"  {desc}\n"))
            fragment_list.append(("", "\n"))
        fragment_list.pop()

        plain_text = fragment_list_to_text(fragment_list)
        body = TextArea(
            text=plain_text.strip(),
            multiline=True,
            focusable=True,
            wrap_lines=False,
            input_processors=[FormatTextProcessor()],
            width=max([len(line) for line in plain_text.split("\n")]) + 2,
            scrollbar=True,
        )
        body.control.formatted_text = fragment_list

        self.dialog(
            title="Keyboard Shortcuts",
            body=body,
            buttons={"OK": None},
        )

    def help_about(self):
        self.dialog(
            title="About",
            body=Window(
                FormattedTextControl(
                    [
                        ("class:logo", logo),
                        ("", " "),
                        ("bold", "euporie\n\n"),
                        ("", "A command line editor for Jupyter notebooks\n"),
                        ("class:hr", "─" * 43 + "\n\n"),
                        ("", "Created by Josiah Outram Halstead\n"),
                        ("", "© 2021"),
                    ]
                ),
                dont_extend_height=True,
            ),
            buttons={"OK": None},
        )

    @classmethod
    def launch(cls):
        app = cls()
        for path in sys.argv[1:]:
            app.open_file(path)
        app.run()
