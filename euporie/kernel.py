# -*- coding: utf-8 -*-
"""Contains the main class for a notebook file."""
from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import Future
from functools import partial
from typing import AsyncGenerator, Callable, Optional

import nbformat  # type: ignore
from jupyter_client import (  # type: ignore
    AsyncKernelManager,
    KernelClient,
    KernelManager,
)

log = logging.getLogger(__name__)


class NotebookKernel:
    """Runs a notebook kernel asynchronously in it's own thread."""

    kc: "KernelClient"

    def __init__(self, name: "str" = "python3") -> None:
        """Called when the ``NotebookKernel`` is initalized.

        Args:
            name: The name of the kernel to start

        """
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._setup_loop)
        self.thread.daemon = True
        self.thread.start()

        self.km = AsyncKernelManager(kernel_name=name or "python")
        self.status = "stopped"

    @property
    def specs(self) -> "dict[str, dict]":
        """Returns a list of available kernelspecs."""
        return self.km.kernel_spec_manager.get_all_specs()

    def _setup_loop(self) -> "None":
        """Set the current loop the the kernel's event loop.

        This method is intended to be run in the kernel thread.
        """
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start(self, cb: "Optional[Callable]" = None) -> "None":
        """Starts the kernel.

        Args:
            cb: An optional callback to run after the kernel has started

        """
        asyncio.run_coroutine_threadsafe(
            self._start(cb),
            self.loop,
        )

    async def _start(self, cb: "Optional[Callable]" = None) -> "None":
        """Start the kernel and set its status."""
        await self.km.start_kernel()
        self.kc = self.km.client()
        self.kc.start_channels()
        try:
            await self.kc.wait_for_ready(timeout=5)
        except RuntimeError:
            await self._stop()
            self.status = "error"
        else:
            self.status = "idle"

        if callable(cb):
            cb()

    def wait(self) -> "None":
        """Blocks until the kernel is ready."""
        import time

        while self.status != "idle":
            time.sleep(0.1)

    def run(
        self,
        cell_json: "dict",
        output_cb: "Optional[Callable]" = None,
        cb: "Optional[Callable]" = None,
    ) -> "None":
        """Run a cell using the notebook kernel.

        Args:
            cell_json: The JSON representation of the cell to run
            output_cb: An optional callback to run after each response message
            cb: An optional callback to run when the cell has finished running

        """
        future = asyncio.run_coroutine_threadsafe(
            self._run(cell_json, output_cb),
            self.loop,
        )

        def _cb(_: "Future") -> "None":
            if cb is not None:
                cb()

        future.add_done_callback(_cb)

    async def _run(self, cell_json: "dict", output_cb: "Optional[Callable]") -> "None":
        # Clear outputs late
        # cell_json["outputs"] = []
        await self.kc.execute_interactive(
            code=cell_json.get("source", ""),
            allow_stdin=False,
            output_hook=partial(self._on_output, cell_json, output_cb),
        )

    def _on_output(
        self, cell_json: "dict", cb: "Optional[Callable]", msg: "dict"
    ) -> "None":
        """Process the response messages and update the cell JSON."""
        msg_type = msg.get("header", {}).get("msg_type")

        if msg_type == "status":
            self.status = msg.get("content", {}).get("execution_state", "idle")

        elif msg_type == "execute_input":
            cell_json["execution_count"] = msg.get("content", {}).get("execution_count")

        elif msg_type in ("error", "display_data", "execute_result"):
            cell_json.setdefault("outputs", []).append(nbformat.v4.output_from_msg(msg))

        elif msg_type == "stream":
            # Combine stream outputs
            stream_name = msg.get("content", {}).get("name")
            for output in cell_json.get("outputs", []):
                if output.get("name") == stream_name:
                    output["text"] = output.get("text", "") + msg.get(
                        "content", {}
                    ).get("text", "")
                    break
            else:
                cell_json.setdefault("outputs", []).append(
                    nbformat.v4.output_from_msg(msg)
                )

        if callable(cb):
            cb()

    async def _complete(self, code: "str", cursor_pos: "int") -> "AsyncGenerator":
        """Request code completions from the kernel."""
        msg_id = self.kc.complete(code, cursor_pos)
        msg = await self.kc.get_shell_msg()
        if (
            msg["parent_header"].get("msg_id") == msg_id
            and msg.get("header", {}).get("msg_type") == "complete_reply"
        ):
            content = msg.get("content", {})
            jupyter_types = content.get("metadata", {}).get(
                "_jupyter_types_experimental"
            )
            if jupyter_types:
                for match in jupyter_types:
                    rel_start_position = match.get("start", 0) - cursor_pos
                    completion_type = match.get("type")
                    completion_type = (
                        None if completion_type == "<unknown>" else completion_type
                    )
                    yield {
                        "text": match.get("text"),
                        "start_position": rel_start_position,
                        "display_meta": completion_type,
                    }
            else:
                rel_start_position = content.get("cursor_start", 0) - cursor_pos
                for match in content.get("matches", []):
                    yield {"text": match, "start_position": rel_start_position}

    def interrupt(self) -> "None":
        """Interrupt the kernel.

        This is run synchronously rather than on the event loop in the kernel's thread,
        because otherwise we would have to wait for currently running tasks on the
        kernel's event loop to finish.

        """
        log.debug(f"Interrupting kernel {self.km.kernel_id}")
        if self.km.has_kernel:
            KernelManager.interrupt_kernel(self.km)

    def change(self, name: "str", metadata_json: "dict") -> "None":
        """Change the kernel.

        Args:
            name: The name of the kernel to change to
            metadata_json: The notebook's metedata, so the kernel notebook's kernelspec
                metadata can be updated

        """
        spec = self.specs.get(name, {}).get("spec", {})
        metadata_json["kernelspec"] = {
            "display_name": spec["display_name"],
            "language": spec["language"],
            "name": name,
        }
        self.km.kernel_name = name
        self.restart()

    def restart(self) -> "None":
        """Restarts the current `Notebook`'s kernel."""
        asyncio.run_coroutine_threadsafe(
            self._restart(),
            self.loop,
        )

    async def _restart(self) -> "None":
        await self.km.restart_kernel()
        log.debug(f"Kernel {self.km.kernel_id} restarted")

    def stop(self, cb: "Optional[Callable]" = None) -> "None":
        """Stops the current kernel.

        Args:
            cb: An optional callback to run when the kernel has stopped.

        """
        log.debug(f"Stopping kernel {self.km.kernel_id}")
        # This helps us leave a little earlier
        self.interrupt()
        asyncio.run_coroutine_threadsafe(
            self._stop(cb),
            self.loop,
        )

    async def _stop(self, cb: "Optional[Callable]" = None) -> "None":
        """Stop the kernel."""
        self.kc.stop_channels()
        await self.km.shutdown_kernel()
        log.debug(f"Kernel {self.km.kernel_id} shutdown")
        if callable(cb):
            cb()

    def shutdown(self) -> "None":
        """Shutdown the kernel and close the kernel's thread.

        This is intended to be run when the notebook is closed: the
        :py:class:`~euporie.notebook.NotebookKernel` cannot be restarted after this.

        """
        asyncio.run_coroutine_threadsafe(
            self._shutdown(),
            self.loop,
        )
        self.thread.join()

    async def _shutdown(self) -> "None":
        """Close the kernel's event loop."""
        await self.km.shutdown_kernel(now=True)
        self.loop.stop()
        self.loop.close()
        log.debug("Loop closed")
