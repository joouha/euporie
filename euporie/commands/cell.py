"""Defines commands relating to cells."""

import logging

from prompt_toolkit.filters import buffer_has_focus, has_completions

from euporie.app.current import get_edit_app as get_app
from euporie.commands.registry import add
from euporie.filters import cell_has_focus, cursor_on_first_line, cursor_on_last_line

log = logging.getLogger(__name__)


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


@add(
    keys=["up"],
    filter=cell_has_focus & buffer_has_focus & cursor_on_first_line & ~has_completions,
    group="cell",
)
def edit_previous_cell() -> "None":
    """Move the cursor up to the previous cell."""
    nb = get_app().notebook
    if nb is not None:
        new_index = nb.cell.index - 1
        cells = nb.rendered_cells()
        if 0 <= new_index < len(cells):
            cells[new_index].select(position=-1)


@add(
    keys=["down"],
    filter=cell_has_focus & buffer_has_focus & cursor_on_last_line & ~has_completions,
    group="cell",
)
def edit_next_cell() -> "None":
    """Move the cursor down to the next cell."""
    nb = get_app().notebook
    if nb is not None:
        new_index = nb.cell.index + 1
        cells = nb.rendered_cells()
        if 0 <= new_index < len(cells):
            cells[new_index].select(position=0)


@add(
    keys=["left"],
    filter=cell_has_focus & ~buffer_has_focus,
    group="cell",
)
def scroll_output_left() -> "None":
    """Scroll the cell output to the left."""
    from euporie.widgets.output.container import OutputWindow

    nb = get_app().notebook
    if nb is not None:
        for output_window in nb.cell.output_box.children:
            assert isinstance(output_window, OutputWindow)
            output_window._scroll_left()


@add(
    keys=["right"],
    filter=cell_has_focus & ~buffer_has_focus,
    group="cell",
)
def scroll_output_right() -> "None":
    """Scroll the cell output to the right."""
    from euporie.widgets.output.container import OutputWindow

    nb = get_app().notebook
    if nb is not None:
        for output_window in nb.cell.output_box.children:
            assert isinstance(output_window, OutputWindow)
            output_window._scroll_right()
