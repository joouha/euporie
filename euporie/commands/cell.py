"""Defines commands relating to cells."""

import logging

from prompt_toolkit.filters import buffer_has_focus

from euporie.app.current import get_tui_app as get_app
from euporie.commands.registry import add
from euporie.filters import cell_has_focus

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
    keys=["c-\\"],
    filter=cell_has_focus & buffer_has_focus,
    group="cell",
)
def split_cell() -> "None":
    """Split the current cell at the cursor position."""
    cell = get_app().cell
    if cell is not None:
        cell.split()
