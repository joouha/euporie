"""Contains the main class for a notebook file."""

from __future__ import annotations

import copy
import logging
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

import nbformat  # type: ignore
from prompt_toolkit.auto_suggest import DummyAutoSuggest
from prompt_toolkit.completion import DummyCompleter
from prompt_toolkit.filters import Condition, to_filter
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.mouse_events import MouseEventType
from prompt_toolkit.widgets import Box, Label, RadioList

from euporie.app.current import get_tui_app as get_app
from euporie.box import BorderLine, Pattern
from euporie.cell import Cell, InteractiveCell, get_cell_id
from euporie.completion import KernelCompleter
from euporie.config import config
from euporie.containers import PrintingContainer
from euporie.kernel import NotebookKernel
from euporie.key_binding.bindings.commands import load_command_bindings
from euporie.output.container import CellOutput
from euporie.scroll import ScrollbarControl, ScrollingContainer
from euporie.suggest import KernelAutoSuggest
from euporie.tab import Tab

if TYPE_CHECKING:
    from collections.abc import MutableSequence
    from typing import Callable, Optional, Sequence, Type

    from prompt_toolkit.auto_suggest import AutoSuggest
    from prompt_toolkit.completion import Completer
    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.mouse_events import MouseEvent

    from euporie.app.base import EuporieApp
    from euporie.app.tui import TuiApp
    from euporie.cell import PagerState

__all__ = ["Notebook"]

log = logging.getLogger(__name__)

KERNEL_STATUS_REPR = {
    "stopped": "⨂",
    "starting": "◍",
    "idle": "○",
    "busy": "●",
    "error": "☹",
}


