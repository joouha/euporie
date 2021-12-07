# -*- coding: utf-8 -*-
"""Contains the main class for a notebook file."""
from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import nbformat  # type: ignore
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.margins import NumberedMargin
from prompt_toolkit.mouse_events import MouseEventType
from prompt_toolkit.widgets import Label, RadioList

from euporie.box import BorderLine, Pattern
from euporie.cell import Cell, get_cell_id
from euporie.completion import KernelCompleter
from euporie.config import config
from euporie.containers import PrintingContainer
from euporie.kernel import NotebookKernel
from euporie.keys import KeyBindingsInfo
from euporie.scroll import ScrollBar, ScrollingContainer
from euporie.suggest import KernelAutoSuggest
from euporie.tab import Tab

if TYPE_CHECKING:
    from typing import Callable, Optional, cast

    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.mouse_events import MouseEvent

    from euporie.app import App

__all__ = ["Notebook"]

log = logging.getLogger(__name__)

KERNEL_STATUS_REPR = {
    "stopped": "⨂",
    "starting": "◍",
    "idle": "○",
    "busy": "●",
    "error": "☹",
}


class Notebook(Tab):
    """The main notebook container class."""

    def __init__(
        self,
        path: "Path",
        interactive: "bool" = True,
        autorun: "bool" = False,
        scroll: "bool" = False,
        app: "Application" = None,
    ):
        """Instantiate a Notebook container, using a notebook at a given path."""
        self.path = Path(path).expanduser()
        self.interactive = interactive
        self.autorun = autorun
        self.autoran = False
        self.scroll = scroll
        self.completer = None
        self.suggester = None

        log.debug(
            "Loading notebooks %s, interactive=%s, autorun=%s, scroll=%s",
            self.path,
            self.interactive,
            self.autorun,
            self.scroll,
        )

        # Open json file
        if self.path.exists():
            self.json = nbformat.read(self.path, as_version=4)
        else:
            self.json = nbformat.v4.new_notebook()
        # Ensure there is always at least one cell
        if not self.json.setdefault("cells", []):
            self.json["cells"] = [nbformat.v4.new_code_cell()]

        self.clipboard: "list[Cell]" = []
        self.dirty = False
        self.line_numbers = config.line_numbers

        self.container: "AnyContainer"

        self.app = app or cast("App", get_app())

        self._rendered_cells = {}

        # Set up kernel if we're going to need it
        self.kernel = None

        # Set up the kernel
        if self.interactive or self.autorun:
            self.kernel = NotebookKernel(
                str(self.kernel_name), threaded=not self.interactive
            )
            self.kernel.start(cb=self.check_kernel, wait=not self.interactive)
            # Don't load the kernel completer if it won't be needed
            if self.interactive:
                self.completer = KernelCompleter(self.kernel)
                self.suggester = KernelAutoSuggest(self.kernel)

        # Set up container
        if not self.scroll:
            self.container = PrintingContainer(
                self.rendered_cells,
                width=config.max_notebook_width,
            )

        else:
            self.page = ScrollingContainer(
                self.rendered_cells, width=config.max_notebook_width
            )
            # Wrap the scolling container in an hsplit and apply the keybindings
            self.container = VSplit(
                [
                    VSplit(
                        [
                            Pattern(),
                            BorderLine(width=1, collapse=True),
                            BorderLine(char=" ", width=1, collapse=True),
                            self.page,
                            BorderLine(char=" ", width=1, collapse=True),
                            BorderLine(width=1, collapse=True),
                            Pattern(),
                        ]
                    ),
                    Window(ScrollBar(self.page), width=1, style="class:scrollbar"),
                ],
                key_bindings=self.load_key_bindings(),
            )

    def check_kernel(self, result: "None" = None) -> "None":
        """Checks if the kernel has started and prompts user if not."""
        assert self.kernel is not None
        status = self.kernel.status
        log.debug("Kernel status is '%s'", status)
        if self.kernel.missing:
            self.change_kernel(
                msg=f"Kernel '{self.kernel_display_name}' not registered"
            )
        elif status == "error":
            self.app.dialog(
                "Error Starting Kernel",
                Label(self.kernel.error.__repr__()),
                {"OK": None},
            )
        elif status == "idle" and self.autorun and not self.autoran:
            self.autoran = True
            log.debug("Notebook was set to autorun: running all cells")
            self.run_all(wait=not self.interactive)

        self.app.invalidate()

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

    def rendered_cells(self) -> "list[Cell]":
        """Return a list of `Cell` generator functions for the notebooks' cells."""
        cells = {}
        for i, cell_json in enumerate(self.json.get("cells", [])):
            cell_id = get_cell_id(cell_json)
            if cell_id in self._rendered_cells:
                cells[cell_id] = self._rendered_cells[cell_id]
            else:
                cells[cell_id] = Cell(i, cell_json, self)
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

    def load_key_bindings(self) -> "KeyBindings":
        """Load the key bindings associate with a `Notebook` container."""
        kb = KeyBindingsInfo()

        if config.debug:

            @kb.add("?", group="Application", desc="Save current file")
            def debug(event: "KeyPressEvent") -> "None":
                log.debug(
                    "Kernel Report:\n- Status: %s\n- ID: %s\n- Missing: %s\n- Events: %s",
                    self.kernel.status,
                    self.kernel.id,
                    self.kernel.missing,
                    self.kernel.events,
                )
                self.check_kernel()

        @kb.add("c-s", group="Application", desc="Save current file")
        def save(event: "KeyPressEvent") -> "None":
            self.save()

        @kb.add("a", group="Notebook", desc="Add new cell above current")
        def add_above(event: "KeyPressEvent") -> "None":
            self.add(0)

        @kb.add("b", group="Notebook", desc="Add new cell below current")
        def add_below(event: "KeyPressEvent") -> "None":
            self.add(1)

        @kb.add("d", "d", group="Notebook", desc="Delete current cell")
        def delete(event: "KeyPressEvent") -> "None":
            self.delete()

        @kb.add("x", group="Notebook", desc="Cut current cell")
        def cut(event: "KeyPressEvent") -> "None":
            self.cut()

        @kb.add("c", group="Notebook", desc="Copy current cell")
        def copy(event: "KeyPressEvent") -> "None":
            self.copy()

        @kb.add("v", group="Notebook", desc="Paste copied cell")
        def paste(event: "KeyPressEvent") -> "None":
            self.paste()

        @kb.add("m", group="Notebook", desc="Change cell to markdown")
        def to_markdown(event: "KeyPressEvent") -> "None":
            self.cell.set_cell_type("markdown")
            self.cell.clear_output()

        @kb.add("y", group="Notebook", desc="Change cell to code")
        def to_code(event: "KeyPressEvent") -> "None":
            self.cell.set_cell_type("code")

        @kb.add("r", group="Notebook", desc="Change cell to raw")
        def to_raw(event: "KeyPressEvent") -> "None":
            self.cell.set_cell_type("raw")
            self.cell.clear_output()

        @kb.add("l", group="Notebook", desc="Toggle line numbers")
        def line_nos(event: "KeyPressEvent") -> "None":
            self.line_numbers = not self.line_numbers
            for cell in self.rendered_cells:
                assert isinstance(cell, Cell)
                cell.input_box.window.left_margins = (
                    [NumberedMargin()] if self.line_numbers else []
                )

        @kb.add("I", "I", group="Notebook", desc="Interrupt notebook kernel")
        def interrupt(event: "KeyPressEvent") -> "None":
            self.interrupt_kernel()

        @kb.add("0", "0", group="Notebook", desc="Restart notebook kernel")
        def restart(event: "KeyPressEvent") -> "None":
            self.restart_kernel()

        return kb

    @property
    def cell(self) -> "Cell":
        """Returns the currently selected `Cell` in this `Notebook`."""
        cell = self.page.get_child()
        assert isinstance(cell, Cell)
        return cell

    def is_cell_obscured(self, index: "int") -> "bool":
        """Determine if a cell is partially visible.

        Args:
            index: The index of the child of interest.

        Returns:
            True if the child is rendered and partially off-screen, otherwise False

        """
        if self.scroll:
            return self.page.is_child_obscured(index)
        else:
            return False

    def run_cell(self, cell: "Cell", wait: "bool" = False) -> "None":
        """Runs a cell.

        Args:
            cell: The rendered cell to run. If ``None``, runs the currently
                selected cell.
            wait: If :py:const:`True`, blocks until cell execution is finished

        """
        if self.kernel:
            if cell is None:
                cell = self.cell
            cell.clear_output()
            self.kernel.run(
                cell.json, output_cb=cell.on_output, done_cb=cell.ran, wait=wait
            )

    def run_all(self, wait: "bool" = False) -> None:
        """Run all cells."""
        log.debug("Running all cells (wait=%s)", wait)
        for cell in self.rendered_cells():
            log.debug("Running cell %s", cell.id)
            self.run_cell(cell, wait=wait)
        log.debug("All cells run")

    def add(self, offset: "int") -> "None":
        """Creates a new cell at a given offset from the currently selected cell.

        Args:
            offset: How many cells above (negative) or below (positive) the current
                cell the new cell should be placed.

        """
        index = self.page.selected_index + offset
        self.json["cells"].insert(
            index,
            nbformat.v4.new_code_cell(),
        )
        self.dirty = True
        self.refresh(index=index)

    def cut(self, index: "Optional[int]" = None) -> "None":
        """Remove a cell from the notebook and add it to the `Notebook`'s clipboard."""
        if index is None:
            index = self.page.selected_index
        self.copy(index)
        self.delete(index)

    def copy(self, index: "Optional[int]" = None) -> "None":
        """Add a copy of this cell to the `Notebook`'s clipboard."""
        if index is None:
            index = self.page.selected_index
        self.clipboard = copy.deepcopy(self.json["cells"][index : index + 1])

    def paste(self, index: "Optional[int]" = None) -> "None":
        """Append the contents of the `Notebook`'s clipboard below the current cell."""
        if index is None:
            index = self.page.selected_index
        cell_jsons = copy.deepcopy(self.clipboard)
        # Assign a new cell IDs
        for cell_json in cell_jsons:
            cell_json["id"] = nbformat.v4.new_code_cell().get("id")
        self.json["cells"][index + 1 : index + 1] = cell_jsons
        self.dirty = True
        self.refresh(index + 1)

    def delete(self, index: "Optional[int]" = None) -> "None":
        """Delete a cell from the notebook."""
        if len(self.json["cells"]) > 1:
            if index is None:
                index = self.page.selected_index
            del self.json["cells"][index]
            self.dirty = True
            self.refresh()

    def refresh(self, index: "Optional[int]" = None) -> "None":
        """Refresh the rendered contents of this notebook."""
        if index is None:
            index = self.page.selected_index
        # self.page.children = self.cell_renderers
        self.page.reset()
        self.page._set_selected_index(index, force=True)

    def save(self) -> "None":
        """Write the notebook's JSON to the current notebook's file."""
        self.json = nbformat.from_dict(self.json)
        nbformat.write(nb=self.json, fp=self.path)
        self.dirty = False

    def close(self, cb: "Optional[Callable]") -> "None":
        """Check if the user want to save an unsaved notebook, then close the file.

        Args:
            cb: A callback to run if after closing the notebook.

        """
        if self.dirty:
            self.unsaved(cb)
        else:
            self.really_close(cb)

    def really_close(self, cb: "Optional[Callable]") -> "None":
        """Shutdown the kernel and close the notebook.

        Args:
            cb: A callback to run if after closing the notebook.

        """
        log.debug("Closing notebook '%s'", self.path.name)
        if self.kernel:
            # When closing a notebook in interactive mode we do not want to wait for
            # the kernel to finish before closing it. If we have a kernel in
            # non-interactive mode, we are doing a run and dump, so we want to wait for
            # the kernel to finish everything before we close it
            self.kernel.stop(wait=not self.interactive)
            self.kernel.shutdown()
        if cb:
            cb()

    def unsaved(self, cb: "Optional[Callable]") -> "None":
        """Display a dialog prompting the user to save unsaved changes.

        Args:
            cb: A callback to run if after closing the notebook.

        """
        app = cast("App", get_app())

        def yes_cb() -> "None":
            self.save()
            self.really_close(cb)

        def no_cb() -> "None":
            self.really_close(cb)

        app.dialog(
            title="Unsaved Changes",
            body=Window(
                FormattedTextControl(
                    [
                        ("bold", self.path.name),
                        ("", " has unsaved changes\n"),
                        ("", "Do you want to save your changes?"),
                    ]
                ),
                dont_extend_height=True,
            ),
            buttons={
                "Yes": yes_cb,
                "No": no_cb,
                "Cancel": None,
            },
        )

    def statusbar_fields(
        self,
    ) -> "tuple[list[AnyFormattedText], list[AnyFormattedText]]":
        """Generates the formatted text for the statusbar."""
        return (
            [
                f"Cell {self.page.selected_index+1}",
                "*" if self.dirty else "",
            ],
            [
                ("", self.kernel_display_name, self._statusbar_kernel_handeler),
                KERNEL_STATUS_REPR[self.kernel.status],
            ],
        )

    def _statusbar_kernel_handeler(self, event: "MouseEvent") -> "None":
        """Event handler for kernel name field in statusbar."""
        if event.event_type == MouseEventType.MOUSE_UP:
            self.change_kernel()
