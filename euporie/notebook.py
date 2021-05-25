# -*- coding: utf-8 -*-
"""Contains the main class for a notebook file."""
from __future__ import annotations

import asyncio
import copy
import threading
from functools import partial
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    AsyncGenerator,
    Callable,
    Iterable,
    Optional,
    Union,
    cast,
)

import nbformat  # type: ignore
from jupyter_client import KernelClient, KernelManager  # type: ignore
from jupyter_client.kernelspec import KernelSpecManager  # type: ignore
from prompt_toolkit.application.current import get_app
from prompt_toolkit.completion.base import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.layout.containers import AnyContainer, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.layout.margins import NumberedMargin
from prompt_toolkit.widgets import Label, RadioList

from euporie.cell import Cell
from euporie.config import config
from euporie.keys import KeyBindingsInfo
from euporie.scroll import PrintingContainer, ScrollingContainer

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent

    from euporie.app import App


class File:
    """Base class for file containers."""

    def close(self, cb: "Optional[Callable]") -> "None":
        """Function to close a file.

        Args:
            cb: A function to call when the file is closed.

        """
        pass

    def focus(self) -> "None":
        """Focuses the file."""
        pass

    def __pt_container__(self) -> "AnyContainer":
        """Return the file container object."""
        pass


class KernelCompleter(Completer):
    """A prompt_toolkit completer which provides completions from a Jupyter kernel."""

    def __init__(self, nb: "Notebook"):
        """Instantiate the completer for a given notebook.

        Args:
            nb: A `Notebook` instance

        """
        self.nb = nb

    def get_completions(
        self, document: "Document", complete_event: "CompleteEvent"
    ) -> "Iterable[Completion]":
        """Does nothing as completions are retrieved asynchronously."""
        while False:
            yield

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> "AsyncGenerator[Completion, None]":
        """An asynchronous generator of `Completions`, as returned by the kernel."""
        if self.nb.kc:
            msg_id = self.nb.kc.complete(
                code=document.text,
                cursor_pos=document.cursor_position,
            )
            # msg = await self.nb.kc._async_get_shell_msg()
            msg = self.nb.kc.get_shell_msg()
            if msg["parent_header"].get("msg_id") == msg_id:
                # run_in_terminal(lambda: print(msg))
                content = msg.get("content", {})
                rel_start_position = (
                    content.get("cursor_start", 0) - document.cursor_position
                )
                for match in content.get("matches", []):
                    yield Completion(match, start_position=rel_start_position)


