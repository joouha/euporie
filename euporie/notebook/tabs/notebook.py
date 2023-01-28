"""Contains the main class for a notebook file."""

from __future__ import annotations

import logging
from collections import deque
from copy import deepcopy
from functools import partial
from typing import TYPE_CHECKING, cast

import nbformat
from prompt_toolkit.clipboard.base import ClipboardData
from prompt_toolkit.filters import (
    Condition,
    buffer_has_focus,
    has_completions,
    vi_mode,
    vi_navigation_mode,
)
from prompt_toolkit.layout.containers import ConditionalContainer, VSplit
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.mouse_events import MouseEventType

from euporie.core.commands import add_cmd, get_cmd
from euporie.core.config import add_setting
from euporie.core.current import get_app
from euporie.core.filters import (
    cursor_on_first_line,
    cursor_on_last_line,
    display_has_focus,
    have_formatter,
    insert_mode,
    kernel_is_python,
    kernel_tab_has_focus,
    multiple_cells_selected,
    replace_mode,
)
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.style import KERNEL_STATUS_REPR
from euporie.core.tabs.base import KernelTab
from euporie.core.tabs.notebook import BaseNotebook
from euporie.core.widgets.cell import Cell
from euporie.core.widgets.decor import Line, Pattern
from euporie.core.widgets.page import ScrollingContainer
from euporie.notebook.filters import (
    cell_has_focus,
    code_cell_selected,
    deleted_cells,
    notebook_has_focus,
)

if TYPE_CHECKING:
    from typing import Any, Deque, MutableSequence, Optional, Sequence

    from prompt_toolkit.formatted_text.base import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.mouse_events import MouseEvent
    from upath import UPath

    from euporie.core.app import BaseApp
    from euporie.core.comm.base import Comm
    from euporie.core.kernel import Kernel

log = logging.getLogger(__name__)


