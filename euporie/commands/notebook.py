# -*- coding: utf-8 -*-
import logging

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import buffer_has_focus

from euporie.commands.command import add
from euporie.filters import notebook_has_focus

log = logging.getLogger(__name__)


@add(
    keys="[",
    filter=notebook_has_focus & ~buffer_has_focus,
    group="Notebook",
)
@add(
    keys="<scroll-up>",
    filter=notebook_has_focus,
    group="Notebook",
)
def scroll_up():
    get_app().notebook.page.scroll(1)


@add(
    keys="]",
    filter=notebook_has_focus & ~buffer_has_focus,
    group="Notebook",
)
@add(
    keys="<scroll-down>",
    filter=notebook_has_focus,
    group="Notebook",
)
def scroll_down():
    get_app().notebook.page.scroll(-1)


@add(
    keys="{",
    filter=notebook_has_focus & ~buffer_has_focus,
    group="Notebook",
)
def scroll_up_5_lines():
    get_app().notebook.page.scroll(5)


@add(
    keys="}",
    filter=notebook_has_focus & ~buffer_has_focus,
    group="Notebook",
)
def scroll_down_5_lines():
    get_app().notebook.page.scroll(-5)


@add(
    keys=["home", "c-up"],
    group="Notebook",
    description="Go to first cell",
    filter=notebook_has_focus & ~buffer_has_focus,
)
def first_child() -> None:
    get_app().notebook.page.selected_index = 0


@add(
    keys="pageup",
    group="Notebook",
    description="Go up 5 cells",
    filter=notebook_has_focus & ~buffer_has_focus,
)
def select_5th_previous_cell() -> None:
    get_app().notebook.page.selected_index -= 5


@add(
    keys=["up", "k"],
    group="Notebook",
    description="Go up one cell",
    filter=notebook_has_focus & ~buffer_has_focus,
)
def select_previous_cell() -> None:
    get_app().notebook.page.selected_index -= 1


@add(
    keys=["down", "j"],
    group="Navigation",
    description="Select the next cell",
    filter=notebook_has_focus & ~buffer_has_focus,
)
def next_child() -> "None":
    get_app().notebook.page.selected_index += 1


@add(
    keys="pagedown",
    group="Notebook",
    description="Go down 5 cells",
    filter=~buffer_has_focus,
)
def select_5th_next_cell() -> "None":
    get_app().notebook.page.selected_index += 5


@add(
    keys=["end", "c-down"],
    group="Notebook",
    description="Select the last cell",
    filter=notebook_has_focus & ~buffer_has_focus,
)
def select_last_cell() -> "None":
    page = get_app().notebook.page
    page.selected_index = len(list(page.children))
