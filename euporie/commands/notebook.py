# -*- coding: utf-8 -*-
import logging

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import buffer_has_focus

from euporie.commands.registry import add
from euporie.filters import notebook_has_focus

log = logging.getLogger(__name__)


@add(
    keys="c-s",
    filter=notebook_has_focus,
    group="Notebook",
)
def save_notebook():
    get_app().notebook.save()


@add(
    filter=notebook_has_focus,
    description="Run or render all cells",
    group="Cell",
)
def run_all_cells() -> None:
    get_app().notebook.run_all()


@add(
    keys="a",
    filter=notebook_has_focus & ~buffer_has_focus,
    group="Notebook",
    description="Add new cell above current",
)
def add_cell_above() -> "None":
    get_app().notebook.add_cell_above()


@add(
    keys="b",
    filter=notebook_has_focus & ~buffer_has_focus,
    group="Notebook",
    description="Add new cell below current",
)
def add_cell_below() -> "None":
    get_app().notebook.add_cell_below()


@add(
    keys=("d", "d"),
    filter=notebook_has_focus & ~buffer_has_focus,
    group="Notebook",
    description="Delete current cell",
)
def delete_cell() -> "None":
    get_app().notebook.delete()


@add(
    keys="x",
    filter=notebook_has_focus & ~buffer_has_focus,
    group="Notebook",
    description="Cut current cell",
)
def cut_cell() -> "None":
    get_app().notebook.cut()


@add(
    keys="c",
    filter=notebook_has_focus & ~buffer_has_focus,
    group="Notebook",
    description="Copy current cell",
)
def copy_cell() -> "None":
    get_app().notebook.copy()


@add(
    keys="v",
    filter=notebook_has_focus & ~buffer_has_focus,
    group="Notebook",
    description="Paste copied cell",
)
def paste_cell() -> "None":
    get_app().notebook.paste()


@add(
    keys=("I", "I"),
    filter=notebook_has_focus & ~buffer_has_focus,
    group="Notebook",
    description="Interrupt notebook kernel",
)
def interrupt_kernel() -> "None":
    get_app().notebook.interrupt_kernel()


@add(
    keys=("0", "0"),
    filter=notebook_has_focus & ~buffer_has_focus,
    group="Notebook",
    description="Restart notebook kernel",
)
def restart_kernel() -> "None":
    get_app().notebook.restart_kernel()


@add(
    filter=notebook_has_focus & ~buffer_has_focus,
    group="Notebook",
    description="Change the notebook kernel",
)
def change_kernel() -> "None":
    get_app().notebook.change_kernel()


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
