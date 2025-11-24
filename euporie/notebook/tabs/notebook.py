"""Contain the main class for a notebook file."""

from __future__ import annotations

import logging
from collections import deque
from copy import deepcopy
from functools import partial
from typing import TYPE_CHECKING, ClassVar
from uuid import uuid4

from prompt_toolkit.clipboard.base import ClipboardData
from prompt_toolkit.filters import (
    Condition,
)
from prompt_toolkit.layout.containers import ConditionalContainer, VSplit
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.mouse_events import MouseEventType

from euporie.core.commands import get_cmd
from euporie.core.filters import (
    insert_mode,
    multiple_cells_selected,
    replace_mode,
)
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.layout.cache import CachedContainer
from euporie.core.layout.decor import Line, Pattern
from euporie.core.layout.mouse import MouseHandlerWrapper
from euporie.core.layout.scroll import ScrollingContainer
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.nbformat import NOTEBOOK_EXTENSIONS, new_code_cell
from euporie.core.style import KERNEL_STATUS_REPR
from euporie.core.tabs.notebook import BaseNotebook
from euporie.core.widgets.cell import Cell

if TYPE_CHECKING:
    from collections.abc import MutableSequence, Sequence
    from pathlib import Path
    from typing import Any

    from prompt_toolkit.formatted_text.base import AnyFormattedText
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.mouse_events import MouseEvent

    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields
    from euporie.core.comm.base import Comm
    from euporie.core.kernel.base import BaseKernel

log = logging.getLogger(__name__)