class Notebook(Tab, metaclass=ABCMeta):
    """The main notebook container class."""

    def __init__(
        self,
        path: "Path",
        app: "Optional[EuporieApp]" = None,
    ):
        """Instantiate a Notebook container, using a notebook at a given path."""
        super().__init__()
        self.path: "Path" = Path(path).expanduser()
        self.completer: "Completer" = DummyCompleter()
        self.suggester: "AutoSuggest" = DummyAutoSuggest()

        log.debug("Loading notebooks %s", self.path)

        # Open json file
        if self.path.exists():
            self.json = nbformat.read(self.path, as_version=4)
        else:
            self.json = nbformat.v4.new_notebook()
        # Ensure there is always at least one cell
        if not self.json.setdefault("cells", []):
            self.json["cells"] = [nbformat.v4.new_code_cell()]

        self.app = app or get_app()
        self._rendered_cells: "dict[str, Cell]" = {}
        self.cell_type: "Type[Cell]" = Cell

        self.edit_mode = False
        self.in_edit_mode = Condition(lambda: self.edit_mode)

        self.pager_visible = to_filter(False)

    def refresh(
        self, slice_: "Optional[slice]" = None, scroll: "bool" = True
    ) -> "None":
        """Refresh the notebook display."""
        return None

    @property
    def title(self) -> "str":
        """Return the tab title."""
        return ("* " if self.dirty else "") + self.path.name

    def lang_file_ext(self) -> "str":
        """Return the file extension for scripts in the notebook's language."""
        return (
            self.json.get("metadata", {})
            .get("language_info", {})
            .get("file_extension", ".py")
        )

    def rendered_cells(self) -> "list[Cell]":
        """Return a list of `Cell` generator functions for the notebooks' cells."""
        cells = {}
        for i, cell_json in enumerate(self.json.get("cells", [])):
            cell_id = get_cell_id(cell_json)
            if cell_id in self._rendered_cells:
                cells[cell_id] = self._rendered_cells[cell_id]
                cells[cell_id].index = i
            else:
                # Pytype doesn't like this..
                cells[cell_id] = self.cell_type(i, cell_json, self)  # type: ignore
        # Clean up graphic floats from deleted cells
        for cell in set(self._rendered_cells.values()) - set(cells.values()):
            cell.remove_output_graphic_floats()
        self._rendered_cells = cells
        return list(self._rendered_cells.values())

    def get_cell_by_id(self, cell_id: "str") -> "Optional[Cell]":
        """Returns a reference to the `Cell` container with a given cell id."""
        for cell in self._rendered_cells.values():
            if cell.id == cell_id:
                break
        else:
            return None
        return cell

    def add(self, index: "int") -> "None":
        """Creates a new cell at a given index.

        Args:
            index: The position at which to insert a new cell

        """
        self.json["cells"].insert(
            index,
            nbformat.v4.new_code_cell(),
        )
        self.dirty = True

    def move(self, n: "int", slice_: "Optional[slice]" = None) -> "None":
        """Move a slice of cells up or down.

        Args:
            slice_: A slice describing the cell indices to move
            n: The amount to move them by

        """
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

    def select(
        self,
        cell_index: "int",
        extend: "bool" = False,
        position: "Optional[int]" = None,
    ) -> "None":
        """Selects a cell or adds it to the selection.

        Args:
            cell_index: The index of the cell to select
            extend: If true, the selection will be extended to include the cell
            position: An optional cursor position index to apply to the cell input

        """
        pass

    def copy(self, slice_: "slice") -> "None":
        """Add a copy of this cell to the `Notebook`'s clipboard."""
        indices = range(*slice_.indices(len(self.json["cells"])))
        self.clipboard = copy.deepcopy(
            # Sort clipboard contents by index)
            [
                x
                for _, x in sorted(
                    zip(indices, self.json["cells"][slice_]), key=lambda x: x[0]
                )
            ]
        )

    def delete(self, slice_: "Optional[slice]" = None) -> "None":
        """Delete a cell from the notebook."""
        if slice_ is not None:
            index = min(range(*slice_.indices(len(self.json["cells"]))))
            del self.json["cells"][slice_]
            # Ensure there is always one cell
            if len(self.json["cells"]) == 0:
                self.add(1)
            self.dirty = True
            self.refresh(slice(index, index + 1), scroll=True)

    def cut(self, slice_: "slice") -> "None":
        """Remove a cell from the notebook and add it to the `Notebook`'s clipboard."""
        self.copy(slice_)
        self.delete(slice_)

    def paste(self, index: "int") -> "None":
        """Append the contents of the `Notebook`'s clipboard below the first selected cell."""
        cell_jsons: "MutableSequence" = copy.deepcopy(self.clipboard)
        # Assign a new cell IDs
        for cell_json in cell_jsons:
            cell_json["id"] = nbformat.v4.new_code_cell().get("id")
        self.json["cells"][index + 1 : index + 1] = cell_jsons
        self.dirty = True
        # Only change the selected cell if we actually pasted something
        if cell_jsons:
            self.refresh(slice(index + 1, index + 1 + len(cell_jsons)))

    def merge(self, slice_: "Optional[slice]" = None) -> "None":
        """Merge two or more cells."""
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
                self.dirty = True

    def split_cell(self, cell: "Cell", cursor_position: "int") -> "None":
        """Splits a cell into two at the given cursor position.

        Args:
            cell: The rendered cell to split
            cursor_position: The position at which to split the cell

        """
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

    def save(self) -> "None":
        """Write the notebook's JSON to the current notebook's file."""
        log.debug("Saving notebook..")
        self.saving = True
        self.app.invalidate()
        nbformat.write(nb=nbformat.from_dict(self.json), fp=self.path)
        self.dirty = False
        self.saving = False
        self.app.invalidate()
        log.debug("Notebook saved")

    def run_cell(self, cell: "Cell", wait: "bool" = False) -> "None":
        """Runs a cell in the notebook."""
        pass

    def hide_pager(self) -> "None":
        """Closes the pager."""
        pass

    def enter_edit_mode(self) -> "None":
        """Enter cell edit mode."""
        self.edit_mode = True

    def exit_edit_mode(self) -> "None":
        """Leave cell edit mode."""
        self.edit_mode = False


