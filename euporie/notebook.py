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

        self.pager_visible = to_filter(False)

    def refresh(self, index: "Optional[int]" = None, scroll: "bool" = True) -> "None":
        """Refresh the notebook display."""
        return None

    @property
    def title(self) -> "str":
        """Return the tab title."""
        return self.path.name

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
            else:
                # Pytype doesn't like this...
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

    def copy(self, index: "int") -> "None":
        """Add a copy of this cell to the `Notebook`'s clipboard."""
        self.clipboard = copy.deepcopy(self.json["cells"][index : index + 1])

    def delete(self, index: "Optional[int]" = None) -> "None":
        """Delete a cell from the notebook."""
        # Ensure there is always one cell
        if index is not None:
            if len(self.json["cells"]) == 1:
                self.add(1)
            del self.json["cells"][index]
            self.dirty = True
            self.refresh(max(0, index), scroll=True)

    def cut(self, index: "int") -> "None":
        """Remove a cell from the notebook and add it to the `Notebook`'s clipboard."""
        self.copy(index)
        self.delete(index)

    def paste(self, index: "int") -> "None":
        """Append the contents of the `Notebook`'s clipboard below the current cell."""
        cell_jsons: "MutableSequence" = copy.deepcopy(self.clipboard)
        # Assign a new cell IDs
        for cell_json in cell_jsons:
            cell_json["id"] = nbformat.v4.new_code_cell().get("id")
        self.json["cells"][index + 1 : index + 1] = cell_jsons
        self.dirty = True
        # Only change the selected cell if we actually pasted something
        if cell_jsons:
            self.refresh(index + 1)

    def save(self) -> "None":
        """Write the notebook's JSON to the current notebook's file."""
        log.debug("Saving notebook...")
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


class DumpNotebook(Notebook):
    def __init__(
        self,
        path: "Path",
        app: "Optional[EuporieApp]" = None,
    ):
        super().__init__(path, app)
        self.container = HSplit(
            [
                PrintingContainer(
                    self.rendered_cells,
                    width=config.max_notebook_width,
                )
            ]
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
                    # self.run_cell(cell, wait=wait)
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
        # Wrap the scolling container in an hsplit and apply the keybindings
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

    def refresh(self, index: "Optional[int]" = None, scroll: "bool" = True) -> "None":
        """Refresh the rendered contents of this notebook."""
        if index is None:
            index = self.page.selected_index
        self.page.reset()
        self.page._set_selected_index(index, force=True, scroll=scroll)

    def add_cell_above(self) -> "None":
        index = self.page.selected_index + 0
        self.add(index)
        self.refresh(index=index, scroll=False)

    def add_cell_below(self) -> "None":
        index = self.page.selected_index + 1
        self.add(index)
        self.refresh(index=index, scroll=True)

    @property
    def cell(self) -> "InteractiveCell":
        """Returns the currently selected `Cell` in this `Notebook`."""
        cell = self.page.get_child()
        assert isinstance(cell, InteractiveCell)
        return cell

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

    def cut(self, index: "Optional[int]" = None) -> "None":
        """Remove a cell from the notebook and add it to the `Notebook`'s clipboard."""
        if index is None:
            index = self.page.selected_index
        super().cut(index)

    def copy(self, index: "Optional[int]" = None) -> "None":
        """Add a copy of this cell to the `Notebook`'s clipboard."""
        if index is None:
            index = self.page.selected_index
        super().copy(index)

    def paste(self, index: "Optional[int]" = None) -> "None":
        """Append the contents of the `Notebook`'s clipboard below the current cell."""
        if index is None:
            index = self.page.selected_index
        super().paste(index)

    def delete(self, index: "Optional[int]" = None) -> "None":
        """Delete a cell from the notebook."""
        if index is None:
            index = self.page.selected_index
        super().delete(index)

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
                f"Cell {self.page.selected_index+1}",
                "*" if self.dirty else "",
                "Saving..." if self.saving else "",
            ],
            [
                [("", self.kernel_display_name, self._statusbar_kernel_handeler)],
                KERNEL_STATUS_REPR[self.kernel.status] if self.kernel else ".",
            ],
        )
