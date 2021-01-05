# -*- coding: utf-8 -*-
import logging

from prompt_toolkit.application import get_app

from euporie.commands.command import add
from euporie.filters import tab_has_focus

log = logging.getLogger(__name__)


@add(
    keys="c-n",
    group="File",
    description="Create a new file",
    menu=True,
)
def new_file() -> "None":
    get_app().ask_new_file()


@add(
    keys="c-o",
    group="File",
    description="Open a file",
    menu=True,
)
def open_file() -> "None":
    get_app().ask_open_file()


@add(
    keys="c-w",
    filter=tab_has_focus,
    group="File",
    description="Close the current file",
    menu=True,
)
def close_file() -> None:
    get_app().close_tab()


@add(
    keys="c-q",
    name="quit",
    group="File",
    description="Quit euporie",
    menu=True,
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
