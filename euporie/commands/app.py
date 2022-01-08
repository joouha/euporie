# -*- coding: utf-8 -*-
import logging

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition, buffer_has_focus

from euporie.commands.registry import add
from euporie.config import config
from euporie.filters import tab_has_focus

log = logging.getLogger(__name__)


@add(
    keys="c-n",
    group="File",
    description="Create a new file",
)
def new_notebook() -> "None":
    get_app().ask_new_file()


@add(
    keys="c-o",
    group="File",
    description="Open a file",
)
def open_file() -> "None":
    get_app().ask_open_file()


@add(
    keys="c-w",
    filter=tab_has_focus,
    group="File",
    description="Close the current file",
)
def close_file() -> None:
    get_app().close_tab()


@add(
    keys="c-q",
    name="quit",
    group="File",
    description="Quit euporie",
)
def quit() -> "None":
    get_app().exit()


@add(
    keys="c-pageup",
    group="App",
    description="Switch to next tab",
)
def next_tab() -> "None":
    get_app().tab_idx += 1


@add(
    keys="c-pagedown",
    group="App",
    description="Switch to previous tab",
)
def next_tab() -> "None":
    get_app().tab_idx -= 1


@add(
    keys="tab",
    group="App",
    description="Focus next control",
)
def focus_next() -> "None":
    get_app().layout.focus_next()


@add(
    keys="s-tab",
    group="App",
    description="Focus previous control",
)
def focus_previous() -> "None":
    get_app().layout.focus_previous()


@add(
    keys="l",
    filter=~buffer_has_focus,
    group="Config",
    toggled=Condition(lambda: config.line_numbers),
)
def show_line_numbers() -> "None":
    config.toggle("line_numbers")


@add(
    filter=~buffer_has_focus,
    group="Config",
)
def switch_background_pattern() -> "None":
    config.toggle("background_pattern")


@add(
    filter=~buffer_has_focus,
    group="Config",
    toggled=Condition(lambda: config.show_cell_borders),
)
def show_cell_borders() -> "None":
    config.toggle("show_cell_borders")


@add(
    keys="w",
    filter=~buffer_has_focus,
    group="Config",
    toggled=Condition(lambda: config.expand),
)
def use_full_width() -> "None":
    config.toggle("expand")


@add(
    title="Completions as you type",
    filter=~buffer_has_focus,
    toggled=Condition(lambda: bool(config.autocomplete)),
)
def autocomplete() -> "None":
    config.toggle("autocomplete")


@add(
    title="Suggest lines from history",
    group="Config",
    toggled=Condition(lambda: bool(config.autosuggest)),
)
def autosuggest() -> "None":
    config.toggle("autosuggest")


@add(
    title="Run cell after external edit",
    group="Config",
    toggled=Condition(lambda: bool(config.run_after_external_edit)),
)
def run_after_external_edit() -> "None":
    config.toggle("run_after_external_edit")


@add(
    group="Config",
    toggled=Condition(lambda: bool(config.show_status_bar)),
)
def show_status_bar() -> "None":
    config.toggle("show_status_bar")


@add(group="help")
def keyboard_shortcuts():
    get_app().help_keys()


@add(group="help")
def view_logs():
    get_app().help_logs()


@add(group="help")
def about():
    get_app().help_about()
