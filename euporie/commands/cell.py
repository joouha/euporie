"""Defines commands relating to cells."""

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
)
async def edit_in_external_editor() -> "None":
    """Edit cell in $EDITOR."""
    await get_app().cell.edit_in_editor()


@add(
    keys=["c-e", ("escape", "[", "1", "3", ";", "5", "u"), "c-f20"],
    filter=cell_has_focus,
    group="Cell",
)
def run_cell() -> None:
    """Run or render the current cell."""
    get_app().cell.run_or_render()


@add(
    keys=["c-r", ("escape", "[", "1", "3", ";", "2", "u"), "f21"],
    filter=cell_has_focus,
    group="Cell",
)
def run_cell_and_select_next_cell() -> None:
    """Run or render the current cell and select the next cell."""
    get_app().cell.run_or_render(advance=True)


@add(
    keys=("escape", "enter"),
    filter=cell_has_focus,
    group="Cell",
)
def run_cell_and_insert_below() -> None:
    """Run or render the current cell and insert a new cell below."""
    get_app().cell.run_or_render(insert=True)


@add(
    keys="enter",
    filter=cell_has_focus & ~buffer_has_focus,
    group="Cell",
)
def enter_cell_edit_mode() -> "None":
    """Enter cell edit mode."""
    get_app().cell.enter_edit_mode()


@add(
    keys=["escape", ("escape", "escape")],
    filter=cell_has_focus & buffer_has_focus,
    group="Cell",
)
def exit_edit_mode() -> "None":
    """Exit cell edit mode."""
    get_app().cell.exit_edit_mode()


@add(
    keys="m",
    filter=cell_has_focus & ~buffer_has_focus,
    group="Cell",
)
def to_markdown() -> "None":
    """Change cell type to markdown."""
    get_app().cell.set_cell_type("markdown", clear=True)


@add(
    keys="y",
    filter=cell_has_focus & ~buffer_has_focus,
    group="Cell",
)
def cell_to_code() -> "None":
    """Change cell type to code."""
    get_app().cell.set_cell_type("code", clear=False)


@add(
    keys="r",
    filter=cell_has_focus & ~buffer_has_focus,
    group="Cell",
)
def cell_to_raw() -> "None":
    """Change cell type to raw."""
    get_app().cell.set_cell_type("raw", clear=True)