class DumpNotebook(Notebook):
    def __init__(
        self,
        path: "Path",
        app: "Optional[EuporieApp]" = None,
    ):
        super().__init__(path, app)
        self.container = VSplit(
            [
                Window(),
                PrintingContainer(self.rendered_cells, width=config.max_notebook_width),
                Window(),
            ],
        )


class KernelNotebook(Notebook):

    kernel: "NotebookKernel"

    def __init__(
        self,
        path: "Path",
        app: "Optional[EuporieApp]" = None,
    ):
        super().__init__(path, app)
        self.autoran = False
        self.load_kernel()
        self.completer = KernelCompleter(self.kernel)
        self.suggester = KernelAutoSuggest(self.kernel)
        self.dirty = False

    @abstractmethod
    def load_kernel(self) -> "None":
        ...

    def interrupt_kernel(self) -> "None":
        """Interrupt the current `Notebook`'s kernel."""
        assert self.kernel is not None
        self.kernel.interrupt()

    @property
    def kernel_name(self) -> "str":
        """Return the name of the kernel defined in the notebook JSON."""
        return self.json.get("metadata", {}).get("kernelspec", {}).get("name")

    @property
    def kernel_display_name(self) -> "str":
        """Return the display name of the kernel defined in the notebook JSON."""
        return (
            self.json.get("metadata", {}).get("kernelspec", {}).get("display_name", "")
        )

    def run_cell(self, cell: "Cell", wait: "bool" = False) -> "None":
        """Runs a cell.

        Args:
            cell: The rendered cell to run. If ``None``, runs the currently
                selected cell.
            wait: If :py:const:`True`, blocks until cell execution is finished

        """
        cell.clear_output()
        self.dirty = True
        self.kernel.run(
            cell.json,
            output_cb=cell.on_output,
            done_cb=cell.ran,
            wait=wait,
        )

    def reformat(self) -> "None":
        """Reformat all code cells in the notebooks."""
        for cell in self.rendered_cells():
            if cell.cell_type == "code":
                cell.reformat()

    def run_all(self, wait: "bool" = False) -> "None":
        """Run all cells."""
        if self.kernel:
            log.debug("Running all cells (wait=%s)", wait)
            for cell in self.rendered_cells():
                if cell.json.get("cell_type") == "code":
                    log.debug("Running cell %s", cell.id)
                    cell.run_or_render(wait=wait)
            log.debug("All cells run")

    def _process_kernel_info(self, info: "dict") -> "None":
        self.json.setdefault("metadata", {})["language_info"] = info.get(
            "language_info", {}
        )

    def check_kernel(self, result: "None" = None) -> "None":
        log.debug("Kernel status is '%s'", self.kernel.status)
        self.kernel.info(cb=self._process_kernel_info, wait=False)


class DumpKernelNotebook(DumpNotebook, KernelNotebook):
    def check_kernel(self, result: "None" = None) -> "None":
        super().check_kernel()
        if self.kernel.status == "idle" and config.run:
            self.autoran = True
            log.debug("Notebook was set to autorun: running all cells")
            self.run_all(wait=True)

    def load_kernel(self) -> "None":
        self.kernel = NotebookKernel(str(self.kernel_name), threaded=True)
        self.kernel.start(cb=self.check_kernel, wait=True)

    def close(self, cb: "Optional[Callable]") -> "None":
        """Shutdown the kernel and close the notebook.

        Args:
            cb: A callback to run if after closing the notebook.

        """
        log.debug("Closing notebook '%s'", self.path.name)
        self.kernel.stop(wait=False)
        self.kernel.shutdown()
        if callable(cb):
            cb()


