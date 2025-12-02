"""Contain the base class for a notebook tabs."""

from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod, abstractproperty
from base64 import standard_b64decode
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.filters import Never

from euporie.core.comm.registry import open_comm
from euporie.core.io import edit_in_editor
from euporie.core.kernel.base import MsgCallbacks
from euporie.core.nbformat import from_dict, new_code_cell, new_notebook
from euporie.core.nbformat import read as read_nb
from euporie.core.nbformat import write as write_nb
from euporie.core.tabs.kernel import KernelTab
from euporie.core.widgets.cell import Cell, get_cell_id

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path
    from typing import Any

    from prompt_toolkit.filters import Filter
    from prompt_toolkit.layout.containers import AnyContainer, Window

    from euporie.core.app.app import BaseApp
    from euporie.core.comm.base import Comm
    from euporie.core.kernel.base import BaseKernel
    from euporie.core.lsp import LspClient
    from euporie.core.widgets.inputs import KernelInput

log = logging.getLogger(__name__)


class BaseNotebook(KernelTab, metaclass=ABCMeta):
    """The main notebook container class."""

    allow_stdin = False
    edit_mode = False

    def __init__(
        self,
        app: BaseApp,
        path: Path | None = None,
        kernel: BaseKernel | None = None,
        comms: dict[str, Comm] | None = None,
        use_kernel_history: bool = False,
        json: dict[str, Any] | None = None,
    ) -> None:
        """Instantiate a Notebook container, using a notebook at a given path.

        Args:
            path: The file path of the notebook
            app: The euporie application the notebook tab belongs to
            kernel: An existing kernel instance to use
            comms: Existing kernel comm object to use
            use_kernel_history: If True, load history from the kernel
            json: JSON contents of notebook, used if path not given

        """
        self.default_callbacks = MsgCallbacks(
            {
                "get_input": lambda prompt, password: self.cell.get_input(
                    prompt, password
                ),
                "set_execution_count": lambda n: self.cell.set_execution_count(n),
                "add_output": self.new_output_default,
                "clear_output": lambda wait: self.cell.clear_output(wait),
                "set_metadata": lambda path, data: self.cell.set_metadata(path, data),
                "set_status": self.set_status,
                "set_kernel_info": self.set_kernel_info,
                "dead": self.kernel_died,
                "edit_magic": edit_in_editor,
            }
        )
        self.json = json or new_notebook()
        self._rendered_cells: dict[str, Cell] = {}
        self.multiple_cells_selected: Filter = Never()
        self.loaded = path is None
        self._really_init_kernel: Callable[[], None] | None = None

        super().__init__(
            app, path, kernel=kernel, comms=comms, use_kernel_history=use_kernel_history
        )

        # Load notebook file
        self.container = self.load_container()

    # Tab stuff

    def reset(self) -> None:
        """Reload the notebook file from the disk and re-render."""
        # Restore selection after reset
        if self.path is not None:
            self._rendered_cells = {}
            self.load()
        self.refresh()

    # KernelTab stuff

    def init_kernel(
        self,
        kernel: BaseKernel | None = None,
        comms: dict[str, Comm] | None = None,
        use_kernel_history: bool = False,
        connection_file: Path | None = None,
    ) -> None:
        """Defer loading kernel until after notebook file is loaded."""
        if self.loaded:
            super().init_kernel(kernel, comms, use_kernel_history, connection_file)
        else:
            self._really_init_kernel = partial(
                super().init_kernel, kernel, comms, use_kernel_history, connection_file
            )

    def post_init_kernel(self) -> None:
        """Load the notebook container after the kernel has been loaded."""
        super().post_init_kernel()

        # Load widgets
        self.load_widgets_from_metadata()

    @property
    def metadata(self) -> dict[str, Any]:
        """Return a dictionary to hold notebook / kernel metadata."""
        return self.json.setdefault("metadata", {})

    async def load_history(self) -> None:
        """Load kernel history."""
        await super().load_history()
        # Re-run history load for cell input-boxes
        for cell in self._rendered_cells.values():
            cell.input_box.buffer._load_history_task = None
            cell.input_box.buffer.load_history_if_not_yet_loaded()

    def kernel_started(self, result: dict[str, Any] | None = None) -> None:
        """Task to run when the kernel has started."""
        super().kernel_started(result)

    # Notebook stuff

    def load(self) -> None:
        """Load the notebook file from the file-system."""
        # Open json file, or load from passed json object
        if self.path is not None and self.path.exists():
            with self.path.open() as f:
                self.json = read_nb(f, as_version=4)
        # Ensure there is always at least one cell
        if not self.json.setdefault("cells", []):
            self.json["cells"] = [new_code_cell()]
        self.loaded = True
        if callable(self._really_init_kernel):
            # Only call this once
            self._really_init_kernel()
            self._really_init_kernel = None

    def set_status(self, status: str) -> None:
        """Call when kernel status changes."""
        self.cell.set_status(status)
        self.app.invalidate()

    @property
    def selected_indices(self) -> list[int]:
        """Return a list of the currently selected cell indices."""
        return []

    @abstractmethod
    def load_container(self) -> AnyContainer:
        """Absract method for loading the notebook's main container."""

    @abstractproperty
    def cell(self) -> Cell:
        """Return the current cell."""
        ...

    @property
    def current_input(self) -> KernelInput:
        """Return the currently active kernel input, if any."""
        return self.cell.input_box

    @property
    def path_name(self) -> str:
        """Return the path name."""
        if self.path is not None:
            return self.path.name
        else:
            return "(New file)"

    @property
    def title(self) -> str:
        """Return the tab title."""
        return ("* " if self.dirty else "") + self.path_name

    def lang_file_ext(self) -> str:
        """Return the file extension for scripts in the notebook's language."""
        return (
            self.json.get("metadata", {})
            .get("language_info", {})
            .get("file_extension", ".py")
        )

    def rendered_cells(self) -> list[Cell]:
        """Return a list of rendered notebooks' cells."""
        cells = {}
        for i, cell_json in enumerate(self.json.get("cells", [])):
            cell_id = get_cell_id(cell_json)
            if cell_id in self._rendered_cells:
                cells[cell_id] = self._rendered_cells[cell_id]
            else:
                cells[cell_id] = Cell(
                    i, cell_json, self, is_new=bool(self._rendered_cells)
                )
            cells[cell_id].index = i
        # These cells will be removed
        for cell in set(self._rendered_cells.values()) - set(cells.values()):
            cell.close()
            del cell
        self._rendered_cells = cells
        return list(self._rendered_cells.values())

    def get_cell_by_id(self, cell_id: str) -> Cell | None:
        """Return a reference to the `Cell` container with a given cell id."""
        # Re-render the cells as the one we want might be new
        for cell in self._rendered_cells.values():
            if cell.id == cell_id:
                break
        else:
            return None
        return cell

    def select(
        self,
        cell_index: int,
        extend: bool = False,
        position: int | None = None,
        scroll: bool = False,
    ) -> None:
        """Select a cell."""

    def scroll_to(self, index: int) -> None:
        """Scroll to a cell by index."""

    def refresh(self, slice_: slice | None = None, scroll: bool = False) -> None:
        """Refresh the notebook."""

    def refresh_cell(self, cell: Cell) -> None:
        """Trigger the refresh of a notebook cell."""

    def close(self, cb: Callable | None = None) -> None:
        """Check if the user want to save an unsaved notebook, then close the file.

        Args:
            cb: A callback to run if after closing the notebook.

        """
        if self.dirty and (unsaved := self.app.get_dialog("unsaved")):
            unsaved.show(
                tab=self,
                cb=partial(super().close, cb),
            )
        else:
            super().close(cb)

    def write_file(self, path: Path) -> None:
        """Write the notebook's JSON to the current notebook's file.

        Additionally save the widget state to the notebook metadata.

        Args:
            path: An path at which to save the file

        """
        if self.app.config.save_widget_state:
            self.json.setdefault("metadata", {})["widgets"] = {
                "application/vnd.jupyter.widget-state+json": {
                    "version_major": 2,
                    "version_minor": 0,
                    "state": {
                        comm_id: comm._get_embed_state()
                        for comm_id, comm in self.comms.items()
                        if comm.data.get("state", {}).get("__unlinked__") is not True
                    },
                }
            }
        with path.open("w") as open_file:
            try:
                write_nb(nb=from_dict(self.json), fp=open_file)
            except AssertionError:
                try:
                    # Jupytext requires a filename if we don't give it a format
                    write_nb(nb=from_dict(self.json), fp=path)
                except Exception:
                    # Jupytext requires a format if the path has no extension
                    # We just use ipynb as the default format
                    write_nb(
                        nb=from_dict(self.json),
                        fp=open_file,
                        fmt="ipynb",
                    )

    def run_cell(
        self,
        cell: Cell,
        wait: bool = False,
        callback: Callable[..., None] | None = None,
    ) -> None:
        """Run a cell.

        Args:
            cell: The rendered cell to run. If ``None``, runs the currently
                selected cell.
            wait: If :py:const:`True`, blocks until cell execution is finished
            callback: Function to run after completion

        """
        cell.remove_outputs()
        self.dirty = True
        # Queue cell if kernel not yet started
        if self.kernel.status == "starting":
            log.debug("Queuing running of cell %s", cell.index)
            self.kernel_queue.append(partial(self.run_cell, cell, wait, callback))
        else:
            self.kernel.run(
                str(cell.json.get("source")),
                wait=wait,
                callback=callback,
                get_input=cell.get_input,
                set_execution_count=cell.set_execution_count,
                add_output=cell.add_output,
                clear_output=cell.clear_output,
                set_metadata=cell.set_metadata,
                set_status=cell.set_status,
                done=cell.ran,
            )

    def new_output_default(self, output_json: dict[str, Any], own: bool) -> None:
        """Add a new output without a cell to the currently selected cell."""
        if self.app.config.show_remote_outputs:
            self.cell.add_output(output_json, own)

    def load_widgets_from_metadata(self) -> None:
        """Load widgets from state saved in notebook metadata."""
        for comm_id, comm_data in (
            self.json.get("metadata", {})
            .get("widgets", {})
            .get("application/vnd.jupyter.widget-state+json", {})
            .get("state", {})
        ).items():
            state = comm_data.get("state", {})
            # Add _model_* keys to the state
            for key, value in comm_data.items():
                if key not in ("state", "buffers"):
                    state[f"_{key}"] = value
            # Flag this widget as not linked to a widget in the kernel, so its state
            # will not be persisted on the next save
            state["__unlinked__"] = True
            # Decode base64 encoded buffers and add buffer paths to data
            buffers = []
            buffer_paths = []
            if "buffers" in state:
                for buffer_data in state.pop("buffers", []):
                    buffer_paths.append(buffer_data["path"])
                    buffers.append(standard_b64decode(buffer_data["data"]))
            # Add this comm to the notebook's current Comm map
            self.comms[comm_id] = open_comm(
                comm_container=self,
                content={
                    "data": {
                        "state": state,
                        "buffer_paths": buffer_paths,
                    },
                    "comm_id": comm_id,
                    "target_name": "jupyter.widget",
                },
                buffers=buffers,
            )

    def lsp_open_handler(self, lsp: LspClient) -> None:
        """Tell the LSP we opened a file."""
        lsp.open_nb(
            path=self.path,
            cells=[cell.lsp_cell for cell in self.rendered_cells()],
            metadata=self.metadata,
        )

    def lsp_change_handler(self, lsp: LspClient) -> None:
        """Tell the LSP server a file metadata has changed."""
        lsp.change_nb_meta(path=self.path, metadata=self.metadata)

    def lsp_before_save_handler(self, lsp: LspClient) -> None:
        """Tell the the LSP we are about to save a document."""
        # Do nothing for notebooks

    def lsp_after_save_handler(self, lsp: LspClient) -> None:
        """Tell the the LSP we saved a document."""
        lsp.save_nb(self.path)

    def lsp_close_handler(self, lsp: LspClient) -> None:
        """Tell the LSP we opened a file."""
        if lsp.can_close_nb:
            lsp.close_nb(
                path=self.path, cells=[cell.lsp_cell for cell in self.rendered_cells()]
            )
        else:
            for cell in self.rendered_cells():
                lsp.close_doc(cell.path)

    def lsp_update_diagnostics(self, lsp: LspClient) -> None:
        """Process a new diagnostic report from the LSP."""
        # Do nothing, these are handled by cells

    def __pt_searchables__(self) -> Sequence[Window]:
        """Return list of cell input buffer controls for searching."""
        return [cell.input_box.window for cell in self.rendered_cells()]
