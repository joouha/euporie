"""Defines commands relating to notebooks."""

import logging

from prompt_toolkit.filters import buffer_has_focus

from euporie.app.current import get_tui_app as get_app
from euporie.commands.registry import add
from euporie.filters import (
    cell_has_focus,
    cell_output_has_focus,
    code_cell_selected,
    have_formatter,
    kernel_is_python,
    multiple_cells_selected,
    notebook_has_focus,
)

log = logging.getLogger(__name__)


@add(
    keys="c-s",
    filter=notebook_has_focus,
    group="notebook",
)
def save_notebook() -> "None":
    """Save the current notebook."""
    nb = get_app().notebook
    if nb is not None:
        nb.save()


@add(
    keys="enter",
    filter=cell_has_focus & ~buffer_has_focus,
    group="notebook",
)
def enter_cell_edit_mode() -> "None":
    """Enter cell edit mode."""
    nb = get_app().notebook
    if nb is not None:
        nb.enter_edit_mode()


@add(
    keys=["escape", ("escape", "escape")],
    filter=cell_has_focus & buffer_has_focus,
    group="notebook",
)
def exit_edit_mode() -> "None":
    """Exit cell edit mode."""
    nb = get_app().notebook
    if nb is not None:
        nb.exit_edit_mode()


@add(
    keys=["c-enter", "c-e"],
    filter=cell_has_focus,
    group="notebook",
)
def run_selected_cells() -> None:
    """Run or render the current cells."""
    nb = get_app().notebook
    if nb is not None:
        nb.run_selected_cells()


@add(
    keys=["s-enter", "c-r"],
    filter=cell_has_focus,
    group="notebook",
)
def run_selected_cells_and_select_next_cell() -> None:
    """Run or render the current cells and select the next cell."""
    nb = get_app().notebook
    if nb is not None:
        nb.run_selected_cells(advance=True)


@add(
    keys=("escape", "enter"),
    filter=cell_has_focus,
    group="notebook",
)
def run_cell_and_insert_below() -> None:
    """Run or render the current cells and insert a new cell below."""
    nb = get_app().notebook
    if nb is not None:
        nb.run_selected_cells(insert=True)


@add(
    filter=notebook_has_focus,
    group="notebook",
)
def run_all_cells() -> "None":
    """Run or render all the cells in the current notebook."""
    nb = get_app().notebook
    if nb is not None:
        nb.run_all()


@add(
    keys="a",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
    group="notebook",
)
def add_cell_above() -> "None":
    """Add a new cell above the current."""
    nb = get_app().notebook
    if nb is not None:
        nb.add_cell_above()


@add(
    keys="b",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
    group="notebook",
)
def add_cell_below() -> "None":
    """Add a new cell below the current."""
    nb = get_app().notebook
    if nb is not None:
        nb.add_cell_below()


@add(
    keys=("d", "d"),
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
    group="notebook",
)
def delete_cells() -> "None":
    """Delete the current cells."""
    nb = get_app().notebook
    if nb is not None:
        nb.delete()


@add(
    keys="x",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
    group="notebook",
)
def cut_cells() -> "None":
    """Cut the current cells."""
    nb = get_app().notebook
    if nb is not None:
        nb.cut()


@add(
    keys="c",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
    group="notebook",
)
def copy_cells() -> "None":
    """Copy the current cells."""
    nb = get_app().notebook
    if nb is not None:
        nb.copy()


@add(
    keys="v",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
    group="notebook",
)
def paste_cells() -> "None":
    """Paste the previously copied cells."""
    nb = get_app().notebook
    if nb is not None:
        nb.paste()


@add(
    keys="M",
    filter=notebook_has_focus
    & ~buffer_has_focus
    & ~cell_output_has_focus
    & multiple_cells_selected,
    group="notebook",
)
def merge_cells() -> "None":
    """Merge the selected cells."""
    nb = get_app().notebook
    if nb is not None:
        nb.merge()


@add(
    keys=("I", "I"),
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
    group="notebook",
)
def interrupt_kernel() -> "None":
    """Interrupt the notebook's kernel."""
    nb = get_app().notebook
    if nb is not None:
        nb.interrupt_kernel()


@add(
    keys=("0", "0"),
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
    group="notebook",
)
def restart_kernel() -> "None":
    """Restart the notebook's kernel."""
    nb = get_app().notebook
    if nb is not None:
        nb.restart_kernel()


@add(
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
    group="notebook",
)
def change_kernel() -> "None":
    """Change the notebook's kernel."""
    nb = get_app().notebook
    if nb is not None:
        nb.change_kernel()


@add(
    keys="[",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
    group="notebook",
)
@add(
    keys="<scroll-up>",
    filter=notebook_has_focus,
    group="notebook",
)
def scroll_up() -> "None":
    """Scroll the page up a line."""
    nb = get_app().notebook
    if nb is not None:
        nb.page.scroll(1)


@add(
    keys="]",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
    group="notebook",
)
@add(
    keys="<scroll-down>",
    filter=notebook_has_focus,
    group="notebook",
)
def scroll_down() -> "None":
    """Scroll the page down a line."""
    nb = get_app().notebook
    if nb is not None:
        nb.page.scroll(-1)


@add(
    keys="{",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
    group="notebook",
)
def scroll_up_5_lines() -> "None":
    """Scroll the page up 5 lines."""
    nb = get_app().notebook
    if nb is not None:
        nb.page.scroll(5)


