"""Contains the main class for a notebook file."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
from collections import defaultdict
from subprocess import DEVNULL  # noqa S404 - Security implications considered
from typing import TYPE_CHECKING, TypedDict

import nbformat
from _frozen_importlib import _DeadlockError
from jupyter_client import AsyncKernelManager, KernelManager
from jupyter_client.kernelspec import NATIVE_KERNEL_NAME, NoSuchKernel
from jupyter_core.paths import jupyter_path

from euporie.core.config import add_setting

if TYPE_CHECKING:
    from typing import Any, Callable, Coroutine, Optional, Union

    from jupyter_client import KernelClient

    from euporie.core.comm.base import KernelTab


log = logging.getLogger(__name__)


class MsgCallbacks(TypedDict, total=False):
    """Typed dictionary for named message callbacks."""

    get_input: "Callable[[str, bool], None]|None"
    set_execution_count: "Callable[[int], None]|None"
    add_output: "Callable[[dict[str, Any]], None]|None"
    clear_output: "Callable[[bool], None]|None"
    done: "Callable[[dict[str, Any]], None]|None"
    set_metadata: "Callable[[tuple[str, ...], Any], None]|None"
    set_status: "Callable[[str], None]|None"
    set_kernel_info: "Callable[[dict[str, Any]], None]|None"
    completeness_status: "Callable[[dict[str, Any]], None]|None"


class Kernel:
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
        self,
        kernel_tab: "KernelTab",
        threaded: "bool" = True,
        allow_stdin: "bool" = False,
        default_callbacks: "Optional[MsgCallbacks]" = None,
    ) -> "None":
        """Called when the :py:class:`Kernel` is initialized.

        Args:
            kernel_tab: The notebook this kernel belongs to
            threaded: If :py:const:`True`, run kernel communication in a separate thread
            allow_stdin: Whether the kernel is allowed to request input
            default_callbacks: The default callbacks to use on recipt of a message

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

        self.kernel_tab = kernel_tab
        self.kc: "Optional[KernelClient]" = None
        self.km = AsyncKernelManager(
            kernel_name=str(kernel_tab.kernel_name),
        )
        self._status = "stopped"
        self.error: "Optional[Exception]" = None

        self.coros: "dict[str, concurrent.futures.Future]" = {}
        self.poll_tasks: "list[asyncio.Task]" = []

        self.default_callbacks = MsgCallbacks(
            {
                "get_input": None,
                "set_execution_count": None,
                "add_output": None,
                "clear_output": None,
                "done": None,
                "set_metadata": None,
                "set_status": None,
            }
        )
        if default_callbacks is not None:
            self.default_callbacks.update(default_callbacks)

        self.msg_id_callbacks: "dict[str, MsgCallbacks]" = defaultdict(
            # Return a copy of the default callbacks
            lambda: MsgCallbacks(dict(self.default_callbacks))  # type: ignore # mypy #8890
        )

        # Set the kernel folder list to prevent the default method from running.
        # This prevents the kernel spec manager from loading IPython, just for the
        # purpose of adding the depreciated :file:`.ipython/kernels` folder to the list
        # of kernel search paths. Without this, having IPython installed causes a
        # import race condition error where IPython was imported in the main thread for
        # displaying LaTeX and in the kernel thread to discover kernel paths.
        # Also this speeds up launch since importing IPython is pretty slow.
        self.km.kernel_spec_manager.kernel_dirs = jupyter_path("kernels")

        self.status_change_event = asyncio.Event()

    def _aodo(
        self,
        coro: "Coroutine",
        wait: "bool" = False,
        callback: "Optional[Callable]" = None,
        timeout: "Optional[Union[int, float]]" = None,
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
            self.status = "error"

    @property
    def status(self) -> "str":
        """Retrieve the current kernel status.

        Trigger a kernel life status check when retrieved

        Returns:
            The kernel status

        """
        # Check kernel is alive - use client rather than manager if we have one, as we
        # could be connected to a kernel which we was not started by the manager
        self._aodo(
            self.km.is_alive(),
            timeout=0.2,
            callback=self._set_living_status,
            wait=False,
        )

        return self._status

    @status.setter
    def status(self, value: "str") -> "None":
        """Set the kernel status."""
        self.status_change_event.set()
        self._status = value
        self.status_change_event.clear()

    def wait_for_status(self, status: "str" = "idle") -> "None":
        """Block until the kernel reasches a given status value."""
        if self.status != status:

            async def _wait() -> "None":
                while self.status != status:
                    await asyncio.wait_for(
                        self.status_change_event.wait(), timeout=None
                    )

            self._aodo(_wait(), wait=True)

    @property
    def missing(self) -> "bool":
        """Return True if the requested kernel is not found."""
        try:
            self.km.kernel_spec
        except NoSuchKernel:
            return True
        else:
            return self.km.kernel_spec is None

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
        if self.km.kernel_name is None:
            self.status = "error"
        log.debug("Starting kernel")
        self.status = "starting"

        # If we are connecting to an existing kernel, create a kernel client using
        # the given connection file
        if self.kernel_tab.app.config.kernel_connection_file:
            connection_file = self.kernel_tab.app.config.kernel_connection_file
            self.km.load_connection_file(connection_file)
            kc = self.km.client_factory(connection_file=connection_file)
            kc.load_connection_file()
            kc.start_channels()
            self.kc = kc

        # Otherwise, start a new kernel using the kernel manager
        else:
            while True:
                try:
                    # TODO - send stdout to log
                    await self.km.start_kernel(stdout=DEVNULL, stderr=DEVNULL)
                except _DeadlockError:
                    # Keep trying if we get an import deadlock
                    continue
                except Exception as e:
                    log.exception("Kernel '%s' could not start", self.km.kernel_name)
                    self.status = "error"
                    self.error = e
                else:
                    log.debug("Started kernel")
                    # Create a client for the newly started kernel
                    if self.km.has_kernel:
                        self.kc = self.km.client()
                break
        try:
            ks = self.km.kernel_spec
        except NoSuchKernel as e:
            self.error = e
            self.status = "error"
        else:
            if ks is not None:
                self.kernel_tab.metadata["kernelspec"] = {
                    "name": self.km.kernel_name,
                    "display_name": ks.display_name,
                    "language": ks.language,
                }

        if self.kc and self.status != "error":
            log.debug("Waiting for kernel to become ready")
            try:
                await self.kc._async_wait_for_ready(timeout=10)
            except RuntimeError as e:
                log.exception("Error connecting to kernel")
                await self.stop_()
                self.error = e
                self.status = "error"
            else:
                log.debug("Kernel %s ready", self.id)
                self.status = "idle"
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
        # Attempt to import ipykernel if it is installed
        # ipykernel is imported by jupyter_client, but since starting the kernel runs
        # in another thread, we do the import here first to prevent import deadlocks,
        # which sometimes occur as we import ipython elsewhere in the main thread
        if self.kernel_tab.kernel_name == NATIVE_KERNEL_NAME:
            try:
                from ipykernel import kernelspec  # noqa F401

                log.debug("Imported `ipykernel` to prevent import deadlock")
            except ImportError:
                pass

        # Start the kernel
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

    def on_unhandled(self, channel: "str", rsp: "dict[str, Any]") -> "None":
        """Report unhandled messages to the debug log."""
        log.debug(
            "Unhandled %s message:\nparent_id = '%s'\ntype = '%s'\ncontent='%s'",
            channel,
            rsp.get("parent_header", {}).get("msg_id"),
            rsp["header"]["msg_type"],
            rsp.get("content"),
        )

    def on_stdin_input_request(self, rsp: "dict[str, Any]") -> "None":
        """Call ``get_input`` callback for a stdin input request message."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        content = rsp.get("content", {})
        if callable(get_input := self.msg_id_callbacks[msg_id].get("get_input")):
            get_input(
                content.get("prompt", ""),
                content.get("password", False),
            )

    def on_shell_status(self, rsp: "dict[str, Any]") -> "None":
        """Call ``set_execution_count`` callback for a shell status response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        content = rsp.get("content", {})
        status = rsp.get("content", {}).get("status", "")
        if status == "ok":
            if execution_count := content.get("execution_count"):
                if callable(
                    set_execution_count := self.msg_id_callbacks[msg_id].get(
                        "set_execution_count"
                    )
                ):
                    set_execution_count(execution_count)

    def on_shell_execute_reply(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for a shell execute reply response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        content = rsp.get("content", {})

        if callable(set_metadata := self.msg_id_callbacks[msg_id]["set_metadata"]):
            set_metadata(
                ("execute", "shell", "execute_reply"),
                rsp["header"]["date"].isoformat(),
            )

        if execution_count := content.get("execution_count"):
            if callable(
                set_execution_count := self.msg_id_callbacks[msg_id][
                    "set_execution_count"
                ]
            ):
                set_execution_count(execution_count)

        # Show pager output as a cell execution output
        if payloads := content.get("payload", []):
            if callable(add_output := self.msg_id_callbacks[msg_id]["add_output"]):
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

    def on_shell_kernel_info_reply(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for a shell kernel info response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(
            set_kernel_info := self.msg_id_callbacks[msg_id].get("set_kernel_info")
        ):
            set_kernel_info(rsp.get("content", {}))

    def on_shell_complete_reply(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for a shell completion reply response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(done := self.msg_id_callbacks[msg_id].get("done")):
            done(rsp.get("content", {}))

    def on_shell_history_reply(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for a shell history reply response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(done := self.msg_id_callbacks[msg_id].get("done")):
            done(rsp.get("content", {}))

    def on_shell_inspect_reply(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for a shell inspection reply response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(done := self.msg_id_callbacks[msg_id].get("done")):
            done(rsp.get("content", {}))

    def on_shell_is_complete_reply(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for a shell completeness reply response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(
            completeness_status := self.msg_id_callbacks[msg_id].get(
                "completeness_status"
            )
        ):
            completeness_status(rsp.get("content", {}))

    def on_iopub_status(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for an iopub status response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        status = rsp.get("content", {}).get("execution_state")

        self.status = status
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

    def on_iopub_execute_input(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for an iopub execute input response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(set_metadata := self.msg_id_callbacks[msg_id]["set_metadata"]):
            set_metadata(
                ("iopub", "execute_input"),
                rsp["header"]["date"].isoformat(),
            )

    def on_iopub_display_data(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for an iopub display data response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(add_output := self.msg_id_callbacks[msg_id]["add_output"]):
            add_output(nbformat.v4.output_from_msg(rsp))

    def on_iopub_update_display_data(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for an iopub update display data response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(add_output := self.msg_id_callbacks[msg_id]["add_output"]):
            add_output(nbformat.v4.output_from_msg(rsp))

    def on_iopub_execute_result(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for an iopub execute result response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(add_output := self.msg_id_callbacks[msg_id]["add_output"]):
            add_output(nbformat.v4.output_from_msg(rsp))

        if execution_count := rsp.get("content", {}).get("execution_count"):
            if callable(
                set_execution_count := self.msg_id_callbacks[msg_id][
                    "set_execution_count"
                ]
            ):
                set_execution_count(execution_count)

    def on_iopub_error(self, rsp: "dict[str, dict[str, Any]]") -> "None":
        """Call callbacks for an iopub error response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id", "")
        if callable(add_output := self.msg_id_callbacks[msg_id].get("add_output")):
            add_output(nbformat.v4.output_from_msg(rsp))
        if callable(done := self.msg_id_callbacks[msg_id].get("done")):
            done(rsp.get("content", {}))

    def on_iopub_stream(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for an iopub stream response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(add_output := self.msg_id_callbacks[msg_id]["add_output"]):
            add_output(nbformat.v4.output_from_msg(rsp))

    def on_iopub_clear_output(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for an iopub clear output response."""
        # Clear cell output, either now or when we get the next output
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(clear_output := self.msg_id_callbacks[msg_id]["clear_output"]):
            clear_output(rsp.get("content", {}).get("wait", False))

    '''
    def on_iopub_comm_info_reply(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for an comm open response."""
        self.kernel_tab.comm_open(
            content=rsp.get("content", {}), buffers=rsp.get("buffers", [])
        )
    '''

    def on_iopub_comm_open(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for an comm open response."""
        # TODO
        # "If the target_name key is not found on the receiving side, then it should
        # immediately reply with a comm_close message to avoid an inconsistent state."
        #
        self.kernel_tab.comm_open(
            content=rsp.get("content", {}), buffers=rsp.get("buffers", [])
        )

    def on_iopub_comm_msg(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for an iopub comm message response."""
        self.kernel_tab.comm_msg(
            content=rsp.get("content", {}), buffers=rsp.get("buffers", [])
        )

    def on_iopub_comm_close(self, rsp: "dict[str, Any]") -> "None":
        """Call callbacks for an iopub comm close response."""
        self.kernel_tab.comm_close(
            content=rsp.get("content", {}), buffers=rsp.get("buffers", [])
        )

    def kc_comm(self, comm_id: "str", data: "dict[str, Any]") -> "str":
        """Send a comm message on the shell channel."""
        content = {
            "comm_id": comm_id,
            "data": data,
        }
        if self.kc is not None:
            msg = self.kc.session.msg("comm_msg", content)
            self.kc.shell_channel.send(msg)
            return msg["header"]["msg_id"]
        else:
            raise Exception("Cannot send message when kernel has not started")

    def run(
        self,
        source: "str",
        wait: "bool" = False,
        callback: "Optional[Callable[..., None]]" = None,
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
                callback=callback,
            )

    async def run_(
        self,
        source: "str",
        get_input: "Optional[Callable[[str, bool], None]]" = None,
        set_execution_count: "Optional[Callable[[int], None]]" = None,
        add_output: "Optional[Callable[[dict[str, Any]], None]]" = None,
        clear_output: "Optional[Callable[[bool], None]]" = None,
        done: "Optional[Callable[[dict[str, Any]], None]]" = None,
        set_metadata: "Optional[Callable[[tuple[str, ...], Any], None]]" = None,
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

        def wrapped_done(content: "dict[str, Any]") -> "None":
            """Sets the event after the ``done`` callback has completed."""
            # Run the original callback
            if callable(done):
                done(content)
            # Set the event
            event.set()

        callbacks = {
            "get_input": get_input,
            "set_execution_count": set_execution_count,
            "add_output": add_output,
            "clear_output": clear_output,
            "set_metadata": set_metadata,
            "set_status": set_status,
            "done": wrapped_done,
        }
        self.msg_id_callbacks[msg_id].update(
            MsgCallbacks(
                filter(lambda x: x[1] is not None, callbacks.items())
            )  # type: ignore # mypy #8890
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
        set_kernel_info: "Optional[Callable[[dict[str, Any]], None]]" = None,
        set_status: "Optional[Callable[[str], None]]" = None,
    ) -> "None":
        """Request information about the kernel."""
        if self.kc is not None:
            msg_id = self.kc.kernel_info()
            callbacks = {"set_kernel_info": set_kernel_info, "set_status": set_status}
            self.msg_id_callbacks[msg_id].update(
                MsgCallbacks(
                    filter(lambda x: x[1] is not None, callbacks.items())
                )  # type: ignore # mypy #8890
            )

    def comm_info(self, target_name: "Optional[str]" = None) -> "None":
        """Request information about the current comms."""
        if self.kc is not None:
            self.kc.comm_info(target_name=target_name)

    async def complete_(
        self, code: "str", cursor_pos: "int", timeout: "int" = 60
    ) -> "list[dict]":
        """Request code completions from the kernel, asynchronously."""
        results: "list[dict]" = []
        if not self.kc:
            return results

        event = asyncio.Event()

        def process_complete_reply(content: "dict[str, Any]") -> "None":
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
        self,
        pattern: "str" = "",
        n: "int" = 1,
        hist_access_type: "str" = "search",
        timeout: "int" = 1,
    ) -> "Optional[list[tuple[int, int, str]]]":
        """Retrieve history from the kernel asynchronously."""
        await asyncio.sleep(0.1)  # Add a tiny timeout so we don't spam the kernel

        results: "list[tuple[int, int, str]]" = []

        if not self.kc:
            return results

        event = asyncio.Event()

        def process_history_reply(content: "dict[str, Any]") -> "None":
            """Process responses on the shell channel."""
            status = content.get("status", "")
            if status == "ok":
                for item in content.get("history", []):
                    results.append(item)
                    event.set()

        msg_id = self.kc.history(
            pattern=pattern, n=n, hist_access_type=hist_access_type, unique=True
        )
        self.msg_id_callbacks[msg_id].update({"done": process_history_reply})

        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for kernel info response")

        return results

    def history(
        self, pattern: "str" = "", n: "int" = 1, hist_access_type: "str" = "search"
    ) -> "Optional[list[tuple[int, int, str]]]":
        """Retrieve history from the kernel.

        Args:
            pattern: The pattern to search for
            n: the number of history items to return
            hist_access_type: How to access the history ('range', 'tail' or 'search')

        Returns:
            A list of history items, consisting of tuples (session, line_number, input)

        """
        return self._aodo(
            self.history_(pattern, n, hist_access_type),
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

        def process_inspect_reply(content: "dict[str, Any]") -> "None":
            """Process responses on the shell channel."""
            status = content.get("status", "")
            if status == "ok":
                if content.get("found", False):
                    result.update(content)
                    event.set()

        log.debug("Requesting contextual help from the kernel")
        msg_id = self.kc.inspect(code, cursor_pos=cursor_pos, detail_level=detail_level)
        self.msg_id_callbacks[msg_id].update({"done": process_inspect_reply})

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

    async def is_complete_(
        self,
        code: "str",
        timeout: "Union[int, float]" = 0.1,
    ) -> "dict[str, Any]":
        """Ask the kernel to determine if code is complete asynchronously."""
        result: "dict[str, Any]" = {}

        if not self.kc:
            return result

        event = asyncio.Event()

        def process_is_complete_reply(content: "dict[str, Any]") -> "None":
            """Process responses on the shell channel."""
            result.update(content)
            event.set()

        msg_id = self.kc.is_complete(code)
        self.msg_id_callbacks[msg_id].update(
            {"completeness_status": process_is_complete_reply}
        )

        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for kernel info response")

        return result

    def is_complete(
        self,
        code: "str",
        timeout: "Union[int, float]" = 0.1,
        wait: "bool" = False,
        callback: "Optional[Callable[[dict[str, Any]], None]]" = None,
    ) -> "dict[str, Any]":
        """Request code completeness status from the kernel.

        Args:
            code: The code string to check the completeness status of
            timeout: How long to wait for a kernel response
            wait: Whether to wait for the response
            callback: A function to run when the inspection result arrives. The result
                is passed as an argument.

        Returns:
            A string describing the completeness status

        """
        return self._aodo(
            self.is_complete_(code, timeout),
            wait=wait,
            callback=callback,
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
        log.debug("Restarting kernel `%s`", self.id)
        await self.km.restart_kernel()
        log.debug("Kernel %s restarted", self.id)

    def restart(self, wait: "bool" = False, cb: "Optional[Callable]" = None) -> "None":
        """Restarts the current kernel."""
        self._aodo(
            self.restart_(),
            wait=wait,
            callback=cb,
        )

    def change(self, name: "str", cb: "Optional[Callable]" = None) -> "None":
        """Change the kernel.

        Args:
            name: The name of the kernel to change to
            cb: Callback to run once restarted

        """
        spec = self.specs.get(name, {}).get("spec", {})

        self.kernel_tab.metadata["kernelspec"] = {
            "name": name,
            "display_name": spec["display_name"],
            "language": spec["language"],
        }
        self.km.kernel_name = name
        if self.km.has_kernel:
            self.restart(cb=cb)
        else:
            self.start(cb=cb)

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
        :py:class:`~euporie.core.tabs.notebook.Kernel` cannot be restarted after this.

        Args:
            wait: Whether to block until shutdown completes

        """
        self._aodo(
            self.shutdown_(),
            wait=wait,
        )
        if self.threaded:
            self.thread.join(timeout=5)

    # ################################### Settings ####################################

    add_setting(
        name="kernel_connection_file",
        flags=["--kernel-connection-file"],
        type_=str,
        help_="Attempt to connect to an existing kernel using a JSON connection info file",
        default="",
        description="""
            Load connection info from JSON dict. This allows euporie to connect to
            existing kernels.
        """,
    )
