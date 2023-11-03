"""Contain the main class for a notebook file."""

from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod, abstractproperty
from base64 import standard_b64decode
from functools import partial
from typing import TYPE_CHECKING

import nbformat
from prompt_toolkit.filters import Never, buffer_has_focus

from euporie.core.comm.registry import open_comm
from euporie.core.commands import get_cmd
from euporie.core.config import add_setting
from euporie.core.kernel import MsgCallbacks
from euporie.core.path import parse_path
from euporie.core.tabs.base import KernelTab
from euporie.core.terminal import edit_in_editor
from euporie.core.widgets.cell import Cell, get_cell_id

try:
    from jupytext import read as read_nb
    from jupytext import write as write_nb
except ModuleNotFoundError:
    from nbformat import read as read_nb
    from nbformat import write as write_nb

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, Callable

    from prompt_toolkit.filters import Filter
    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.app import BaseApp
    from euporie.core.comm.base import Comm
    from euporie.core.kernel import Kernel

log = logging.getLogger(__name__)


class BaseNotebook(KernelTab, metaclass=ABCMeta):
    """The main notebook container class."""

    allow_stdin = False
    edit_mode = False

    def __init__(
        self,
        app: BaseApp,
        path: Path | None = None,
        kernel: Kernel | None = None,
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
                "add_output": lambda output_json: self.cell.add_output(output_json),
                "clear_output": lambda wait: self.cell.clear_output(wait),
                "set_metadata": lambda path, data: self.cell.set_metadata(path, data),
                "set_status": self.set_status,
                "set_kernel_info": self.set_kernel_info,
                "dead": self.kernel_died,
                "edit_magic": edit_in_editor,
            }
        )
        self.json = json or {}
        self._rendered_cells: dict[str, Cell] = {}
        self.multiple_cells_selected: Filter = Never()
        self.path = parse_path(path) if path else None
        self.loaded = False

        super().__init__(
            app, path, kernel=kernel, comms=comms, use_kernel_history=use_kernel_history
        )

    # Tab stuff

    def reset(self) -> None:
        """Reload the notebook file from the disk and re-render."""
        # Restore selection after reset
        if self.path is not None:
            self._rendered_cells = {}
            self.load()
        self.refresh()

    # KernelTab stuff

    def pre_init_kernel(self) -> None:
        """Run stuff before the kernel is loaded."""
        # Load notebook file
        self.load()

    def post_init_kernel(self) -> None:
        """Load the notebook container after the kernel has been loaded."""
        # Replace the tab's container
        prev = self.container
        self.container = self.load_container()
        self.loaded = True
        self.app.invalidate()

        # Update the focus if the old container had focus
        if (layout := self.app.layout).has_focus(prev):

            async def _focus_new_container() -> None:
                layout.focus(self.container)

            self.app.create_background_task(_focus_new_container())

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

    def kernel_died(self) -> None:
        """Call if the kernel dies."""
        if confirm := self.app.dialogs.get("confirm"):
            confirm.show(
                title="Kernel connection lost",
                message="The kernel appears to have died\n"
                "as it can no longer be reached.\n\n"
                "Do you want to restart the kernel?",
                cb=self.kernel.restart,
            )

    # Notebook stuff

    def load(self) -> None:
        """Load the notebook file from the file-system."""
        # Open json file, or load from passed json object
        if self.path is not None and self.path.exists():
            with self.path.open() as f:
                self.json = read_nb(f, as_version=4)
        else:
            self.json = self.json or nbformat.v4.new_notebook()
        # Ensure there is always at least one cell
        if not self.json.setdefault("cells", []):
            self.json["cells"] = [nbformat.v4.new_code_cell()]

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
        """Abcract method for loading the notebook's main container."""
        ...

    @abstractproperty
    def cell(self) -> Cell:
        """Return the current cell."""
        ...

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
                # Pytype doesn't like this..
                cells[cell_id] = Cell(i, cell_json, self)  # type: ignore
            cells[cell_id].index = i
        # These cells will be removed
        for cell in set(self._rendered_cells.values()) - set(cells.values()):
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
        if self.dirty and (unsaved := self.app.dialogs.get("unsaved")):
            unsaved.show(
                tab=self,
                cb=cb,
            )
        else:
            super().close(cb)

    def save(self, path: Path | None = None, cb: Callable | None = None) -> None:
        """Write the notebook's JSON to the current notebook's file.

        Additionally save the widget state to the notebook metadata.

        Args:
            path: An optional new path at which to save the tab
            cb: A callback to run if after saving the notebook.

        """
        if path is not None:
            self.path = path
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
        if self.path is None:
            if dialog := self.app.dialogs.get("save-as"):
                dialog.show(tab=self, cb=cb)
        else:
            log.debug("Saving notebook..")
            self.saving = True
            self.app.invalidate()

            # Save to a temp file, then replace the original
            temp_path = self.path.parent / f".{self.path.stem}.tmp{self.path.suffix}"
            log.debug("Using temporary file %s", temp_path.name)
            try:
                open_file = temp_path.open("w")
            except NotImplementedError:
                get_cmd("save-as").run()
            else:
                try:
                    try:
                        with open_file as f:
                            write_nb(nb=nbformat.from_dict(self.json), fp=f)
                    except AssertionError:
                        # Jupytext requires a filename if we don't give it a format
                        write_nb(nb=nbformat.from_dict(self.json), fp=temp_path)
                except Exception:
                    if dialog := self.app.dialogs.get("save-as"):
                        dialog.show(tab=self, cb=cb)
                else:
                    open_file.close()
                    try:
                        temp_path.rename(self.path)
                    except Exception:
                        if dialog := self.app.dialogs.get("save-as"):
                            dialog.show(tab=self, cb=cb)
                    else:
                        self.dirty = False
                        self.saving = False
                        self.app.invalidate()
                        log.debug("Notebook saved")
            # Run the callback
            if callable(cb):
                cb()

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

    # ################################### Settings ####################################

    add_setting(
        name="save_widget_state",
        flags=["--save-widget-state"],
        type_=bool,
        help_="Save a notebook's widget state in the notebook metadata",
        default=True,
        description="""
            When set to ``True``, the state of any widgets in the current notebook will
            be saves in the notebook's metadata. This enables widgets to be displayed
            when the notebook is re-opened without having to re-run the notebook.
        """,
    )

    add_setting(
        name="max_notebook_width",
        flags=["--max-notebook-width"],
        type_=int,
        help_="Maximum width of notebooks",
        default=120,
        schema={
            "minimum": 1,
        },
        description="""
            The maximum width at which to display a notebook.
        """,
    )

    add_setting(
        name="expand",
        flags=["--expand"],
        type_=bool,
        help_="Use the full width to display notebooks",
        default=False,
        description="""
            Whether the notebook page should expand to fill the available width
        """,
        cmd_filter=~buffer_has_focus,
    )