@add(
    keys="}",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
    group="notebook",
)
def scroll_down_5_lines() -> "None":
    """Scroll the page down 5 lines."""
    nb = get_app().notebook
    if nb is not None:
        nb.page.scroll(-5)


@add(
    keys=["home", "c-up"],
    group="notebook",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
)
def select_first_cell() -> "None":
    """Select the first cell in the notebook."""
    nb = get_app().notebook
    if nb is not None:
        nb.select(0)


@add(
    keys="pageup",
    group="notebook",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
)
def select_5th_previous_cell() -> "None":
    """Go up 5 cells."""
    nb = get_app().notebook
    if nb is not None:
        nb.select(nb.page.selected_slice.start - 5)


@add(
    keys=["up", "k"],
    group="notebook",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
)
def select_previous_cell() -> "None":
    """Go up one cell."""
    nb = get_app().notebook
    if nb is not None:
        nb.select(nb.page.selected_slice.start - 1)


@add(
    keys=["down", "j"],
    group="notebook",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
)
def select_next_cell() -> "None":
    """Select the next cell."""
    nb = get_app().notebook
    if nb is not None:
        nb.select(nb.page.selected_slice.start + 1)


@add(
    keys="pagedown",
    group="notebook",
    filter=~buffer_has_focus,
)
def select_5th_next_cell() -> "None":
    """Go down 5 cells."""
    nb = get_app().notebook
    if nb is not None:
        nb.select(nb.page.selected_slice.start + 5)


@add(
    keys=["end", "c-down"],
    group="notebook",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
)
def select_last_cell() -> "None":
    """Select the last cell in the notebook."""
    nb = get_app().notebook
    if nb is not None:
        nb.select(len(nb.page.children))


@add(
    keys="c-a",
    group="notebook",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
)
def select_all_cells() -> "None":
    """Select all cells in the notebook."""
    nb = get_app().notebook
    if nb is not None:
        nb.page.selected_slice = slice(
            0,
            len(nb.page.children) + 1,
        )


@add(
    keys=["s-home"],
    group="notebook",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
)
def extend_cell_selection_to_top() -> "None":
    """Extend the cell selection to the top of the notebook."""
    nb = get_app().notebook
    if nb is not None:
        nb.select(0, extend=True)


@add(
    keys=["s-up", "K"],
    group="notebook",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
)
def extend_cell_selection_up() -> "None":
    """Extend the cell selection up a cell."""
    nb = get_app().notebook
    if nb is not None:
        nb.select(nb.page._selected_slice.start - 1, extend=True)


@add(
    keys=["s-down", "J"],
    group="notebook",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
)
def extend_cell_selection_down() -> "None":
    """Extend the cell selection down a cell."""
    nb = get_app().notebook
    if nb is not None:
        nb.select(nb.page._selected_slice.start + 1, extend=True)


@add(
    keys=["s-end"],
    group="notebook",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
)
def extend_cell_selection_to_bottom() -> "None":
    """Extend the cell selection to the bottom of the notebook."""
    nb = get_app().notebook
    if nb is not None:
        nb.select(len(nb.json["cells"]) - 1, extend=True)


@add(
    keys=[("escape", "up")],
    group="notebook",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
)
def move_cells_up() -> "None":
    """Move selected cells up."""
    nb = get_app().notebook
    if nb is not None:
        nb.move(-1)


@add(
    keys=[("escape", "down")],
    group="notebook",
    filter=notebook_has_focus & ~buffer_has_focus & ~cell_output_has_focus,
)
def move_cells_down() -> "None":
    """Move selected cells down."""
    nb = get_app().notebook
    if nb is not None:
        nb.move(1)


@add(
    keys="m",
    filter=cell_has_focus & ~buffer_has_focus,
    group="notebook",
)
def cells_to_markdown() -> "None":
    """Change selected cells to markdown cells."""
    nb = get_app().notebook
    if nb is not None:
        for cell in nb.cells:
            cell.set_cell_type("markdown", clear=True)


@add(
    keys="y",
    filter=cell_has_focus & ~buffer_has_focus,
    group="notebook",
)
def cells_to_code() -> "None":
    """Change selected cells to code cells."""
    nb = get_app().notebook
    if nb is not None:
        for cell in nb.cells:
            cell.set_cell_type("code", clear=False)


@add(
    keys="r",
    filter=cell_has_focus & ~buffer_has_focus,
    group="notebook",
)
def cells_to_raw() -> "None":
    """Change selected cells to raw cells."""
    nb = get_app().notebook
    if nb is not None:
        for cell in nb.cells:
            cell.set_cell_type("raw", clear=True)


@add(
    keys="f",
    title="Reformat cells",
    filter=have_formatter
    & code_cell_selected
    & kernel_is_python
    & cell_has_focus
    & ~buffer_has_focus,
    group="cell",
)
def reformat_cells() -> "None":
    """Format the selected code cells."""
    nb = get_app().notebook
    if nb is not None:
        for cell in nb.cells:
            if cell.cell_type == "code":
                cell.reformat()


@add(
    keys="F",
    group="notebook",
    filter=have_formatter & kernel_is_python & notebook_has_focus & ~buffer_has_focus,
)
def reformat_notebook() -> "None":
    """Automatically reformat all code cells in the notebook."""
    nb = get_app().notebook
    if nb is not None:
        nb.reformat()