class TuiNotebook(KernelNotebook):

    app: "TuiApp"

    def __init__(
        self,
        path: "Path",
        app: "Optional[EuporieApp]" = None,
    ):
        super().__init__(path, app)

        self.clipboard: "list[Cell]" = []
        self.saving = False

        self.pager_state: "Optional[PagerState]" = None
        self.pager_visible = Condition(
            lambda: self.pager_state is not None
            and bool(self.pager_state.response.get("found"))
        )
        self.pager_content = CellOutput({})

        self.cell_type = InteractiveCell
        self.page = ScrollingContainer(
            self.rendered_cells, width=config.max_notebook_width
        )
        # Wrap the scrolling container in an hsplit and apply the keybindings
        expand = Condition(lambda: config.expand)

        self.container = HSplit(
            [
                VSplit(
                    [
                        ConditionalContainer(
                            VSplit(
                                [
                                    Pattern(),
                                    BorderLine(
                                        width=1,
                                        collapse=True,
                                        style="class:notebook.border",
                                    ),
                                    BorderLine(
                                        char=" ",
                                        width=1,
                                        collapse=True,
                                        style="class:notebook.border",
                                    ),
                                ]
                            ),
                            filter=~expand,
                        ),
                        self.page,
                        ConditionalContainer(
                            VSplit(
                                [
                                    BorderLine(
                                        char=" ",
                                        width=1,
                                        collapse=True,
                                        style="class:notebook.border",
                                    ),
                                    BorderLine(
                                        width=1,
                                        collapse=True,
                                        style="class:notebook.border",
                                    ),
                                    Pattern(),
                                ]
                            ),
                            filter=~expand,
                        ),
                        Window(
                            ScrollbarControl(self.page),
                            width=1,
                            style="class:scrollbar",
                        ),
                    ],
                    height=Dimension(weight=2),
                    key_bindings=load_command_bindings("notebook", "cell"),
                ),
                ConditionalContainer(
                    HSplit(
                        [
                            BorderLine(
                                height=1, collapse=False, style="class:pager.border"
                            ),
                            Box(
                                DynamicContainer(self.get_pager_content),
                                padding=0,
                                padding_left=1,
                            ),
                        ],
                        height=Dimension(weight=1),
                        style="class:pager",
                        key_bindings=load_command_bindings("pager"),
                    ),
                    filter=self.pager_visible,
                ),
            ],
        )

    def get_pager_content(self) -> "CellOutput":
        """Returns the rendered pager content."""
        if (
            self.pager_state is not None
            and self.pager_content.json is not self.pager_state.response
        ):
            self.pager_content = CellOutput(
                self.pager_state.response,
                show_scrollbar=True,
                focusable=True,
                focus_on_click=True,
                wrap_lines=True,
                style="class:pager",
            )
        return self.pager_content

    def focus_pager(self) -> "None":
        """Focuses the pager."""
        self.app.layout.focus(self.pager_content)

    def hide_pager(self) -> "None":
        """Closes the pager."""
        self.pager_state = None

    def select(
        self,
        cell_index: "int",
        extend: "bool" = False,
        position: "Optional[int]" = None,
    ) -> "None":
        """Selects a cell or adds it to the selection.

        Args:
            cell_index: The index of the cell to select
            extend: If true, the selection will be extended to include the cell
            position: An optional cursor position index to apply to the cell input

        """
        if extend:
            # indices = self.page.selected_indices
            slice_ = self.page._selected_slice
            stop = -1 if slice_.stop is None else slice_.stop
            step = slice_.step
            if step == -1 and cell_index <= stop:
                stop += 2
                step = 1
            elif step == -1 and cell_index >= stop:
                pass
            elif step in (1, None) and cell_index < stop:
                step = 1
            elif step in (1, None) and cell_index >= stop:
                step = -1
                stop -= 2
            self.page.selected_slice = slice(
                cell_index,
                stop,
                step,
            )
        else:
            self.page.selected_slice = slice(cell_index, cell_index + 1)
        # Focus the selected cell - use the current slice in case it did not change
        self.rendered_cells()[self.page.selected_slice.start].focus(position)

    def enter_edit_mode(self) -> "None":
        """Enter cell edit mode."""
        super().enter_edit_mode()
        self.cell.select()

    def exit_edit_mode(self) -> "None":
        """Leave cell edit mode."""
        super().exit_edit_mode()
        self.cell.select()

    def refresh(
        self, slice_: "Optional[slice]" = None, scroll: "bool" = True
    ) -> "None":
        """Refresh the rendered contents of this notebook."""
        if slice_ is None:
            slice_ = self.page._selected_slice
        self.page.reset()
        self.page._set_selected_slice(slice_, force=True, scroll=scroll)

    def add_cell_above(self) -> "None":
        index = self.page.selected_slice.start + 0
        self.add(index)
        self.refresh(slice_=slice(index, index + 1), scroll=False)

    def add_cell_below(self) -> "None":
        index = self.page.selected_slice.start + 1
        self.add(index)
        self.refresh(slice_=slice(index, index + 1), scroll=True)

    @property
    def cell(self) -> "InteractiveCell":
        """Returns the currently selected `Cell` in this `Notebook`."""
        cell = self.page.get_child()
        assert isinstance(cell, InteractiveCell)
        return cell

    @property
    def cells(self) -> "Sequence[Cell]":
        """Returns the currently selected `Cells` in this `Notebook`."""
        return self.page.children[self.page.selected_slice]

    def change_kernel(self, msg: "Optional[str]" = None) -> None:
        """Displays a dialog for the user to select a new kernel."""

        def _change_kernel_cb() -> None:
            assert self.kernel is not None
            name = options.current_value
            self.kernel.change(name, self.json.setdefault("metadata", {}))

        assert self.kernel is not None
        kernel_specs = self.kernel.specs
        options = RadioList(
            [
                (
                    kernel_name,
                    kernel_spec.get("spec", {}).get("display_name", kernel_name),
                )
                for kernel_name, kernel_spec in kernel_specs.items()
            ]
        )
        self.app.dialog(
            title="Select Kernel",
            body=HSplit(
                [
                    Label((f"{msg}\n" if msg else "") + "Please select a kernel:\n"),
                    options,
                ]
            ),
            buttons={
                "Select": _change_kernel_cb,
                "Cancel": None,
            },
        )

    def check_kernel(self, result: "None" = None) -> "None":
        """Checks if the kernel has started and prompts user if not."""
        super().check_kernel()
        if self.kernel.missing:
            self.change_kernel(
                msg=f"Kernel '{self.kernel_display_name}' not registered"
            )
        elif self.kernel.status == "error":
            self.app.dialog(
                "Error Starting Kernel",
                Label(self.kernel.error.__repr__()),
                {"OK": None},
            )
        elif self.kernel.status == "idle" and config.run:
            self.run_all(wait=False)

        self.app.invalidate()

    def load_kernel(self) -> "None":
        self.kernel = NotebookKernel(
            str(self.kernel_name), threaded=True, allow_stdin=True
        )
        self.kernel.start(cb=self.check_kernel, wait=False)

    def restart_kernel(self) -> "None":
        """Restarts the current `Notebook`'s kernel."""

        def _do_restart() -> "None":
            assert self.kernel is not None
            self.kernel.restart()

        self.app.dialog(
            "Restart",
            Label("Are you sure you want to restart the kernel?"),
            {"Yes": _do_restart, "No": None},
        )

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
        n_cells = len(self.json["cells"])
        selected_indices = self.page.selected_indices
        rendered_cells = {cell.index: cell for cell in self._rendered_cells.values()}

        # Run the cells
        for i in sorted(selected_indices):
            rendered_cells[i].run_or_render()
        # Insert a cell if we are at the last cell
        index = max(selected_indices)
        if insert or (advance and max(selected_indices) == (n_cells) - 1):
            self.add(index + 1)
            self.refresh(slice_=slice(index + 1, index + 2), scroll=True)
        elif advance:
            self.select(index + 1)

    def run_cell(self, cell: "Cell", wait: "bool" = False) -> "None":
        if cell is None:
            cell = self.cell
        assert isinstance(cell, InteractiveCell)
        cell.clear_output()
        self.dirty = True
        self.kernel.run(
            cell.json,
            stdin_cb=cell.get_input,
            output_cb=cell.on_output,
            done_cb=cell.ran,
            wait=wait,
        )

    def cut(self, slice_: "Optional[slice]" = None) -> "None":
        """Remove cells from the notebook and them to the `Notebook`'s clipboard."""
        if slice_ is None:
            slice_ = self.page.selected_slice
        super().cut(slice_)

    def copy(self, slice_: "Optional[slice]" = None) -> "None":
        """Add a copy of the selected cells to the `Notebook`'s clipboard."""
        if slice_ is None:
            slice_ = self.page.selected_slice
        super().copy(slice_)

    def paste(self, index: "Optional[int]" = None) -> "None":
        """Append the contents of the `Notebook`'s clipboard below the current cell."""
        if index is None:
            index = self.page.selected_slice.start
        super().paste(index)

    def delete(self, slice_: "Optional[slice]" = None) -> "None":
        """Delete a slice of cells from the notebook."""
        if slice_ is None:
            slice_ = self.page.selected_slice
        super().delete(slice_)

    def move(self, n: "int", slice_: "Optional[slice]" = None) -> "None":
        """Move a slice of cells up or down."""
        if slice_ is None:
            slice_ = self.page.selected_slice
        super().move(n, slice_)

    def merge(self, slice_: "Optional[slice]" = None) -> "None":
        """Merge two or more cells."""
        if slice_ is None:
            slice_ = self.page.selected_slice
        super().merge(slice_)

    def really_close(self, cb: "Optional[Callable]") -> "None":
        """Shutdown the kernel and close the notebook.

        Args:
            cb: A callback to run if after closing the notebook.

        """
        log.debug("Closing notebook '%s'", self.path.name)
        self.kernel.stop(wait=False)
        self.kernel.shutdown()
        if callable(cb):
            cb()

    def unsaved(self, cb: "Optional[Callable]") -> "None":
        """Display a dialog prompting the user to save unsaved changes.

        Args:
            cb: A callback to run if after closing the notebook.

        """

        def yes_cb() -> "None":
            self.save()
            self.really_close(cb)

        def no_cb() -> "None":
            self.really_close(cb)

        self.app.dialog(
            title="Unsaved Changes",
            body=Window(
                FormattedTextControl(
                    [
                        ("bold", self.path.name),
                        ("", " has unsaved changes\n"),
                        ("", "Do you want to save your changes?"),
                    ]
                ),
            ),
            buttons={
                "Yes": yes_cb,
                "No": no_cb,
                "Cancel": None,
            },
        )

    def close(self, cb: "Optional[Callable]") -> "None":
        """Check if the user want to save an unsaved notebook, then close the file.

        Args:
            cb: A callback to run if after closing the notebook.

        """
        if self.dirty:
            self.unsaved(cb)
        else:
            self.really_close(cb)

    def _statusbar_kernel_handeler(self, event: "MouseEvent") -> "None":
        """Event handler for kernel name field in statusbar."""
        if event.event_type == MouseEventType.MOUSE_UP:
            self.change_kernel()

    def statusbar_fields(
        self,
    ) -> "tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]":
        """Generates the formatted text for the statusbar."""
        return (
            [
                "^" if self.edit_mode else ">",
                f"Cell {self.page.selected_slice.start+1}",
                "Saving.." if self.saving else "",
            ],
            [
                [("", self.kernel_display_name, self._statusbar_kernel_handeler)],
                KERNEL_STATUS_REPR[self.kernel.status] if self.kernel else ".",
            ],
        )
