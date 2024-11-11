"""Defines tab commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.filters import (
    buffer_has_focus,
    has_completions,
    vi_mode,
    vi_navigation_mode,
)

from euporie.core.app.current import get_app
from euporie.core.commands import add_cmd, get_cmd
from euporie.core.filters import (
    cursor_on_first_line,
    cursor_on_last_line,
    display_has_focus,
    kernel_tab_has_focus,
    multiple_cells_selected,
)
from euporie.core.tabs.kernel import KernelTab
from euporie.notebook.filters import (
    cell_has_focus,
    code_cell_selected,
    deleted_cells,
    notebook_has_focus,
)

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone

# euporie.notebook.tabs.log


@add_cmd()
def _view_logs() -> None:
    """Open the logs in a new tab."""
    from euporie.notebook.tabs.log import LogView

    app = get_app()
    for tab in app.tabs:
        if isinstance(tab, LogView):
            break
    else:
        tab = LogView(app)
        app.add_tab(tab)
    tab.focus()


# euporie.notebook.tabs.notebook


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
)
def _enter_cell_edit_mode() -> None:
    """Enter cell edit mode."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.enter_edit_mode()


@add_cmd(
    filter=cell_has_focus
    & buffer_has_focus
    & (~vi_mode | (vi_mode & vi_navigation_mode)),
)
def _exit_edit_mode() -> None:
    """Exit cell edit mode."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.exit_edit_mode()


@add_cmd(
    filter=cell_has_focus,
)
def _run_selected_cells() -> None:
    """Run or render the current cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.run_selected_cells()


@add_cmd(
    title="Run selected cells and select next cell",
    filter=cell_has_focus,
)
def _run_and_select_next() -> None:
    """Run or render the current cells and select the next cell."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.run_selected_cells(advance=True)


@add_cmd(
    filter=cell_has_focus,
)
def _run_cell_and_insert_below() -> None:
    """Run or render the current cells and insert a new cell below."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.run_selected_cells(insert=True)


@add_cmd(
    filter=notebook_has_focus,
)
def _run_all_cells() -> None:
    """Run or render all the cells in the current notebook."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.run_all()


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _add_cell_above() -> None:
    """Add a new cell above the current."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.add_cell_above()


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _add_cell_below() -> None:
    """Add a new cell below the current."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.add_cell_below()


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _delete_cells() -> None:
    """Delete the current cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.delete()


@add_cmd(
    menu_title="Undo delete cell",
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus & deleted_cells,
)
def _undelete_cells() -> None:
    """Undelete the last deleted cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.undelete()


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _cut_cells() -> None:
    """Cut the current cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.cut()


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _copy_cells() -> None:
    """Copy the current cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.copy()


@add_cmd(
    menu_title="Copy cell outputs",
    filter=cell_has_focus & ~buffer_has_focus,
)
def _copy_outputs() -> None:
    """Copy the cell's output to the clipboard."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.copy_outputs()


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _paste_cells() -> None:
    """Pate the previously copied cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.paste()


@add_cmd(
    filter=notebook_has_focus
    & ~buffer_has_focus
    & ~display_has_focus
    & multiple_cells_selected,
)
def _merge_cells() -> None:
    """Merge the selected cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.merge()


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
@add_cmd(
    filter=notebook_has_focus,
)
def _scroll_up() -> NotImplementedOrNone:
    """Scroll the page up a line."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        return nb.page.scroll(1)
    return None


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
@add_cmd(
    filter=notebook_has_focus,
)
def _scroll_down() -> NotImplementedOrNone:
    """Scroll the page down a line."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        return nb.page.scroll(-1)
    return None


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _scroll_up_5_lines() -> None:
    """Scroll the page up 5 lines."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.page.scroll(5)


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _scroll_down_5_lines() -> None:
    """Scroll the page down 5 lines."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.page.scroll(-5)


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _select_first_cell() -> None:
    """Select the first cell in the notebook."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.select(0)


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _select_5th_previous_cell() -> None:
    """Go up 5 cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.select(nb.page.selected_slice.start - 5)


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _select_previous_cell() -> None:
    """Go up one cell."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.select(nb.page.selected_slice.start - 1)


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _select_next_cell() -> None:
    """Select the next cell."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.select(nb.page.selected_slice.start + 1)


@add_cmd(
    filter=~buffer_has_focus,
)
def _select_5th_next_cell() -> None:
    """Go down 5 cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.select(nb.page.selected_slice.start + 5)


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _select_last_cell() -> None:
    """Select the last cell in the notebook."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.select(len(nb.page.all_children()) - 1)


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _select_all_cells() -> None:
    """Select all cells in the notebook."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.page.selected_slice = slice(
            0,
            len(nb.page.all_children()) + 1,
        )


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _extend_cell_selection_to_top() -> None:
    """Extend the cell selection to the top of the notebook."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.select(0, extend=True)


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _extend_cell_selection_up() -> None:
    """Extend the cell selection up a cell."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.select(nb.page._selected_slice.start - 1, extend=True)


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _extend_cell_selection_down() -> None:
    """Extend the cell selection down a cell."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.select(nb.page._selected_slice.start + 1, extend=True)


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _extend_cell_selection_to_bottom() -> None:
    """Extend the cell selection to the bottom of the notebook."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.select(len(nb.json["cells"]) - 1, extend=True)


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _move_cells_up() -> None:
    """Move selected cells up."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.move(-1)


