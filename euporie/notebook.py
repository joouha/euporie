# -*- coding: utf-8 -*-
import asyncio
import copy
import threading
from functools import partial
from pathlib import Path
from typing import Optional

import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from prompt_toolkit.application.current import get_app
from prompt_toolkit.completion.base import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.layout.containers import Container, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.layout.margins import NumberedMargin
from prompt_toolkit.widgets import Box, Label, RadioList

from euporie.cell import Cell
from euporie.config import config
from euporie.keys import KeyBindingsInfo
from euporie.scroll import ScrollingContainer


class KernelCompleter(Completer):
    def __init__(self, nb):
        self.nb = nb

    def get_completions(self):
        pass

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ):
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


class Notebook:
    def __init__(self, path):

        self.char_px_y = 32
        self.char_px_x = 15

        self.output_cache = {}

        self.dirty = False
        self.kernel_status = "starting"
        self.line_numbers = config.show_line_numbers

        self.path = Path(path).expanduser()
        if self.path.exists():
            self.json = nbformat.read(self.path, as_version=4)
        else:
            self.json = nbformat.v4.new_notebook()
        # Ensure there is always at least one cell
        if not self.json.setdefault("cells", []):
            self.json["cells"] = [nbformat.v4.new_code_cell()]

        self.page = ScrollingContainer(
            children=self.cell_renderers,
            max_content_width=D(preferred=config.max_notebook_width),
        )
        self.container = Box(self.page, padding=0, padding_left=1)
        self.container.container.key_bindings = self.load_key_bindings()

        self.clipboard = []

        self.completer = KernelCompleter(self)
        self.km = self.kc = None

        def setup_loop():
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
        self.kernel_thread = threading.Thread(target=setup_loop)
        self.kernel_thread.start()

    async def start_kernel(self):

        if not self.kernel_name:
            self.change_kernel()
            return

        # Create a kernel manager for this notebook
        self.km = KernelManager(kernel_name=self.kernel_name)
        try:
            # await self.km._async_start_kernel()
            self.km.start_kernel()
        except Exception as e:
            get_app().dialog("Error Starting Kernel", Label(e.__repr__()), {"OK": None})
            self.kc = None
            self.kernel_status = "error"
        else:
            self.kc = self.km.client()
            self.kc.start_channels()
            self.kernel_status = "idle"
        get_app().invalidate()

    def restart_kernel(self):
        async def restart():
            if self.km:
                await self.km._async_shutdown_kernel()
            await self.start_kernel()

        asyncio.run_coroutine_threadsafe(
            restart(),
            self.kernel_loop,
        )

    @property
    def kernel_name(self):
        return self.json.get("metadata", {}).get("kernelspec", {}).get("name")

    def change_kernel(self):
        def change_kernel_cb():
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
        get_app().dialog(
            title="Select Kernel",
            body=HSplit(
                [
                    Label("Please select a kernel:"),
                    options,
                ]
            ),
            buttons={
                "Select": change_kernel_cb,
                "Cancel": None,
            },
        )

    @property
    def cell_renderers(self):
        return [
            partial(Cell, i, cell_json, self)
            for i, cell_json in enumerate(self.json["cells"])
        ]

    def get_cell_by_id(self, cell_id) -> Optional[Cell]:
        for cell in self.page.child_cache.values():
            if cell.id == cell_id:
                break
        else:
            return
        return cell

    def load_key_bindings(self):
        kb = KeyBindingsInfo()

        @kb.add("c-s", group="Application", desc="Save current file")
        def save(event):
            self.save()

        @kb.add("a", group="Notebook", desc="Add new cell above")
        def add_above(event):
            self.add(0)

        @kb.add("b", group="Notebook", desc="Add new cell below")
        def add_below(event):
            self.add(1)

        @kb.add("d", "d", group="Notebook", desc="Delete current cell")
        def delete(event):
            self.delete()

        @kb.add("x", group="Notebook", desc="Cut current cell")
        def cut(event):
            self.cut()

        @kb.add("c", group="Notebook", desc="Copy current cell")
        def copy(event):
            self.copy()

        @kb.add("v", group="Notebook", desc="Paste copied cell")
        def paste(event):
            self.paste()

        @kb.add("m", group="Notebook", desc="Change cell to markdown")
        def to_markdown(event):
            self.cell.set_cell_type("markdown")
            self.cell.clear_output()

        @kb.add("y", group="Notebook", desc="Change cell to code")
        def to_code(event):
            self.cell.set_cell_type("code")

        @kb.add("r", group="Notebook", desc="Change cell to raw")
        def to_raw(event):
            self.cell.set_cell_type("raw")
            self.cell.clear_output()

        @kb.add("l", group="Notebook", desc="Toggle line numbers")
        def line_nos(event):
            self.line_numbers = not self.line_numbers
            for cell in self.page.child_cache.values():
                cell.input_box.window.left_margins = (
                    [NumberedMargin()] if self.line_numbers else []
                )

        return kb

    @property
    def cell(self):
        return self.page.get_child()

    def add(self, offset):
        index = self.page.selected_index + offset
        self.json["cells"].insert(
            index,
            nbformat.v4.new_code_cell(),
        )
        self.dirty = True
        self.refresh(index=index)

    def cut(self, index=None):
        if index is None:
            index = self.page.selected_index
        self.copy(index)
        self.delete(index)

    def copy(self, index=None):
        if index is None:
            index = self.page.selected_index
        self.clipboard = copy.deepcopy(self.json["cells"][index : index + 1])

    def paste(self, index=None):
        if index is None:
            index = self.page.selected_index
        self.json["cells"][index + 1 : index + 1] = copy.deepcopy(self.clipboard)
        self.dirty = True
        self.refresh(index + 1)

    def delete(self, index=None):
        if len(self.json["cells"]) > 1:
            if index is None:
                index = self.page.selected_index
            del self.json["cells"][index]
            self.dirty = True
            self.refresh()

    def refresh(self, index=None):
        if index is None:
            index = self.page.selected_index
        self.page.children = self.cell_renderers
        self.page.reset()
        self.page._set_selected_index(index, force=True)

    def save(self):
        self.json = nbformat.from_dict(self.json)
        nbformat.write(nb=self.json, fp=self.path)
        self.dirty = False

    def close(self, cb):
        if self.dirty:
            self.unsaved(cb)
        else:
            self.really_close(cb)

    def really_close(self, cb):
        # Tell the kernel to shutdown
        if self.kc is not None:
            self.kc.shutdown()
        # Tell the event loop in the kernel monitoring thread to shutdown
        self.kernel_loop.call_soon_threadsafe(self.kernel_loop.stop)
        # Close the kernel monitoring thread
        self.kernel_thread.join()
        # Tell the app we've closed
        cb()

    def unsaved(self, cb):
        app = get_app()

        def yes_cb():
            self.save()
            self.really_close(cb)

        def no_cb():
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

    def __pt_container__(self) -> Container:
        return self.container
