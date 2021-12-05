# -*- coding: utf-8 -*-
"""Contains the main class for a notebook file."""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
import time
from concurrent.futures import Future
from contextlib import asynccontextmanager
from functools import partial
from typing import AsyncGenerator, Callable, Optional

import nbformat  # type: ignore
from jupyter_client import (  # type: ignore
    AsyncKernelManager,
    KernelClient,
    KernelManager,
)
from jupyter_client.kernelspec import NoSuchKernel  # type: ignore

log = logging.getLogger(__name__)


class NotebookKernel:
    """Runs a notebook kernel and communicates with it asynchronously.

    Has the ability to run itself in it's own thread.
    """

    def __init__(self, name: "str", threaded=False) -> None:
        """Called when the ``NotebookKernel`` is initalized.

        Args:
            name: The name of the kernel to start

        """
        self.threaded = threaded
        if threaded:
            self.loop = asyncio.new_event_loop()
            self.thread = threading.Thread(target=self._setup_loop)
            self.thread.daemon = True
            self.thread.start()
        else:
            self.loop = asyncio.get_event_loop()

        self.kc: "Optional[KernelClient]" = None
        self.km = AsyncKernelManager(kernel_name=name)
        self._status = "stopped"
        self.error: "Optional[RuntimeError]" = None

        self.poll_tasks = []
        self.events = {}
        self.msgs = {}

    def aodo(
        self,
        coro,
        wait: "bool" = False,
        callback=None,
        timeout: "Optional[int]" = None,
        warn=True,
    ):
        if wait:
            task = asyncio.run_coroutine_threadsafe(coro, self.loop)
            result = None
            try:
                result = task.result(timeout)
            except concurrent.futures.TimeoutError:
                if warn:
                    log.error("Operation '%s' timed out", coro)
                task.cancel()
            finally:
                if callable(callback):
                    callback(result)
                return result
        else:
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            if callable(callback):
                future.add_done_callback(lambda f: callback(f.result()))

    @property
    def status(self):
        # Check kernel is alive
        if self.km:
            self.aodo(
                self.km.is_alive(),
                timeout=0.2,
                callback=self._set_living_status,
                wait=False,
                warn=False,
            )

        return self._status

    def _set_living_status(self, alive):
        if not alive:
            self._status = "error"

    @property
    def missing(self) -> "bool":
        """Returns a list of available kernelspecs."""
        if self.km:
            try:
                self.km.kernel_spec
            except NoSuchKernel:
                return True
            else:
                return False
        else:
            return False

    @property
    def id(self) -> "Optional[str]":
        if self.km.has_kernel:
            return self.km.kernel_id

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

    def start(self, cb: "Optional[Callable]" = None, wait: "bool" = False) -> "None":
        """Starts the kernel.

        Args:
            cb: An optional callback to run after the kernel has started

        """
        self.aodo(
            self.start_(cb),
            timeout=10,
            wait=wait,
            callback=cb,
        )

    async def start_(self, cb: "Optional[Callable]" = None) -> "None":
        """Start the kernel and set its status."""
        log.debug("Starting kernel")
        self._status = "starting"
        try:
            await self.km.start_kernel()
        except Exception as e:
            log.error("Kernel '%s' does not exist", self.km.kernel_name)
            self._status = "error"
            self.error = e
        else:
            log.debug("Started kernel")

        if self.km.has_kernel:
            self.kc = self.km.client()
            self.kc.start_channels()
            log.debug("Waiting for kernel to become ready")
            try:
                await self.kc.wait_for_ready(timeout=10)
            except RuntimeError as e:
                await self.stop_()
                self.error = e
                self._status = "error"
            else:
                log.debug("Kernel %s ready", self.id)
                self._status = "idle"
                self.error = None
                self.poll_tasks = [
                    asyncio.create_task(
                        self.poll(self.kc.get_shell_msg, channel="shell")
                    ),
                    asyncio.create_task(
                        self.poll(self.kc.get_iopub_msg, channel="iopub")
                    ),
                ]
                log.debug(self.poll_tasks)

    async def poll(self, msg_getter_coro, channel):
        self.events[channel] = {}
        self.msgs[channel] = {}
        log.debug("Waiting for %s messages", channel)
        while True:
            log.debug("Waiting for next %s message", channel)
            msg = await msg_getter_coro()
            msg_id = msg["parent_header"].get("msg_id")
            # log.debug("Got message in response to %s", msg_id)
            if msg_id in self.events[channel]:
                self.msgs[channel][msg_id] = msg
                self.events[channel][msg_id].set()
            else:
                log.debug(
                    "Got stray %s message:\ntype = '%s', content = '%s'",
                    channel,
                    msg["header"]["msg_type"],
                    msg.get("content"),
                )
                log.debug(self.events[channel])

    async def await_rsps(self, msg_id, channel):
        self.events[channel][msg_id] = asyncio.Event()
        log.debug("Waiting for %s response to %s", channel, msg_id[-7:])
        while msg_id in self.events[channel]:
            event = self.events[channel][msg_id]
            log.debug("Waiting for event on %s channel", channel)
            await self.events[channel][msg_id].wait()
            log.debug("Event occured on channel %s", channel)
            rsp = self.msgs[channel][msg_id]
            del self.msgs[channel][msg_id]
            log.debug(
                "Got shell response:\ntype = '%s', content = '%s'",
                rsp["header"]["msg_type"],
                rsp.get("content"),
            )
            try:
                yield rsp
            except StopIteration:
                del self.events[channel][msg_id]
            finally:
                event.clear()

    async def await_iopub_rsps(self, msg_id):
        async for rsp in self.await_rsps(msg_id, channel="iopub"):
            stop = False
            msg_type = rsp.get("header", {}).get("msg_type")
            if msg_type == "status":
                status = rsp.get("content", {}).get("execution_state")
                self._status = status
                if status == "idle":
                    stop = True
            elif msg_type == "error":
                stop = True
            try:
                yield rsp
            except StopIteration:
                log.debug("Stopped early?")
                break
            else:
                if stop:
                    break

    async def await_shell_rsps(self, msg_id):
        async for rsp in self.await_rsps(msg_id, channel="shell"):
            stop = False
            status = rsp.get("content", {}).get("status")
            if status == "ok":
                stop = True
            elif msg_type == "error":
                stop = True
            try:

                yield rsp
            except StopIteration:
                log.debug("Stopped early?")
                break
            else:
                if stop:
                    break

    async def process_default_iopub_rsp(self, msg_id):
        async for rsp in self.await_iopub_rsps(msg_id):
            pass

    def run(
        self,
        cell_json: "dict",
        output_cb: "Optional[Callable]" = None,
        done_cb: "Optional[Callable]" = None,
        wait: "bool" = False,
    ) -> "None":
        """Run a cell using the notebook kernel.

        Args:
            cell_json: The JSON representation of the cell to run
            output_cb: An optional callback to run after each response message
            cb: An optional callback to run when the cell has finished running

        """
        if self.kc is None:
            log.debug("Cannot run cell because kernel has not started")
        else:
            self.aodo(
                self.run_(
                    cell_json=cell_json,
                    output_cb=output_cb,
                    done_cb=done_cb,
                ),
                wait=wait,
            )

    async def run_(self, cell_json, output_cb, done_cb):
        """"""
        msg_id = self.kc.execute(
            cell_json.get("source"),
            store_history=True,
            allow_stdin=False,
        )

        async def process_execute_shell_rsp():
            async for rsp in self.await_shell_rsps(msg_id):
                status = rsp.get("content", {}).get("status", "")
                if status == "ok":
                    cell_json["execution_count"] = rsp.get("content", {}).get(
                        "execution_count"
                    )

        async def process_execute_iopub_rsp():
            async for rsp in self.await_iopub_rsps(msg_id):
                stop = False
                log.debug(
                    "Got iopub response:\ntype = '%s', content = '%s'",
                    rsp["header"]["msg_type"],
                    rsp.get("content"),
                )
                msg_type = rsp.get("header", {}).get("msg_type")
                if msg_type in ("display_data", "execute_result", "error"):
                    cell_json.setdefault("outputs", []).append(
                        nbformat.v4.output_from_msg(rsp)
                    )
                    if msg_type == "execute_result":
                        cell_json["execution_count"] = rsp.get("content", {}).get(
                            "execution_count"
                        )
                    elif msg_type == "error":
                        stop = True
                elif msg_type == "stream":
                    # Combine stream outputs
                    stream_name = rsp.get("content", {}).get("name")
                    for output in cell_json.get("outputs", []):
                        if output.get("name") == stream_name:
                            output["text"] = output.get("text", "") + rsp.get(
                                "content", {}
                            ).get("text", "")
                            break
                    else:
                        cell_json.setdefault("outputs", []).append(
                            nbformat.v4.output_from_msg(rsp)
                        )
                elif msg_type == "status":
                    if rsp.get("content", {}).get("execution_state") == "idle":
                        done_cb()
                        break
                if callable(output_cb):
                    log.debug("Calling callback")
                    output_cb()
                if stop:
                    break

        await asyncio.gather(
            process_execute_shell_rsp(),
            process_execute_iopub_rsp(),
            return_exceptions=True,
        )

    def complete(self, code: "str", cursor_pos: "int") -> "Generator":
        return self.aodo(
            self.complete_(code, cursor_pos),
            wait=True,
        )

    async def complete_(self, code: "str", cursor_pos: "int"):  # -> "AsyncGenerator":
        """Request code completions from the kernel."""
        results = []
        if not self.kc:
            return results

        msg_id = self.kc.complete(code, cursor_pos)

        async def process_complete_shell_rsp():
            async for rsp in self.await_shell_rsps(msg_id):
                status = rsp.get("content", {}).get("status", "")
                if status == "ok":
                    content = rsp.get("content", {})
                    jupyter_types = content.get("metadata", {}).get(
                        "_jupyter_types_experimental"
                    )
                    if jupyter_types:
                        for match in jupyter_types:
                            rel_start_position = match.get("start", 0) - cursor_pos
                            completion_type = match.get("type")
                            completion_type = (
                                None
                                if completion_type == "<unknown>"
                                else completion_type
                            )
                            results.append(
                                {
                                    "text": match.get("text"),
                                    "start_position": rel_start_position,
                                    "display_meta": completion_type,
                                }
                            )
                    else:
                        rel_start_position = content.get("cursor_start", 0) - cursor_pos
                        for match in content.get("matches", []):
                            results.append(
                                {"text": match, "start_position": rel_start_position}
                            )

        objs = await asyncio.gather(
            process_complete_shell_rsp(),
            self.process_default_iopub_rsp(msg_id),
            return_exceptions=True,
        )
        log.debug(objs)
        return results

    def history(
        self, pattern: "str", n: "int" = 1
    ) -> "Optional[list[tuple[int, int, str]]]":
        return self.aodo(
            self.history_(pattern, n),
            wait=True,
        )

    async def history_(
        self, pattern: "str", n: "int" = 1
    ) -> "Optional[list[tuple[int, int, str]]]":

        results: "list[tuple[int, int, str]]" = []

        if not self.kc:
            return results

        msg_id = self.kc.history(pattern=pattern, n=n, hist_access_type="search")

        async def process_history_shell_rsp():
            async for rsp in self.await_shell_rsps(msg_id):
                status = rsp.get("content", {}).get("status", "")
                if status == "ok":
                    for item in rsp.get("content", {}).get("history", []):
                        results.append(item)

        await asyncio.gather(
            process_history_shell_rsp(),
            self.process_default_iopub_rsp(msg_id),
            return_exceptions=True,
        )
        return results

    def interrupt(self) -> "None":
        """Interrupt the kernel.

        This is run in the main thread rather than on the event loop in the kernel's thread,
        because otherwise we would have to wait for currently running tasks on the
        kernel's event loop to finish.
        """
        if self.km.has_kernel:
            log.debug("Interrupting kernel %s", self.id)
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
        if self.km.has_kernel:
            self.restart()
        else:
            self.start()

    def restart(self, wait: "bool" = False) -> "None":
        """Restarts the current `Notebook`'s kernel."""
        self.aodo(
            self.restart_(),
            wait=wait,
        )

    async def restart_(self) -> "None":
        await self.km.restart_kernel()
        log.debug("Kernel %s restarted", self.id)

    def stop(self, cb: "Optional[Callable]" = None, wait: "bool" = False) -> "None":
        """Stops the current kernel.

        Args:
            cb: An optional callback to run when the kernel has stopped.
            wait: If True, wait for the kernel to become idle, otherwise the kernel is
                interrupted before it is stopped

        """
        if self.km.has_kernel is None:
            log.debug("Cannot stop kernel because it is not running")
            if callable(cb):
                cb()
        else:
            log.debug("Stopping kernel %s (wait=%s)", self.id, wait)
            # This helps us leave a little earlier
            if not wait:
                self.interrupt()
            self.aodo(
                self.stop_(),
                callback=cb,
                wait=wait,
            )

    async def stop_(self, cb: "Optional[Callable]" = None) -> "None":
        """Stop the kernel."""
        for task in self.poll_tasks:
            task.cancel()
        if self.kc is not None:
            self.kc.stop_channels()
        if self.km.has_kernel:
            await self.km.shutdown_kernel()
        log.debug("Kernel %s shutdown", self.id)

    def shutdown(self, wait: "bool" = False) -> "None":
        """Shutdown the kernel and close the kernel's thread.

        This is intended to be run when the notebook is closed: the
        :py:class:`~euporie.notebook.NotebookKernel` cannot be restarted after this.

        """
        self.aodo(
            self.shutdown_(),
            wait=wait,
        )
        if self.threaded:
            self.thread.join(timeout=5)

    async def shutdown_(self) -> "None":
        """Close the kernel's event loop."""
        if self.km.has_kernel:
            await self.km.shutdown_kernel(now=True)
        if self.threaded:
            self.loop.stop()
            self.loop.close()
            log.debug("Loop closed")