class Notebook(BaseNotebook):
    """Interactive notebooks.

    A tab which allows running and editing a notebook.
    """

    allow_stdin = True

    def __init__(
        self,
        app: "BaseApp",
        path: "Optional[UPath]" = None,
        kernel: "Optional[Kernel]" = None,
        comms: "Optional[dict[str, Comm]]" = None,
        use_kernel_history: "bool" = True,
        json: "Optional[dict[str, Any]]" = None,
    ) -> "None":
        """Load a editable notebook."""
        super().__init__(
            app=app,
            path=path,
            kernel=kernel,
            comms=comms,
            use_kernel_history=use_kernel_history,
            json=json,
        )

        self.edit_mode = False
        self.in_edit_mode = Condition(self.check_edit_mode)
        self.multiple_cells_selected = multiple_cells_selected
        self.clipboard: "list[Cell]" = []
        self.undo_buffer: "Deque[tuple[int, list[Cell]]]" = deque(maxlen=10)

        if not kernel:
            self.kernel.start(cb=self.kernel_started, wait=False)

    # Tab stuff

    def _statusbar_kernel_handeler(self, event: "MouseEvent") -> "NotImplementedOrNone":
        """Event handler for kernel name field in statusbar."""
        if event.event_type == MouseEventType.MOUSE_UP:
            get_cmd("change-kernel").run()
            return None
        else:
            return NotImplemented

    def statusbar_fields(
        self,
    ) -> "tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]":
        """Generates the formatted text for the statusbar."""
        rendered = self.page.pre_rendered
        return (
            [
                self.mode(),
                f"Cell {self.page.selected_slice.start+1}",
                f"Rendering… ({rendered:.0%})" if rendered < 1 else "",
                "Saving…" if self.saving else "",
            ],
            [
                lambda: cast(
                    "StyleAndTextTuples",
                    [("", self.kernel_display_name, self._statusbar_kernel_handeler)],
                ),
                KERNEL_STATUS_REPR[self.kernel.status] if self.kernel else ".",
            ],
        )

    # Notebook stuff

    @property
    def selected_indices(self) -> "list[int]":
        """Return a list of the currently selected cell indices."""
        return self.page.selected_indices

    def kernel_started(self, result: "Optional[dict[str, Any]]" = None) -> "None":
        """Run when the kernel has started."""
        super().kernel_started(result)
        if not self.kernel_name or self.kernel.missing:
            if not self.kernel_name:
                msg = "No kernel selected"
            else:
                msg = f"Kernel '{self.kernel_display_name}' not installed"
            self.change_kernel(
                msg=msg,
                startup=True,
            )
        elif self.kernel.status == "error":
            self.app.dialogs["error"].show(
                exception=self.kernel.error, when="starting the kernel"
            )
        elif self.kernel.status == "idle":
            if self.app.config.run:
                self.run_all(wait=False)

    def load_container(self) -> "AnyContainer":
        """Load the main notebook container."""
        self.page = ScrollingContainer(
            self.rendered_cells, width=self.app.config.max_notebook_width
        )

        expand = Condition(lambda: self.app.config.expand)

        pattern = Pattern(
            partial(getattr, self.app.config, "background_character"),
            partial(getattr, self.app.config, "background_pattern"),
        )

        return VSplit(
            [
                ConditionalContainer(
                    VSplit(
                        [
                            pattern,
                            Line(
                                char="▋",  # 5/8
                                width=1,
                                collapse=True,
                                style="class:drop-shadow,outer reverse",
                            ),
                            Line(
                                char="▎",  # 2/8
                                width=1,
                                collapse=True,
                                style="class:drop-shadow,inner",
                            ),
                        ]
                    ),
                    filter=~expand,
                ),
                self.page,
                ConditionalContainer(
                    VSplit(
                        [
                            Line(
                                char="▊",  # 6/8
                                width=1,
                                collapse=True,
                                style="class:drop-shadow,inner reverse",
                            ),
                            Line(
                                char="▍",  # 3/8
                                width=1,
                                collapse=True,
                                style="class:drop-shadow,outer",
                            ),
                            pattern,
                        ]
                    ),
                    filter=~expand,
                ),
                ConditionalContainer(
                    MarginContainer(ScrollbarMargin(), target=self.page),
                    filter=Condition(lambda: self.app.config.show_scroll_bar),
                ),
            ],
            width=Dimension(weight=1),
            height=Dimension(min=1, weight=2),
            key_bindings=load_registered_bindings(
                "euporie.notebook.tabs.notebook.Notebook"
            ),
        )

    @property
    def cell(self) -> "Cell":
        """Returns the currently selected `Cell` in this `Notebook`."""
        cell = self.page.get_child()
        assert isinstance(cell, Cell)
        return cell

    # Editing specific stuff

    @property
    def cells(self) -> "Sequence[Cell]":
        """Returns the currently selected `Cells` in this `Notebook`."""
        return [
            child
            for child in self.page.children[self.page.selected_slice]
            if isinstance(child, Cell)
        ]

    def check_edit_mode(self) -> "bool":
        """Determine if the notebook is (or should be) in edit mode."""
        if self.cell.input_box.has_focus():
            self.edit_mode = True
        return self.edit_mode

    def enter_edit_mode(self) -> "None":
        """Enter cell edit mode."""
        self.edit_mode = True
        self.select(self.cell.index)
        self.scroll_to(self.cell.index)

    def exit_edit_mode(self) -> "None":
        """Leave cell edit mode."""
        self.edit_mode = False
        self.select(self.cell.index)

    def mode(self) -> "str":
        """Returns a symbol representing the current mode.

        * ``^``: Notebook mode
        * ``>``: Navigation mode
        * ``I``: Insert mode
        * ``v``: Visual mode

        Returns:
            A character representing the current mode
        """
        # TODO - sort this out
        if self.in_edit_mode():
            if insert_mode():
                return "I"
            elif replace_mode():
                return "o"
            else:
                return ">"
        return "^"

    def select(
        self,
        index: "int",
        extend: "bool" = False,
        position: "Optional[int]" = None,
        scroll: "bool" = True,
    ) -> "None":
        """Selects a cell or adds it to the selection.

        Args:
            index: The index of the cell to select
            extend: If true, the selection will be extended to include the cell
            position: An optional cursor position index to apply to the cell input
            scroll: Whether to scroll the page

        """
        self.page.select(index=index, extend=extend, position=position, scroll=scroll)
        # Focus the selected cell - use the current slice in case it did not change
        self.rendered_cells()[self.page.selected_slice.start].focus(
            position, scroll=scroll
        )

    def scroll_to(self, index: "int") -> "None":
        """Scroll to a cell by index."""
        self.page.scroll_to(index)

    def refresh(
        self, slice_: "Optional[slice]" = None, scroll: "bool" = True
    ) -> "None":
        """Refresh the rendered contents of this notebook."""
        if slice_ is None:
            slice_ = self.page._selected_slice
        # This triggers another redraw of the selected cell
        self.page._set_selected_slice(slice_, force=True, scroll=scroll)
        self.page.reset()

    def refresh_cell(self, cell: "Cell") -> "None":
        """Trigger the refresh of a notebook cell."""
        self.page.get_child_render_info(cell.index).refresh = True

    def add_cell_above(self) -> "None":
        """Insert a cell above the current selection."""
        index = self.page.selected_slice.start + 0
        self.add(index)
        self.refresh(slice_=slice(index, index + 1), scroll=False)

    def add_cell_below(self) -> "None":
        """Insert a cell below the current selection."""
        index = self.page.selected_slice.start + 1
        self.add(index)
        self.refresh(slice_=slice(index, index + 1), scroll=True)

    def cut(self, slice_: "Optional[slice]" = None) -> "None":
        """Remove cells from the notebook and them to the `Notebook`'s clipboard."""
        if slice_ is None:
            slice_ = self.page.selected_slice
        self.copy(slice_)
        self.delete(slice_)

    def copy(self, slice_: "Optional[slice]" = None) -> "None":
        """Add a copy of the selected cells to the `Notebook`'s clipboard."""
        if slice_ is None:
            slice_ = self.page.selected_slice
        indices = range(*slice_.indices(len(self.json["cells"])))
        self.clipboard = deepcopy(
            # Sort clipboard contents by index)
            [
                x
                for _, x in sorted(
                    zip(indices, self.json["cells"][slice_]), key=lambda x: x[0]
                )
            ]
        )

    def copy_outputs(self, slice_: "Optional[slice]" = None) -> "None":
        """Copy the outputs of the selected cells."""
        if slice_ is None:
            slice_ = self.page.selected_slice
        output_strings = []

        indices = sorted(range(*slice_.indices(len(self.json["cells"]))))
        rendered_cells = list(self._rendered_cells.values())

        for index in indices:
            cell = rendered_cells[index]
            output_strings.append(cell.output_area.to_plain_text())

        if output_strings:
            self.app.clipboard.set_data(ClipboardData("\n\n".join(output_strings)))

    def paste(self, index: "Optional[int]" = None) -> "None":
        """Append the contents of the `Notebook`'s clipboard below the current cell."""
        if index is None:
            index = self.page.selected_slice.start
        cell_jsons: "MutableSequence" = deepcopy(self.clipboard)
        # Assign a new cell IDs
        for cell_json in cell_jsons:
            cell_json["id"] = nbformat.v4.new_code_cell().get("id")
        self.json["cells"][index + 1 : index + 1] = cell_jsons
        self.dirty = True
        # Only change the selected cell if we actually pasted something
        if cell_jsons:
            self.refresh(slice(index + 1, index + 1 + len(cell_jsons)))

    def add(self, index: "int", source: "str" = "", **kwargs: "Any") -> "None":
        """Creates a new cell at a given index.

        Args:
            index: The position at which to insert a new cell
            source: The contents of the new cell
            kwargs: Additional parameters for the cell

        """
        self.json["cells"].insert(
            index,
            nbformat.v4.new_code_cell(source=source, **kwargs),
        )
        self.dirty = True

    def move(self, n: "int", slice_: "Optional[slice]" = None) -> "None":
        """Move a slice of cells up or down.

        Args:
            slice_: A slice describing the cell indices to move
            n: The amount to move them by

        """
        if slice_ is None:
            slice_ = self.page.selected_slice
        if slice_ is not None:
            indices = range(*slice_.indices(len(self.json["cells"])))
            index = min(indices) + n
            if 0 <= index and index + len(indices) <= len(self.json["cells"]):
                cells = [
                    x
                    for _, x in sorted(
                        zip(indices, self.json["cells"][slice_]), key=lambda x: x[0]
                    )
                ]
                del self.json["cells"][slice_]
                self.json["cells"][index:index] = cells
                self.refresh(
                    slice(
                        slice_.start + n,
                        (-1 if slice_.stop is None else slice_.stop) + n,
                        slice_.step,
                    )
                )
            self.dirty = True

    def delete(self, slice_: "Optional[slice]" = None) -> "None":
        """Delete cells from the notebook."""
        if slice_ is None:
            slice_ = self.page.selected_slice
        if slice_ is not None:
            indices = sorted(range(*slice_.indices(len(self.json["cells"]))))
            index = min(indices)
            cell_jsons = [
                x[1] for x in sorted(zip(indices, self.json["cells"][slice_]))
            ]
            self.undo_buffer.append((index, cell_jsons))
            del self.json["cells"][slice_]
            # Ensure there is always one cell
            if len(self.json["cells"]) == 0:
                self.add(1)
            # Get top cell of deleted range or cell above it
            slice_top = max(0, min(index, len(self.json["cells"]) - 1))
            self.refresh(slice(slice_top, slice_top + 1), scroll=True)
            self.dirty = True

    def undelete(self) -> "None":
        """Inserts the last deleted cell(s) back into the notebook."""
        if self.undo_buffer:
            index, cells = self.undo_buffer.pop()
            self.json["cells"][index:index] = cells
            self.refresh(slice(index, index + len(cells)))

    def merge(self, slice_: "Optional[slice]" = None) -> "None":
        """Merge two or more cells."""
        if slice_ is None:
            slice_ = self.page.selected_slice
        if slice_ is not None:
            indices = sorted(range(*slice_.indices(len(self.json["cells"]))))
            if len(indices) >= 2:
                # Create a new cell
                new_cell_json = nbformat.v4.new_code_cell()
                # Set the type for that for the focused cell
                cell_type = self.json["cells"][slice_.start].get("cell_type", "code")
                new_cell_json["cell_type"] = cell_type
                # Create and set the combined cell source
                sources = []
                for i in indices:
                    cell_json = self.json["cells"][i]
                    source = cell_json.get("source", "")
                    # Comment markdown cell contents if merging into code cell
                    if cell_type == "code" and cell_json.get("cell_type") == "markdown":
                        source = "\n".join([f"# {line}" for line in source.split("\n")])
                    sources.append(source)
                new_cell_json["source"] = "\n\n".join(sources)
                # Insert the new cell
                new_index = max(indices) + 1
                self.json["cells"].insert(new_index, new_cell_json)
                # Delete the selected slice
                self.delete(slice_)
                # Select the new cell
                self.select(indices[0])
                self.dirty = True

    def split_cell(self) -> "None":
        """Splits a cell into two at the cursor position."""
        # Get the current cell
        cell = self.cell
        # Get the cursor position in the cell
        cursor_position = cell.input_box.buffer.cursor_position
        # Reset the cursor position to avoid an error after splitting
        cell.input_box.buffer.cursor_position = 0
        # Get the cell contents
        source = cell.json.get("source", "")
        # Create a new cell
        new_cell_json = nbformat.v4.new_code_cell()
        # Split the cell contents at the cursor position
        cell.input = source[cursor_position:]
        new_cell_json["source"] = source[:cursor_position]
        # Copy the cell type
        new_cell_json["cell_type"] = cell.json["cell_type"]
        # Add the new cell to the notebook
        self.json["cells"].insert(cell.index, new_cell_json)
        # Refresh the notebook display
        self.refresh()

    def reformat(self) -> "None":
        """Reformat all code cells in the notebooks."""
        for cell in self.rendered_cells():
            if cell.cell_type == "code":
                cell.reformat()

    def run_selected_cells(
        self,
        advance: "bool" = False,
        insert: "bool" = False,
    ) -> "None":
        """Runs the currently selected cells.

        Args:
            advance: If True, move to next cell. If True and at the last cell, create a
                new cell at the end of the notebook.
            insert: If True, add a new empty cell below the current cell and select it.

        """
        self.exit_edit_mode()
        n_cells = len(self.json["cells"])
        selected_indices = self.page.selected_indices
        cells = {cell.index: cell for cell in self._rendered_cells.values()}

        # Run the cells
        for i in sorted(selected_indices):
            cells[i].run_or_render()
        # Insert a cell if we are at the last cell
        index = max(selected_indices)
        if insert or (advance and max(selected_indices) == (n_cells) - 1):
            self.add(index + 1)
            self.refresh(slice_=slice(index + 1, index + 2), scroll=True)
        elif advance:
            self.select(index + 1)

    def run_all(self, wait: "bool" = False) -> "None":
        """Run all cells."""
        if self.kernel:
            log.debug("Running all cells (wait=%s)", wait)
            for cell in self.rendered_cells():
                if cell.json.get("cell_type") == "code":
                    log.debug("Running cell %s", cell.id)
                    cell.run_or_render(wait=wait)
            log.debug("All cells run")

    # ################################### Settings ####################################

    add_setting(
        name="show_scroll_bar",
        title="scroll bar",
        flags=["--show-scroll-bar"],
        type_=bool,
        help_="Show the scroll bar",
        default=True,
        description="""
            Whether the scroll bar should be shown on the right of the screen.
        """,
    )

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus,
    )
    def _save_notebook() -> "None":
        """Save the current notebook."""
        tab = get_app().tab
        if isinstance(tab, Notebook):
            tab.save()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
    )
    def _enter_cell_edit_mode() -> "None":
        """Enter cell edit mode."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.enter_edit_mode()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus
        & buffer_has_focus
        & (~vi_mode | (vi_mode & vi_navigation_mode)),
    )
    def _exit_edit_mode() -> "None":
        """Exit cell edit mode."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.exit_edit_mode()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus,
    )
    def _run_selected_cells() -> "None":
        """Run or render the current cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.run_selected_cells()

    @staticmethod
    @add_cmd(
        title="Run selected cells and select next cell",
        filter=cell_has_focus,
    )
    def _run_and_select_next() -> "None":
        """Run or render the current cells and select the next cell."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.run_selected_cells(advance=True)

    @staticmethod
    @add_cmd(
        filter=cell_has_focus,
    )
    def _run_cell_and_insert_below() -> "None":
        """Run or render the current cells and insert a new cell below."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.run_selected_cells(insert=True)

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus,
    )
    def _run_all_cells() -> "None":
        """Run or render all the cells in the current notebook."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.run_all()

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _add_cell_above() -> "None":
        """Add a new cell above the current."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.add_cell_above()

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _add_cell_below() -> "None":
        """Add a new cell below the current."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.add_cell_below()

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _delete_cells() -> "None":
        """Delete the current cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.delete()

    @staticmethod
    @add_cmd(
        menu_title="Undo delete cell",
        filter=notebook_has_focus
        & ~buffer_has_focus
        & ~display_has_focus
        & deleted_cells,
    )
    def _undelete_cells() -> "None":
        """Undelete the last deleted cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.undelete()

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _cut_cells() -> "None":
        """Cut the current cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.cut()

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _copy_cells() -> "None":
        """Copy the current cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.copy()

    @staticmethod
    @add_cmd(
        menu_title="Copy cell outputs",
        filter=cell_has_focus & ~buffer_has_focus,
    )
    def _copy_outputs() -> "None":
        """Copy the cell's output to the clipboard."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.copy_outputs()

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _paste_cells() -> "None":
        """Paste the previously copied cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.paste()

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus
        & ~buffer_has_focus
        & ~display_has_focus
        & multiple_cells_selected,
    )
    def _merge_cells() -> "None":
        """Merge the selected cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.merge()

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    @add_cmd(
        filter=notebook_has_focus,
    )
    def _scroll_up() -> "NotImplementedOrNone":
        """Scroll the page up a line."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            return nb.page.scroll(1)
        return None

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    @add_cmd(
        filter=notebook_has_focus,
    )
    def _scroll_down() -> "NotImplementedOrNone":
        """Scroll the page down a line."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            return nb.page.scroll(-1)
        return None

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _scroll_up_5_lines() -> "None":
        """Scroll the page up 5 lines."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.page.scroll(5)

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _scroll_down_5_lines() -> "None":
        """Scroll the page down 5 lines."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.page.scroll(-5)

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _select_first_cell() -> "None":
        """Select the first cell in the notebook."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.select(0)

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _select_5th_previous_cell() -> "None":
        """Go up 5 cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.select(nb.page.selected_slice.start - 5)

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _select_previous_cell() -> "None":
        """Go up one cell."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.select(nb.page.selected_slice.start - 1)

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _select_next_cell() -> "None":
        """Select the next cell."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.select(nb.page.selected_slice.start + 1)

    @staticmethod
    @add_cmd(
        filter=~buffer_has_focus,
    )
    def _select_5th_next_cell() -> "None":
        """Go down 5 cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.select(nb.page.selected_slice.start + 5)

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _select_last_cell() -> "None":
        """Select the last cell in the notebook."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.select(len(nb.page.children))

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _select_all_cells() -> "None":
        """Select all cells in the notebook."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.page.selected_slice = slice(
                0,
                len(nb.page.children) + 1,
            )

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _extend_cell_selection_to_top() -> "None":
        """Extend the cell selection to the top of the notebook."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.select(0, extend=True)

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _extend_cell_selection_up() -> "None":
        """Extend the cell selection up a cell."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.select(nb.page._selected_slice.start - 1, extend=True)

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _extend_cell_selection_down() -> "None":
        """Extend the cell selection down a cell."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.select(nb.page._selected_slice.start + 1, extend=True)

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _extend_cell_selection_to_bottom() -> "None":
        """Extend the cell selection to the bottom of the notebook."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.select(len(nb.json["cells"]) - 1, extend=True)

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _move_cells_up() -> "None":
        """Move selected cells up."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.move(-1)

    @staticmethod
    @add_cmd(
        filter=notebook_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _move_cells_down() -> "None":
        """Move selected cells down."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.move(1)

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
    )
    def _cells_to_markdown() -> "None":
        """Change selected cells to markdown cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            for cell in nb.cells:
                cell.set_cell_type("markdown", clear=True)

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
    )
    def _cells_to_code() -> "None":
        """Change selected cells to code cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            for cell in nb.cells:
                cell.set_cell_type("code", clear=False)

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
    )
    def _cells_to_raw() -> "None":
        """Change selected cells to raw cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            for cell in nb.cells:
                cell.set_cell_type("raw", clear=True)

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
    )
    def _clear_cell_outputs() -> "None":
        """Clear the outputs of the selected cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            for cell in nb.cells:
                cell.remove_outputs()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
    )
    def _clear_all_outputs() -> "None":
        """Clear the outputs of the selected cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            for cell in nb._rendered_cells.values():
                cell.remove_outputs()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
        title="Expand cell inputs",
    )
    def _show_cell_inputs() -> "None":
        """Expand the selected cells' inputs."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            for cell in nb.cells:
                cell.show_input()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
        title="Collapse cell inputs",
    )
    def _hide_cell_inputs() -> "None":
        """Collapse the selected cells' inputs."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            for cell in nb.cells:
                cell.hide_input()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
    )
    def _toggle_cell_inputs() -> "None":
        """Toggle the visibility of the selected cells' inputs."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            for cell in nb.cells:
                cell.toggle_input()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
        title="Expand cell outputs",
    )
    def _show_cell_outputs() -> "None":
        """Expand the selected cells' outputs."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            for cell in nb.cells:
                cell.show_output()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
        title="Collapse cell outputs",
    )
    def _hide_cell_outputs() -> "None":
        """Collapse the selected cells' outputs."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            for cell in nb.cells:
                cell.hide_output()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
    )
    def _toggle_cell_outputs() -> "None":
        """Toggle the visibility of the selected cells' outputs."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            for cell in nb.cells:
                cell.toggle_output()

    @staticmethod
    @add_cmd(
        title="Reformat cells",
        filter=have_formatter
        & code_cell_selected
        & kernel_is_python
        & cell_has_focus
        & ~buffer_has_focus,
    )
    def _reformat_cells() -> "None":
        """Format the selected code cells."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            for cell in nb.cells:
                if cell.cell_type == "code":
                    cell.reformat()

    @staticmethod
    @add_cmd(
        filter=have_formatter
        & kernel_is_python
        & notebook_has_focus
        & ~buffer_has_focus,
    )
    def _reformat_notebook() -> "None":
        """Automatically reformat all code cells in the notebook."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.reformat()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
    )
    async def _edit_in_external_editor() -> "None":
        """Edit cell in $EDITOR."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            await nb.cell.edit_in_editor()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & buffer_has_focus,
    )
    def _split_cell() -> "None":
        """Split the current cell at the cursor position."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.split_cell()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus
        & buffer_has_focus
        & cursor_on_first_line
        & ~has_completions,
    )
    def _edit_previous_cell() -> "None":
        """Move the cursor up to the previous cell."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            new_index = nb.cell.index - 1
            cells = nb.rendered_cells()
            if 0 <= new_index < len(cells):
                nb.select(index=new_index, position=-1, scroll=True)

    @staticmethod
    @add_cmd(
        filter=cell_has_focus
        & buffer_has_focus
        & cursor_on_last_line
        & ~has_completions,
    )
    def _edit_next_cell() -> "None":
        """Move the cursor down to the next cell."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            new_index = nb.cell.index + 1
            cells = nb.rendered_cells()
            if 0 <= new_index < len(cells):
                nb.select(index=new_index, position=0, scroll=True)

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
    )
    def _scroll_output_left() -> "None":
        """Scroll the cell output to the left."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.cell.output_area.scroll_left()

    @staticmethod
    @add_cmd(
        filter=cell_has_focus & ~buffer_has_focus,
    )
    def _scroll_output_right() -> "None":
        """Scroll the cell output to the right."""
        nb = get_app().tab
        if isinstance(nb, Notebook):
            nb.cell.output_area.scroll_right()

    @staticmethod
    @add_cmd(
        filter=kernel_tab_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _interrupt_kernel() -> "None":
        """Interrupt the notebook's kernel."""
        if isinstance(kt := get_app().tab, KernelTab):
            kt.interrupt_kernel()

    @staticmethod
    @add_cmd(
        filter=kernel_tab_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _restart_kernel() -> "None":
        """Restart the notebook's kernel."""
        if isinstance(kt := get_app().tab, KernelTab):
            kt.restart_kernel()

    @staticmethod
    @add_cmd(
        filter=kernel_tab_has_focus & ~buffer_has_focus & ~display_has_focus,
    )
    def _restart_kernel_and_clear_all_outputs() -> "None":
        """Restart the notebook's kernel and clear all cell output."""
        if isinstance(nb := get_app().tab, Notebook):
            nb.restart_kernel(cb=Notebook._clear_all_outputs)

    @staticmethod
    @add_cmd(
        filter=~buffer_has_focus,
    )
    def _notebook_toggle_line_numbers() -> "None":
        """Toggles line numbers when a buffer does not have focus."""
        get_cmd("toggle-line-numbers").run()

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.notebook.tabs.notebook.Notebook": {
                "save-notebook": "c-s",
                "enter-cell-edit-mode": "enter",
                "exit-edit-mode": "escape",
                "run-selected-cells": ["c-enter", "c-e"],
                "run-and-select-next": ["s-enter", "c-r"],
                "run-cell-and-insert-below": ("escape", "enter"),
                "add-cell-above": "a",
                "add-cell-below": "b",
                "delete-cells": ("d", "d"),
                "undelete-cells": "z",
                "cut-cells": "x",
                "copy-cells": "c",
                "copy-outputs": ("escape", "c"),
                "paste-cells": "v",
                "interrupt-kernel": ("i", "i"),
                "restart-kernel": ("0", "0"),
                "scroll-up": ["[", "<scroll-up>"],
                "scroll-down": ["]", "<scroll-down>"],
                "scroll-up-5-lines": "{",
                "scroll-down-5-lines": "}",
                "select-first-cell": ["home", "c-up"],
                "select-5th-previous-cell": "pageup",
                "select-previous-cell": ["up", "k"],
                "select-next-cell": ["down", "j"],
                "select-5th-next-cell": "pagedown",
                "select-last-cell": ["end", "c-down"],
                "select-all-cells": "c-a",
                "extend-cell-selection-to-top": "s-home",
                "extend-cell-selection-up": ["s-up", "K"],
                "extend-cell-selection-down": ["s-down", "J"],
                "extend-cell-selection-to-bottom": "s-end",
                "move-cells-up": ("escape", "up"),
                "move-cells-down": ("escape", "down"),
                "cells-to-markdown": "m",
                "cells-to-code": "y",
                "cells-to-raw": "r",
                "reformat-cells": "f",
                "reformat-notebook": "F",
                "edit-in-external-editor": "e",
                "merge-cells": "M",
                "split-cell": "c-\\",
                "edit-previous-cell": "up",
                "edit-next-cell": "down",
                "scroll-output-left": "left",
                "scroll-output-right": "right",
                "toggle-expand": "w",
                "notebook-toggle-line-numbers": "l",
                "reset-tab": "f5",
            }
        }
    )