class Notebook(BaseNotebook):
    """Interactive notebooks.

    A tab which allows running and editing a notebook.
    """

    name = "Notebook Editor"
    weight = 3
    mime_types: ClassVar[set[str]] = {"application/x-ipynb+json"}
    file_extensions: ClassVar[dict[str, None]] = dict.fromkeys(NOTEBOOK_EXTENSIONS)

    allow_stdin = True
    bg_init = True

    def __init__(
        self,
        app: BaseApp,
        path: Path | None = None,
        kernel: BaseKernel | None = None,
        comms: dict[str, Comm] | None = None,
        use_kernel_history: bool = True,
        json: dict[str, Any] | None = None,
    ) -> None:
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
        self.clipboard: list[Cell] = []
        self.undo_buffer: deque[tuple[int, list[Cell]]] = deque(maxlen=10)
        self.default_callbacks["set_next_input"] = self.set_next_input

    # Tab stuff

    def _statusbar_kernel_handler(self, event: MouseEvent) -> NotImplementedOrNone:
        """Event handler for kernel name field in statusbar."""
        if event.event_type == MouseEventType.MOUSE_UP:
            get_cmd("change-kernel").run()
            return None
        else:
            return NotImplemented

    def __pt_status__(self) -> StatusBarFields | None:
        """Generate the formatted text for the statusbar."""
        fields: tuple[list[AnyFormattedText], list[AnyFormattedText]] = (
            ["Saving…" if self.saving else ""],
            [
                [
                    (
                        "",
                        self.kernel_display_name or "No Kernel",
                        self._statusbar_kernel_handler,
                    )
                ],
                KERNEL_STATUS_REPR[self.kernel.status] if self.kernel else ".",
            ],
        )

        if hasattr(self, "page"):
            rendered = self.page.pre_rendered
            fields[0][0:0] = [
                self.mode(),
                f"Cell {self.page.selected_slice.start + 1}",
                f"Rendering… ({rendered:.0%})" if rendered and rendered < 1 else "",
            ]

        return fields

    # Notebook stuff

    def post_init_kernel(self) -> None:
        """Start the kernel after if has been loaded."""
        # Load container
        super().post_init_kernel()

        # Start kernel
        if self.kernel._status == "stopped":
            self.kernel.start(cb=self.kernel_started, wait=False)

    @property
    def selected_indices(self) -> list[int]:
        """Return a list of the currently selected cell indices."""
        return self.page.selected_indices

    def kernel_started(self, result: dict[str, Any] | None = None) -> None:
        """Run when the kernel has started."""
        super().kernel_started(result)

        if self.kernel.status == "idle" and self.app.config.run:
            self.run_all(wait=False)

    def report_kernel_error(self, error: Exception | None) -> None:
        """Report a kernel error to the user."""
        self.app.dialogs["error"].show(exception=error, when="starting the kernel")

    def load_container(self) -> AnyContainer:
        """Trigger loading of the main notebook container."""

        async def _load() -> None:
            # Load notebook file
            self.load()
            # Load and focus container
            prev = self.container
            self.container = self._load_container()
            # Update the focus if the old container had focus
            if self.app.layout.has_focus(prev):
                self.focus()

        self.app.create_background_task(_load())

        return self.container

    def _load_container(self) -> AnyContainer:
        """Actually load the main notebook container."""
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
                    MouseHandlerWrapper(
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
                        self.page.mouse_scroll_handler,
                    ),
                    filter=~expand,
                ),
                self.page,
                ConditionalContainer(
                    MouseHandlerWrapper(
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
                        self.page.mouse_scroll_handler,
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
                "euporie.core.tabs.base:Tab",
                "euporie.notebook.tabs.notebook:Notebook",
                config=self.app.config,
            ),
        )

    @property
    def cell(self) -> Cell:
        """Return the currently selected `Cell` in this `Notebook`."""
        if isinstance(cell := self.page.get_child().content, Cell):
            return cell
        return Cell(0, {}, self)

    # Editing specific stuff

    @property
    def cells(self) -> Sequence[Cell]:
        """Return the currently selected `Cells` in this `Notebook`."""
        return [
            child.content
            for child in self.page.all_children()[self.page.selected_slice]
            if isinstance(child, CachedContainer) and isinstance(child.content, Cell)
        ]

    def check_edit_mode(self) -> bool:
        """Determine if the notebook is (or should be) in edit mode."""
        if self.cell.input_box.has_focus():
            self.edit_mode = True
        return self.edit_mode

    def enter_edit_mode(self) -> None:
        """Enter cell edit mode."""
        # Signal the page to scroll so the cursor is visible on next render
        self.page.scroll_to_cursor = True
        self.edit_mode = True
        # Only one cell can be selected in edit mode
        self.select(self.cell.index)
        self.scroll_to(self.cell.index)

    def exit_edit_mode(self) -> None:
        """Leave cell edit mode."""
        self.edit_mode = False
        # Focus the first selected cell
        self.rendered_cells()[self.page.selected_slice.start].focus(
            self.cell.index, scroll=False
        )

    def mode(self) -> str:
        """Return a symbol representing the current mode.

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
        index: int,
        extend: bool = False,
        position: int | None = None,
        scroll: bool = True,
    ) -> None:
        """Select a cell or adds it to the selection.

        Args:
            index: The index of the cell to select
            extend: If true, the selection will be extended to include the cell
            position: An optional cursor position index to apply to the cell input
            scroll: Whether to scroll the page

        """
        self.page.select(index=index, extend=extend, position=position, scroll=scroll)
        # Focus the selected cell - use the current slice in case it did not change
        self.rendered_cells()[self.page.selected_slice.start].focus(
            position, scroll=False
        )

    def scroll_to(self, index: int) -> None:
        """Scroll to a cell by index."""
        self.page.scroll_to(index)

    def refresh(self, slice_: slice | None = None, scroll: bool = True) -> None:
        """Refresh the rendered contents of this notebook."""
        if slice_ is None:
            slice_ = self.page._selected_slice
        # This triggers another redraw of the selected cell
        self.page._set_selected_slice(slice_, force=True, scroll=scroll)
        self.page.reset()

    def refresh_cell(self, cell: Cell) -> None:
        """Trigger the refresh of a notebook cell."""
        self.page.get_child(cell.index).invalidate()

    def add_cell_above(self) -> None:
        """Inert a cell above the current selection."""
        index = self.page.selected_slice.start + 0
        self.add(index)
        self.refresh(slice_=slice(index, index + 1), scroll=False)

    def add_cell_below(self) -> None:
        """Inert a cell below the current selection."""
        index = self.page.selected_slice.start + 1
        self.add(index)
        self.refresh(slice_=slice(index, index + 1), scroll=True)

    def set_next_input(self, text: str, replace: bool = False) -> None:
        """Handle ``set_next_input`` payloads, e.g. ``%load`` magic."""
        if replace:
            self.cell.input_box.text = text
        else:
            index = self.page.selected_slice.start + 1
            self.add(index, source=text)
            self.refresh(slice_=slice(index, index + 1), scroll=True)

    def cut(self, slice_: slice | None = None) -> None:
        """Remove cells from the notebook and them to the `Notebook`'s clipboard."""
        if slice_ is None:
            slice_ = self.page.selected_slice
        self.copy(slice_)
        self.delete(slice_)

    def copy(self, slice_: slice | None = None) -> None:
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

    def copy_outputs(self, slice_: slice | None = None) -> None:
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

    def paste(self, index: int | None = None) -> None:
        """Append the contents of the `Notebook`'s clipboard below the current cell."""
        if index is None:
            index = self.page.selected_slice.start
        cell_jsons: MutableSequence = deepcopy(self.clipboard)
        # Assign a new cell IDs
        for cell_json in cell_jsons:
            cell_json["id"] = uuid4().hex[:8]
        self.json["cells"][index + 1 : index + 1] = cell_jsons
        self.dirty = True
        # Only change the selected cell if we actually pasted something
        if cell_jsons:
            self.refresh(slice(index + 1, index + 1 + len(cell_jsons)))

    def add(self, index: int, source: str = "", **kwargs: Any) -> None:
        """Create a new cell at a given index.

        Args:
            index: The position at which to insert a new cell
            source: The contents of the new cell
            kwargs: Additional parameters for the cell

        """
        self.json["cells"].insert(
            index,
            new_code_cell(source=source, **kwargs),
        )
        self.dirty = True

    def move(self, n: int, slice_: slice | None = None) -> None:
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
            if index >= 0 and index + len(indices) <= len(self.json["cells"]):
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

    def delete(self, slice_: slice | None = None) -> None:
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

    def undelete(self) -> None:
        """Insert the last deleted cell(s) back into the notebook."""
        if self.undo_buffer:
            index, cells = self.undo_buffer.pop()
            self.json["cells"][index:index] = cells
            self.refresh(slice(index, index + len(cells)))

    def merge(self, slice_: slice | None = None) -> None:
        """Merge two or more cells."""
        if slice_ is None:
            slice_ = self.page.selected_slice
        if slice_ is not None:
            indices = sorted(range(*slice_.indices(len(self.json["cells"]))))
            if len(indices) >= 2:
                # Create a new cell
                new_cell_json = new_code_cell()
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

    def split_cell(self) -> None:
        """Split a cell into two at the cursor position."""
        # Get the current cell
        cell = self.cell
        # Get the cursor position in the cell
        cursor_position = cell.input_box.buffer.cursor_position
        # Reset the cursor position to avoid an error after splitting
        cell.input_box.buffer.cursor_position = 0
        # Get the cell contents
        source = cell.json.get("source", "")
        # Create a new cell
        new_cell_json = new_code_cell()
        # Split the cell contents at the cursor position
        cell.input = source[cursor_position:]
        new_cell_json["source"] = source[:cursor_position]
        # Copy the cell type
        new_cell_json["cell_type"] = cell.json["cell_type"]
        # Add the new cell to the notebook
        self.json["cells"].insert(cell.index, new_cell_json)
        # Refresh the notebook display
        self.refresh()

    def reformat(self) -> None:
        """Reformat all code cells in the notebooks."""
        for cell in self.rendered_cells():
            if cell.cell_type == "code":
                cell.input_box.reformat()

    def run_selected_cells(
        self,
        advance: bool = False,
        insert: bool = False,
    ) -> None:
        """Run the currently selected cells.

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

    def run_all(self, wait: bool = False) -> None:
        """Run all cells."""
        if self.kernel:
            log.debug("Running all cells (wait=%s)", wait)
            for cell in self.rendered_cells():
                if cell.json.get("cell_type") == "code":
                    log.debug("Running cell %s", cell.id)
                    cell.run_or_render(wait=wait)
            log.debug("All cells run")

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.notebook.tabs.notebook:Notebook": {
                "enter-cell-edit-mode": "enter",
                "exit-edit-mode": "escape",
                "run-selected-cells": ["c-enter", "c-e", "c-s-f8"],
                "run-and-select-next": ["s-enter", "c-r", "s-f9"],
                "run-cell-and-insert-below": ("A-enter"),
                "add-cell-above": "a",
                "add-cell-below": "b",
                "delete-cells": ("d", "d"),
                "undelete-cells": "z",
                "cut-cells": "x",
                "copy-cells": "c",
                "copy-outputs": ("A-c"),
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
                "move-cells-up": ("A-up"),
                "move-cells-down": ("A-down"),
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
                "edit-previous-cell-vi": "k",
                "edit-next-cell-vi": "j",
                "scroll-output-left": "left",
                "scroll-output-right": "right",
                "toggle-expand": "w",
                "toggle-wrap-cell-outputs": "W",
                "notebook-toggle-line-numbers": "l",
            }
        }
    )