@add_cmd(
    filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _move_cells_down() -> None:
    """Move selected cells down."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.move(1)


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
)
def _cells_to_markdown() -> None:
    """Change selected cells to markdown cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        for cell in nb.cells:
            cell.set_cell_type("markdown", clear=True)
            # Remove unallowed additional properties
            json = cell.json
            json.pop("execution_count", None)
            json.pop("outputs", None)
            cell.run_or_render()


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
)
def _cells_to_code() -> None:
    """Change selected cells to code cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        for cell in nb.cells:
            cell.set_cell_type("code", clear=False)


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
)
def _cells_to_raw() -> None:
    """Change selected cells to raw cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        for cell in nb.cells:
            cell.set_cell_type("raw", clear=True)


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
)
def _clear_cell_outputs() -> None:
    """Clear the outputs of the selected cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        for cell in nb.cells:
            cell.remove_outputs()


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
)
def _clear_all_outputs() -> None:
    """Clear the outputs of the selected cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        for cell in nb._rendered_cells.values():
            cell.remove_outputs()


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
    title="Expand cell inputs",
)
def _show_cell_inputs() -> None:
    """Expand the selected cells' inputs."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        for cell in nb.cells:
            cell.show_input()


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
    title="Collapse cell inputs",
)
def _hide_cell_inputs() -> None:
    """Collapse the selected cells' inputs."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        for cell in nb.cells:
            cell.hide_input()


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
)
def _toggle_cell_inputs() -> None:
    """Toggle the visibility of the selected cells' inputs."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        for cell in nb.cells:
            cell.toggle_input()


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
    title="Expand cell outputs",
)
def _show_cell_outputs() -> None:
    """Expand the selected cells' outputs."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        for cell in nb.cells:
            cell.show_output()


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
    title="Collapse cell outputs",
)
def _hide_cell_outputs() -> None:
    """Collapse the selected cells' outputs."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        for cell in nb.cells:
            cell.hide_output()


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
)
def _toggle_cell_outputs() -> None:
    """Toggle the visibility of the selected cells' outputs."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        for cell in nb.cells:
            cell.toggle_output()


@add_cmd(
    title="Reformat cells",
    filter=code_cell_selected & cell_has_focus & ~buffer_has_focus & notebook_has_focus,
)
def _reformat_cells() -> None:
    """Format the selected code cells."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        for cell in nb.cells:
            if cell.cell_type == "code":
                cell.input_box.reformat()


@add_cmd(aliases=["fmt"], filter=notebook_has_focus & ~buffer_has_focus)
def _reformat_notebook() -> None:
    """Automatically reformat all code cells in the notebook."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.reformat()


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
)
async def _edit_in_external_editor() -> None:
    """Edit cell in $EDITOR."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        await nb.cell.edit_in_editor()


@add_cmd(
    filter=cell_has_focus & buffer_has_focus,
)
def _split_cell() -> None:
    """Split the current cell at the cursor position."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.split_cell()


@add_cmd(
    name="edit-previous-cell-vi",
    filter=cell_has_focus
    & buffer_has_focus
    & cursor_on_first_line
    & ~has_completions
    & vi_mode
    & vi_navigation_mode,
)
@add_cmd(
    filter=cell_has_focus & buffer_has_focus & cursor_on_first_line & ~has_completions
)
def _edit_previous_cell() -> None:
    """Move the cursor up to the previous cell."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        new_index = nb.cell.index - 1
        cells = nb.rendered_cells()
        if 0 <= new_index < len(cells):
            nb.select(index=new_index, position=-1, scroll=True)


@add_cmd(
    name="edit-next-cell-vi",
    filter=cell_has_focus
    & buffer_has_focus
    & cursor_on_last_line
    & ~has_completions
    & vi_mode
    & vi_navigation_mode,
)
@add_cmd(
    filter=cell_has_focus & buffer_has_focus & cursor_on_last_line & ~has_completions
)
def _edit_next_cell() -> None:
    """Move the cursor down to the next cell."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        new_index = nb.cell.index + 1
        cells = nb.rendered_cells()
        if 0 <= new_index < len(cells):
            nb.select(index=new_index, position=0, scroll=True)


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
)
def _scroll_output_left() -> None:
    """Scroll the cell output to the left."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.cell.output_area.scroll_left()


@add_cmd(
    filter=cell_has_focus & ~buffer_has_focus,
)
def _scroll_output_right() -> None:
    """Scroll the cell output to the right."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.cell.output_area.scroll_right()


@add_cmd(
    filter=kernel_tab_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _interrupt_kernel() -> None:
    """Interrupt the notebook's kernel."""
    if isinstance(kt := get_app().tab, KernelTab):
        kt.interrupt_kernel()


@add_cmd(
    filter=kernel_tab_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _restart_kernel() -> None:
    """Restart the notebook's kernel."""
    if isinstance(kt := get_app().tab, KernelTab):
        kt.restart_kernel()


@add_cmd(
    filter=kernel_tab_has_focus & ~buffer_has_focus & ~display_has_focus,
)
def _restart_kernel_and_clear_all_outputs() -> None:
    """Restart the notebook's kernel and clear all cell output."""
    from euporie.notebook.tabs.notebook import Notebook

    if isinstance(nb := get_app().tab, Notebook):
        nb.restart_kernel(cb=_clear_all_outputs)


@add_cmd(
    filter=~buffer_has_focus,
)
def _notebook_toggle_line_numbers() -> None:
    """Toggle line numbers when a buffer does not have focus."""
    get_cmd("toggle-line-numbers").run()
