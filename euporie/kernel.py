"""Contains the main class for a notebook file."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
from collections import defaultdict
from functools import partial
from subprocess import DEVNULL, STDOUT  # noqa S404 - Security implications considered
from typing import TYPE_CHECKING, TypedDict, cast

import nbformat  # type: ignore
from jupyter_client import (  # type: ignore
    AsyncKernelManager,
    KernelClient,
    KernelManager,
)
from jupyter_client.kernelspec import NoSuchKernel  # type: ignore
from jupyter_core.paths import jupyter_path  # type: ignore

if TYPE_CHECKING:
    from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, Union

    from euporie.tabs.notebook import KernelNotebook


__all__ = ["NotebookKernel"]

log = logging.getLogger(__name__)


class MsgCallbacks(TypedDict, total=False):
    get_input: "Optional[Callable[[str, bool], None]]"
    set_execution_count: "Optional[Callable[[int], None]]"
    add_output: "Optional[Callable[[List[Dict[str, Any]]], None]]"
    clear_output: "Optional[Callable[[bool], None]]"
    done: "Optional[Callable[[Dict[str, Any]], None]]"
    set_metadata: "Optional[Callable[[Tuple[str, ...], Any], None]]"
    set_status: "Optional[Callable[[str], None]]"
    set_kernel_info: "Optional[Callable[[Dict[str, Any]], None]]"


class NotebookKernel:
    """Runs a notebook kernel and communicates with it asynchronously.

    Has the ability to run itself in it's own thread.
    """

    def _setup_loop(self) -> "None":
        """Set the current loop the the kernel's event loop.

        This method is intended to be run in the kernel thread.
        """
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def __init__(
        self, nb: "KernelNotebook", threaded: "bool" = True, allow_stdin: "bool" = False
    ) -> "None":
        """Called when the :py:class:`NotebookKernel` is initialized.

        Args:
            name: The name of the kernel to start
            threaded: If :py:const:`True`, run kernel communication in a separate thread
            allow_stdin: Whether the kernel is allowed to request input

        """
        self.threaded = threaded
        if threaded:
            self.loop = asyncio.new_event_loop()
            self.thread = threading.Thread(target=self._setup_loop)
            self.thread.daemon = True
            self.thread.start()
        else:
            self.loop = asyncio.get_event_loop()

        self.allow_stdin = allow_stdin

        self.nb = nb
        self.kc: "Optional[KernelClient]" = None
        self.km = AsyncKernelManager(kernel_name=str(nb.kernel_name))
        self._status = "stopped"
        self.error: "Optional[Exception]" = None

        self.coros: "Dict[str, concurrent.futures.Future]" = {}
        self.poll_tasks: "list[asyncio.Task]" = []

        self.msg_id_callbacks: "Dict[str, MsgCallbacks]" = defaultdict(
            lambda: {
                "get_input": lambda prompt, password: self.nb.cell.get_input(
                    prompt, password
                ),
                "set_execution_count": lambda n: self.nb.cell.set_execution_count(n),
                "add_output": lambda output_json: self.nb.cell.add_output(output_json),
                "clear_output": lambda wait: self.nb.cell.clear_output(wait),
                "done": None,
                "set_metadata": lambda path, data: self.nb.cell.set_metadata(
                    path, data
                ),
                "set_status": lambda status: self.nb.cell.set_status(status),
            }
        )

        # Set the kernel folder list to prevent the default method from running.
        # This prevents the kernel spec manager from loading IPython, just for the
        # purpose of adding the depreciated :file:`.ipython/kernels` folder to the list
        # of kernel search paths. Without this, having IPython installed causes a
        # import race condition error where IPython was imported in the main thread for
        # displaying LaTex and in the kernel thread to discover kernel paths.
        # Also this speeds up launch since importing IPython is pretty slow.
        self.km.kernel_spec_manager.kernel_dirs = jupyter_path("kernels")

    def _aodo(
        self,
        coro: "Coroutine",
        wait: "bool" = False,
        callback: "Optional[Callable]" = None,
        timeout: "Optional[Union[int, float]]" = None,
        warn: "bool" = True,
        single: "bool" = False,
    ) -> "Any":
        """Schedules a coroutine in the kernel's event loop.

        Optionally waits for the results (blocking the main thread). Optionally
        schedules a callback to run when the coroutine has completed or timed out.

        Args:
            coro: The coroutine to run
            wait: If :py:const:`True`, block until the kernel has started
            callback: A function to run when the coroutine completes. The result from
                the coroutine will be passed as an argument
            timeout: The number of seconds to allow the coroutine to run if waiting
            warn: If :py:const:`True`, log an error if the coroutine times out
            single: If :py:const:`True`, any futures for previous instances of the
                coroutine will be cancelled

        Returns:
            The result of the coroutine

        """
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)

        # Cancel previous future instances if required
        if single and self.coros.get(coro.__name__):
            self.coros[coro.__name__].cancel()
        self.coros[coro.__name__] = future

        if wait:
            result = None
            try:
                result = future.result(timeout)
            except concurrent.futures.TimeoutError:
                log.error("Operation '%s' timed out", coro)
                future.cancel()
            finally:
                if callable(callback):
                    callback(result)
            return result
        else:
            if callable(callback):
                future.add_done_callback(
                    lambda f: callback(f.result()) if callback else None
                )

    def _set_living_status(self, alive: "bool") -> "None":
        """Set the life status of the kernel."""
        if not alive:
            self._status = "error"

    @property
    def status(self) -> "str":
        """Retrieve the current kernel status.

        Trigger a kernel life status check when retrieved

        Returns:
            The kernel status

        """
        # Check kernel is alive
        if self.km:
            self._aodo(
                self.km.is_alive(),
                timeout=0.2,
                callback=self._set_living_status,
                wait=False,
                warn=False,
            )

        return self._status

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
        """Get the ID of the current kernel."""
        if self.km.has_kernel:
            return self.km.kernel_id
        else:
            return None

    @property
    def specs(self) -> "dict[str, dict]":
        """Returns a list of available kernelspecs."""
        return self.km.kernel_spec_manager.get_all_specs()

    async def stop_(self, cb: "Optional[Callable[[], Any]]" = None) -> "None":
        """Stop the kernel asynchronously."""
        for task in self.poll_tasks:
            task.cancel()
        if self.kc is not None:
            self.kc.stop_channels()
        if self.km.has_kernel:
            await self.km.shutdown_kernel()
        log.debug("Kernel %s shutdown", self.id)

    async def start_(self) -> "None":
        """Start the kernel asynchronously and set its status."""
        log.debug("Starting kernel")
        self._status = "starting"
        try:
            # TODO - send stdout to log
            await self.km.start_kernel(stdout=DEVNULL, stderr=STDOUT)
        except Exception as e:
            log.exception("Kernel '%s' does not exist", self.km.kernel_name)
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
                log.exception("Error starting kernel")
                await self.stop_()
                self.error = e
                self._status = "error"
            else:
                log.debug("Kernel %s ready", self.id)
                self._status = "idle"
                self.error = None
                self.poll_tasks = [
                    asyncio.create_task(self.poll("shell")),
                    asyncio.create_task(self.poll("iopub")),
                    asyncio.create_task(self.poll("stdin")),
                ]

    def start(
        self, cb: "Optional[Callable]" = None, wait: "bool" = False, timeout: "int" = 10
    ) -> "None":
        """Starts the kernel.

        Args:
            cb: An optional callback to run after the kernel has started
            wait: If :py:const:`True`, block until the kernel has started
            timeout: How long to wait until failure is assumed

        """
        self._aodo(
            self.start_(),
            timeout=timeout,
            wait=wait,
            callback=cb,
        )

    async def poll(self, channel: "str") -> "None":
        """Polls for messages on a channel, and signal when they arrive.

        Args:
            channel: The name of the channel to get messages from

        """
        msg_getter_coro = getattr(self.kc, f"get_{channel}_msg")
        log.debug("Waiting for %s messages", channel)
        while True:
            # log.debug("Waiting for next %s message", channel)
            rsp = await msg_getter_coro()
            # Run msg type handler
            msg_type = rsp.get("header", {}).get("msg_type")
            if callable(handler := getattr(self, f"on_{channel}_{msg_type}", None)):
                handler(rsp)
            else:
                self.on_unhandled(channel, rsp)

    def on_unhandled(self, channel, rsp):
        log.debug(
            "Unhandled %s message:\nparent_id = '%s'\ntype = '%s'\ncontent='%s'",
            channel,
            rsp.get("parent_header", {}).get("msg_id"),
            rsp["header"]["msg_type"],
            rsp.get("content"),
        )

    def on_stdin_input_request(self, rsp) -> "None":
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        content = rsp.get("content", {})
        get_input = self.msg_id_callbacks[msg_id].get("get_input")
        if callable(get_input):
            get_input(
                content.get("prompt", ""),
                content.get("password", False),
            )

    def on_shell_status(self, rsp):
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        content = rsp.get("content", {})
        status = rsp.get("content", {}).get("status", "")
        if status == "ok":
            if callable(
                set_execution_count := self.msg_id_callbacks[msg_id].get(
                    "set_execution_count"
                )
            ):
                set_execution_count(content.get("execution_count"))

    def on_shell_execute_reply(self, rsp):
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        content = rsp.get("content", {})

        set_metadata = self.msg_id_callbacks[msg_id]["set_metadata"]
        set_metadata(
            ("execute", "shell", "execute_reply"),
            rsp["header"]["date"].isoformat(),
        )

        set_execution_count = self.msg_id_callbacks[msg_id]["set_execution_count"]
        set_execution_count(content.get("execution_count"))

        # Show pager output as a cell execution output
        if payloads := content.get("payload", []):
            add_output = self.msg_id_callbacks[msg_id]["add_output"]
            for payload in payloads:
                if data := payload.get("data", {}):
                    add_output(
                        nbformat.v4.new_output(
                            "execute_result",
                            data=data,
                        )
                    )

        if content.get("status") == "ok":
            if callable(done := self.msg_id_callbacks[msg_id].get("done")):
                done(content)

    def on_shell_kernel_info_reply(self, rsp):
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(done := self.msg_id_callbacks[msg_id].get("done")):
            done(rsp.get("content", {}))

    def on_shell_complete_reply(self, rsp):
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(done := self.msg_id_callbacks[msg_id].get("done")):
            done(rsp.get("content", {}))

    def on_shell_history_reply(self, rsp):
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(done := self.msg_id_callbacks[msg_id].get("done")):
            done(rsp.get("content", {}))

    def on_shell_inspect_reply(self, rsp):
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(done := self.msg_id_callbacks[msg_id].get("done")):
            done(rsp.get("content", {}))

    def on_iopub_status(self, rsp):
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        status = rsp.get("content", {}).get("execution_state")

        self._status = status
        if callable(set_status := self.msg_id_callbacks[msg_id].get("set_status")):
            set_status(status)

        if status == "idle":
            if callable(
                set_metadata := self.msg_id_callbacks[msg_id].get("set_metadata")
            ):
                set_metadata(
                    ("iopub", "status", "idle"),
                    rsp["header"]["date"].isoformat(),
                )

        elif status == "busy":
            if callable(
                set_metadata := self.msg_id_callbacks[msg_id].get("set_metadata")
            ):
                set_metadata(
                    ("iopub", "status", "busy"),
                    rsp["header"]["date"].isoformat(),
                )

    def on_iopub_execute_input(self, rsp):
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        set_metadata = self.msg_id_callbacks[msg_id]["set_metadata"]
        set_metadata(
            ("iopub", "execute_input"),
            rsp["header"]["date"].isoformat(),
        )

    def on_iopub_display_data(self, rsp):
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        add_output = self.msg_id_callbacks[msg_id]["add_output"]
        add_output(nbformat.v4.output_from_msg(rsp))

    def on_iopub_update_display_data(self, rsp):
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        add_output = self.msg_id_callbacks[msg_id]["add_output"]
        add_output(nbformat.v4.output_from_msg(rsp))

    def on_iopub_execute_result(self, rsp):
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        add_output = self.msg_id_callbacks[msg_id]["add_output"]
        add_output(nbformat.v4.output_from_msg(rsp))

        set_execution_count = self.msg_id_callbacks[msg_id]["set_execution_count"]
        set_execution_count(rsp.get("content", {}).get("execution_count"))

    def on_iopub_error(self, rsp):
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(add_output := self.msg_id_callbacks[msg_id].get("add_output")):
            add_output(nbformat.v4.output_from_msg(rsp))
        if callable(done := self.msg_id_callbacks[msg_id].get("done")):
            done(rsp.get("content"))

    def on_iopub_stream(self, rsp):
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        add_output = self.msg_id_callbacks[msg_id]["add_output"]
        add_output(nbformat.v4.output_from_msg(rsp))

    def on_iopub_clear_output(self, rsp):
        # Clear cell output, either now or when we get the next output
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        clear_output = self.msg_id_callbacks[msg_id]["clear_output"]
        clear_output(rsp.get("content", {}).get("wait", False))

    def on_iopub_comm_open(self, rsp):
        # TODO
        # "If the target_name key is not found on the receiving side, then it should
        # immediately reply with a comm_close message to avoid an inconsistent state."
        #
        self.nb.comm_open(
            content=rsp.get("content", {}), buffers=rsp.get("buffers", [])
        )

    def on_iopub_comm_msg(self, rsp):
        self.nb.comm_msg(content=rsp.get("content", {}), buffers=rsp.get("buffers", []))

    def on_iopub_comm_close(self, rsp):
        self.nb.comm_close(
            content=rsp.get("content", {}), buffers=rsp.get("buffers", [])
        )

    ####################################

    def kc_comm(self, comm_id, data):
        """Send a comm message on the shell channel."""
        content = {
            "comm_id": comm_id,
            "data": data,
        }
        msg = self.kc.session.msg("comm_msg", content)
        self.kc.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def run(
        self,
        source: "str",
        wait: "bool" = False,
        **callbacks: "Callable[..., Any]",
    ) -> "None":
        """Run a cell using the notebook kernel and process the responses."""
        if self.kc is None:
            log.debug("Cannot run cell because kernel has not started")
            # TODO - queue cells for execution
        else:
            self._aodo(
                self.run_(source, **callbacks),
                wait=wait,
            )

    async def run_(
        self,
        source: "str",
        get_input: "Optional[Callable[[str, bool], None]]" = None,
        set_execution_count: "Optional[Callable[[int], None]]" = None,
        add_output: "Optional[Callable[[List[Dict[str, Any]]], None]]" = None,
        clear_output: "Optional[Callable[[bool], None]]" = None,
        done: "Optional[Callable[[Dict[str, Any]], None]]" = None,
        set_metadata: "Optional[Callable[[Tuple[str, ...], Any], None]]" = None,
        set_status: "Optional[Callable[[str], None]]" = None,
    ) -> "None":
        """Runs the code cell and and set the response callbacks, optionally waiting."""
        if self.kc is None:
            return
        event = asyncio.Event()
        msg_id = self.kc.execute(
            source,
            store_history=True,
            allow_stdin=self.allow_stdin,
        )

        def wrapped_done(content) -> "None":
            # Run the original callback
            if callable(done):
                done(content)
            # Set the event
            event.set()

        self.msg_id_callbacks[msg_id].update(
            MsgCallbacks(
                get_input=get_input,
                set_execution_count=set_execution_count,
                add_output=add_output,
                clear_output=clear_output,
                set_metadata=set_metadata,
                set_status=set_status,
                done=wrapped_done,
            )
        )
        # Wait for "done" callback to be called
        try:
            await asyncio.wait_for(event.wait(), timeout=None)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for kernel info response")

        # Clean up callbacks
        # await asyncio.sleep(0.1)
        # if msg_id in self.msg_id_callbacks:
        # del self.msg_id_callbacks[msg_id]

    def info(
        self,
        set_kernel_info: "Optional[Callable[[Dict[str, Any]], None]]" = None,
        set_status: "Optional[Callable[[str], None]]" = None,
    ) -> "None":
        """Request information about the kernel."""
        if self.kc is not None:
            msg_id = self.kc.kernel_info()
            self.msg_id_callbacks[msg_id].update(
                MsgCallbacks(set_kernel_info=set_kernel_info, set_status=set_status)
            )

    async def complete_(
        self, code: "str", cursor_pos: "int", timeout: "int" = 60
    ) -> "list[dict]":
        """Request code completions from the kernel, asynchronously."""
        results: "list[dict]" = []
        if not self.kc:
            return results

        event = asyncio.Event()

        def process_complete_reply(content) -> "None":
            """Process response messages on the ``shell`` channel."""
            status = content.get("status", "")
            if status == "ok":
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
                event.set()

        msg_id = self.kc.complete(code, cursor_pos)
        self.msg_id_callbacks[msg_id].update({"done": process_complete_reply})

        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for kernel info response")

        return results

    def complete(self, code: "str", cursor_pos: "int") -> "list[dict]":
        """Request code completions from the kernel.

        Args:
            code: The code string to retrieve completions for
            cursor_pos: The position of the cursor in the code string

        Returns:
            A list of dictionaries defining completion entries. The dictionaries
            contain ``text`` (the completion text), ``start_position`` (the stating
            position of the completion text), and optionally ``display_meta``
            (a string containing additional data about the completion type)

        """
        return self._aodo(
            self.complete_(code, cursor_pos),
            wait=True,
            single=True,
        )

    async def history_(
        self, pattern: "str", n: "int" = 1, timeout: "int" = 60
    ) -> "Optional[list[tuple[int, int, str]]]":
        """Retrieve history from the kernel asynchronously."""
        await asyncio.sleep(0.1)  # Add a tiny timeout so we don't spam the kernel

        results: "list[tuple[int, int, str]]" = []

        if not self.kc:
            return results

        event = asyncio.Event()

        def process_history_reply(content) -> "None":
            """Process responses on the shell channel."""
            status = content.get("status", "")
            if status == "ok":
                for item in content.get("history", []):
                    results.append(item)
                    event.set()

        msg_id = self.kc.history(pattern=pattern, n=n, hist_access_type="search")
        self.msg_id_callbacks[msg_id].update({"done": process_history_reply})

        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for kernel info response")

        return results

    def history(
        self, pattern: "str", n: "int" = 1
    ) -> "Optional[list[tuple[int, int, str]]]":
        """Retrieve history from the kernel.

        Args:
            pattern: The pattern to search for
            n: the number of history items to return

        Returns:
            A list of history items, consisting of tuples (session, line_number, input)

        """
        return self._aodo(
            self.history_(pattern, n),
            wait=True,
            single=True,
        )

    async def inspect_(
        self,
        code: "str",
        cursor_pos: "int",
        detail_level: "int" = 0,
        timeout: "int" = 2,
    ) -> "dict[str, Any]":
        """Retrieve introspection string from the kernel asynchronously."""
        await asyncio.sleep(0.1)  # Add a tiny timeout so we don't spam the kernel

        result: "dict[str, Any]" = {}

        if not self.kc:
            return result

        event = asyncio.Event()

        def process_inspect_reply(content) -> "None":
            """Process responses on the shell channel."""
            status = content.get("status", "")
            if status == "ok":
                if content.get("found", False):
                    result.update(content)
                    event.set()

        msg_id = self.kc.inspect(code, cursor_pos=cursor_pos, detail_level=detail_level)
        self.msg_id_callbacks[msg_id].update({"done": process_inspect_reply})
        log.debug(self.msg_id_callbacks[msg_id])

        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for kernel info response")

        return result

    def inspect(
        self,
        code: "str",
        cursor_pos: "int",
        callback: "Optional[Callable[[dict[str, Any]], None]]" = None,
    ) -> "str":
        """Request code inspection from the kernel.

        Args:
            code: The code string to retrieve completions for
            cursor_pos: The position of the cursor in the code string
            callback: A function to run when the inspection result arrives. The result
                is passed as an argument.

        Returns:
            A string containing useful information about the code at the current cursor
            position

        """
        return self._aodo(
            self.inspect_(code, cursor_pos),
            wait=False,
            callback=callback,
            single=True,
        )

    def interrupt(self) -> "None":
        """Interrupt the kernel.

        This is run in the main thread rather than on the event loop in the kernel's thread,
        because otherwise we would have to wait for currently running tasks on the
        kernel's event loop to finish.
        """
        if self.km.has_kernel:
            log.debug("Interrupting kernel %s", self.id)
            KernelManager.interrupt_kernel(self.km)

    async def restart_(self) -> "None":
        """Restart the kernel asyncchronously."""
        await self.km.restart_kernel()
        log.debug("Kernel %s restarted", self.id)

    def restart(self, wait: "bool" = False) -> "None":
        """Restarts the current kernel."""
        self._aodo(
            self.restart_(),
            wait=wait,
        )

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
            self._aodo(
                self.stop_(),
                callback=cb,
                wait=wait,
            )

    async def shutdown_(self) -> "None":
        """Shut down the kernel and close the event loop if running in a thread."""
        if self.km.has_kernel:
            await self.km.shutdown_kernel(now=True)
        if self.threaded:
            self.loop.stop()
            self.loop.close()
            log.debug("Loop closed")

    def shutdown(self, wait: "bool" = False) -> "None":
        """Shutdown the kernel and close the kernel's thread.

        This is intended to be run when the notebook is closed: the
        :py:class:`~euporie.tabs.notebook.NotebookKernel` cannot be restarted after this.

        Args:
            wait: Whether to block until shutdown completes

        """
        self._aodo(
            self.shutdown_(),
            wait=wait,
        )
        if self.threaded:
            self.thread.join(timeout=5)
