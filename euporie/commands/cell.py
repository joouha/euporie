"""Defines commands relating to cells."""

import logging

from prompt_toolkit.filters import buffer_has_focus

from euporie.app.current import get_tui_app as get_app
from euporie.commands.registry import add
from euporie.filters import cell_has_focus, cell_is_code, have_black, kernel_is_python

log = logging.getLogger(__name__)


# Cell


@add(
    keys="e",
    filter=cell_has_focus & ~buffer_has_focus,
    group="cell",
)
async def edit_in_external_editor() -> "None":
    """Edit cell in $EDITOR."""
    cell = get_app().cell
    if cell is not None:
        await cell.edit_in_editor()


@add(
    keys=["c-enter", "c-e"],
    filter=cell_has_focus,
    group="cell",
)
def run_cell() -> None:
    """Run or render the current cell."""
    cell = get_app().cell
    if cell is not None:
        cell.run_or_render()


@add(
    keys=["s-enter", "c-r"],
    filter=cell_has_focus,
    group="cell",
)
def run_cell_and_select_next_cell() -> None:
    """Run or render the current cell and select the next cell."""
    cell = get_app().cell
    if cell is not None:
        cell.run_or_render(advance=True)


@add(
    keys=("escape", "enter"),
    filter=cell_has_focus,
    group="cell",
)
def run_cell_and_insert_below() -> None:
    """Run or render the current cell and insert a new cell below."""
    cell = get_app().cell
    if cell is not None:
        cell.run_or_render(insert=True)


@add(
    keys="enter",
    filter=cell_has_focus & ~buffer_has_focus,
    group="cell",
)
def enter_cell_edit_mode() -> "None":
    """Enter cell edit mode."""
    cell = get_app().cell
    if cell is not None:
        cell.enter_edit_mode()


@add(
    keys=["escape", ("escape", "escape")],
    filter=cell_has_focus & buffer_has_focus,
    group="cell",
)
def exit_edit_mode() -> "None":
    """Exit cell edit mode."""
    cell = get_app().cell
    if cell is not None:
        cell.exit_edit_mode()


@add(
    keys="m",
    filter=cell_has_focus & ~buffer_has_focus,
    group="cell",
)
def cell_to_markdown() -> "None":
    """Change cell type to markdown."""
    cell = get_app().cell
    if cell is not None:
        cell.set_cell_type("markdown", clear=True)


@add(
    keys="y",
    filter=cell_has_focus & ~buffer_has_focus,
    group="cell",
)
def cell_to_code() -> "None":
    """Change cell type to code."""
    cell = get_app().cell
    if cell is not None:
        cell.set_cell_type("code", clear=False)


@add(
    keys="r",
    filter=cell_has_focus & ~buffer_has_focus,
    group="cell",
)
def cell_to_raw() -> "None":
    """Change cell type to raw."""
    cell = get_app().cell
    if cell is not None:
        cell.set_cell_type("raw", clear=True)


@add(
    keys="f",
    title="Reformat cell",
    filter=have_black
    & kernel_is_python
    & cell_is_code
    & cell_has_focus
    & ~buffer_has_focus,
    group="cell",
)
def reformat_cell_black() -> "None":
    """Format a cell's code using black code formatter."""
    cell = get_app().cell
    if cell is not None:
        cell.reformat()
