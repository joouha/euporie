# -*- coding: utf-8 -*-
import logging

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import buffer_has_focus

from euporie.commands.registry import add
from euporie.filters import cell_has_focus

log = logging.getLogger(__name__)


# Cell


@add(
    keys="e",
    filter=cell_has_focus & ~buffer_has_focus,
    group="Cell",
    description="Edit cell in $EDITOR",
)
async def edit_in_external_editor() -> "None":
    await get_app().cell.edit_in_editor()


@add(
    keys=["c-e", ("escape", "[", "1", "3", ";", "5", "u"), "c-f20"],
    filter=cell_has_focus,
    description="Run or render the current cell",
    group="Cell",
)
def run_cell() -> None:
    get_app().cell.run_or_render()


@add(
    keys=["c-r", ("escape", "[", "1", "3", ";", "2", "u"), "f21"],
    filter=cell_has_focus,
    description="Run or render the current cell and select the next cell",
    group="Cell",
)
def run_cell_and_select_next_cell() -> None:
    get_app().cell.run_or_render(advance=True)


@add(
    keys=("escape", "enter"),
    filter=cell_has_focus,
    description="Run or render the current cell and insert a new cell below",
    group="Cell",
)
def run_cell_and_insert_below() -> None:
    get_app().cell.run_or_render(insert=True)


@add(
    keys="enter",
    filter=cell_has_focus & ~buffer_has_focus,
    group="Cell",
    description="Enter cell edit mode",
)
def enter_cell_edit_mode() -> "None":
    get_app().cell.enter_edit_mode()


@add(
    keys=["escape", ("escape", "escape")],
    filter=cell_has_focus & buffer_has_focus,
    group="Cell",
    description="Exit cell edit mode",
)
def exit_edit_mode() -> "None":
    get_app().cell.exit_edit_mode()


@add(
    keys="m",
    filter=cell_has_focus & ~buffer_has_focus,
    group="Cell",
    description="Change cell type to markdown",
)
def to_markdown() -> "None":
    get_app().cell.set_cell_type("markdown", clear=True)


@add(
    keys="y",
    filter=cell_has_focus & ~buffer_has_focus,
    group="Cell",
    description="Change cell type to code",
)
def cell_to_code() -> "None":
    get_app().cell.set_cell_type("code", clear=False)


@add(
    keys="r",
    filter=cell_has_focus & ~buffer_has_focus,
    group="Cell",
    description="Change cell type to raw",
)
def cell_to_raw() -> "None":
    get_app().cell.set_cell_type("raw", clear=True)