class Notebook(File):
    """The main notebook container class."""

    page: "ScrollingContainer"

    def __init__(
        self,
        path: "Path",
        interactive: "bool" = True,
        execute: "bool" = False,
        scroll: "bool" = False,
    ):
        """Instantiate a Notebook container, using a notebook at a given path."""
        self.path = Path(path).expanduser()
        self.interactive = interactive
        self.execute = execute
        self.scroll = scroll

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
        self.kernel_status = "starting"
        self.line_numbers = config.show_line_numbers
        self.completer = KernelCompleter(self)
        self.km: "Optional[KernelManager]" = None
        self.kc: "Optional[KernelClient]" = None
        self.kernel_loop: "Optional[asyncio.AbstractEventLoop]" = None

        self.container: "AnyContainer"

        if not self.scroll:
            self.container = PrintingContainer(
                self.cell_renderers,
                width=config.max_notebook_width,
            )

        else:
            self.page = ScrollingContainer(
                children=self.cell_renderers,
                max_content_width=D(preferred=int(config.max_notebook_width)),
            )
            # Wrap the scolling container in an hsplit and apply the keybindings
            # TODO - refactor key-bindings
            self.container = HSplit([self.page])
            self.container.key_bindings = self.load_key_bindings()

        def setup_loop() -> None:
            """Set up a thread with an event loop to listen for kernel responses."""
            # Create and set kernel loop
            self.kernel_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.kernel_loop)
            # Start kernel
            asyncio.run_coroutine_threadsafe(
                self.start_kernel(),
                self.kernel_loop,
            )
            # Now we wait
            self.kernel_loop.run_forever()

        # Run the kernel event loop in a new thread
        if self.interactive or self.execute:
            self.kernel_thread = threading.Thread(target=setup_loop)
            self.kernel_thread.start()

    async def start_kernel(self) -> None:
        """Starts a Juypter kernel, creating a `KernelManager`."""
        if not self.kernel_name:
            self.change_kernel()
            return
        # Create a kernel manager for this notebook
        self.km = KernelManager(kernel_name=self.kernel_name)
        try:
            # await self.km._async_start_kernel()
            self.km.start_kernel()
        except Exception as e:
            app = cast("App", get_app())
            app.dialog("Error Starting Kernel", Label(e.__repr__()), {"OK": None})
            self.kc = None
            self.kernel_status = "error"
        else:
            self.kc = self.km.client()
            self.kc.start_channels()
            self.kernel_status = "idle"
        get_app().invalidate()

    def restart_kernel(self) -> "None":
        """Restarts the current `Notebook`'s kernel.

        This is performed asynchronously in the notebook's kernel thread.
        """

        async def _restart() -> "None":
            if self.km:
                await self.km._async_shutdown_kernel()
            await self.start_kernel()

        assert self.kernel_loop is not None
        asyncio.run_coroutine_threadsafe(
            _restart(),
            self.kernel_loop,
        )

    @property
    def kernel_name(self) -> "str":
        """Return the name of the kernel defined in the notebook JSON."""
        return self.json.get("metadata", {}).get("kernelspec", {}).get("name")

    def change_kernel(self) -> None:
        """Displays a dialog for the user to select a new kernel."""

        def _change_kernel_cb() -> None:
            name = options.current_value
            spec = kernel_specs.get(name, {}).get("spec", {})
            self.json.setdefault("metadata", {})["kernelspec"] = {
                "display_name": spec["display_name"],
                "language": spec["language"],
                "name": name,
            }
            self.restart_kernel()

        if self.km:
            kernel_specs = self.km.kernel_spec_manager.get_all_specs()
        else:
            kernel_specs = KernelSpecManager().get_all_specs()
        options = RadioList(
            [
                (
                    kernel_name,
                    kernel_spec.get("spec", {}).get("display_name", kernel_name),
                )
                for kernel_name, kernel_spec in kernel_specs.items()
            ]
        )
        app = cast("App", get_app())
        app.dialog(
            title="Select Kernel",
            body=HSplit(
                [
                    Label("Please select a kernel:"),
                    options,
                ]
            ),
            buttons={
                "Select": _change_kernel_cb,
                "Cancel": None,
            },
        )

    def focus(self) -> "None":
        """Focus the notebooks."""
        if hasattr(self, "page"):
            self.page.focus()

    @property
    def cell_renderers(self) -> "list[Union[Callable, AnyContainer]]":
        """Return a list of `Cell` generator functions for the notebooks' cells."""
        return [
            partial(Cell, i, cell_json, self)
            for i, cell_json in enumerate(self.json["cells"])
        ]

    def get_cell_by_id(self, cell_id: "str") -> "Optional[Cell]":
        """Returns a reference to the `Cell` container with a given cell id."""
        for cell in self.page.child_cache.values():
            assert isinstance(cell, Cell)
            if cell.id == cell_id:
                break
        else:
            return None
        return cell

    def load_key_bindings(self) -> "KeyBindings":
        """Load the key bindings associate with a `Notebook` container."""
        kb = KeyBindingsInfo()

        @kb.add("c-s", group="Application", desc="Save current file")
        def save(event: "KeyPressEvent") -> "None":
            self.save()

        @kb.add("a", group="Notebook", desc="Add new cell above")
        def add_above(event: "KeyPressEvent") -> "None":
            self.add(0)

        @kb.add("b", group="Notebook", desc="Add new cell below")
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
            for cell in self.page.child_cache.values():
                assert isinstance(cell, Cell)
                cell.input_box.window.left_margins = (
                    [NumberedMargin()] if self.line_numbers else []
                )

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
            True if the child is rendered and partially off-screen, otherwise False.=

        """
        if self.scroll:
            return self.page.is_child_obscured(index)
        else:
            return False

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
        self.json["cells"][index + 1 : index + 1] = copy.deepcopy(self.clipboard)
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
        self.page.children = self.cell_renderers
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
        # Tell the kernel to shutdown
        if self.kc is not None:
            self.kc.shutdown()

        if self.kernel_loop is not None:
            # Tell the event loop in the kernel monitoring thread to shutdown
            self.kernel_loop.call_soon_threadsafe(self.kernel_loop.stop)
            # Close the kernel monitoring thread
            self.kernel_thread.join()

        # Tell the app we've closed
        if cb is not None:
            cb()

    def unsaved(self, cb: "Optional[Callable]") -> "None":
        """Display a dialog prompting the user to save unsaved changes.

        Args:
            cb: A callback to run if after closing the notebook.

        """
        app = cast("App", get_app())

        def yes_cb() -> None:
            self.save()
            self.really_close(cb)

        def no_cb() -> None:
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

    def __pt_container__(self) -> "AnyContainer":
        """Return the main `Notebook` container object."""
        return self.container
