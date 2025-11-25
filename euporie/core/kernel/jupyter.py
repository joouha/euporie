"""Contain the main class for a notebook file."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from collections import defaultdict
from functools import partial
from subprocess import PIPE, STDOUT  # S404 - Security implications considered
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from upath import UPath

from euporie.core.kernel.base import BaseKernel, KernelInfo, MsgCallbacks
from euporie.core.nbformat import new_output, output_from_msg

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any, Unpack

    from jupyter_client import KernelClient
    from jupyter_client.kernelspec import KernelSpecManager

    from euporie.core.tabs.kernel import KernelTab


log = logging.getLogger(__name__)


class JupyterKernel(BaseKernel):
    """Run a notebook kernel and communicates with it asynchronously.

    Has the ability to run itself in it's own thread.
    """

    _client_id = f"euporie-{os.getpid()}"
    _spec_manager: KernelSpecManager

    @classmethod
    def variants(cls) -> list[KernelInfo]:
        """Return available kernel specifications."""
        from jupyter_core.paths import jupyter_runtime_dir

        try:
            manager = cls._spec_manager
        except AttributeError:
            from jupyter_client.kernelspec import KernelSpecManager
            from jupyter_core.paths import jupyter_path

            manager = cls._spec_manager = KernelSpecManager()
            # Set the kernel folder list to prevent the default method from running.
            # This prevents the kernel spec manager from loading IPython, just for the
            # purpose of adding the depreciated :file:`.ipython/kernels` folder to the list
            # of kernel search paths. Without this, having IPython installed causes a
            # import race condition error where IPython was imported in the main thread for
            # displaying LaTeX and in the kernel thread to discover kernel paths.
            # Also this speeds up launch since importing IPython is pretty slow.
            manager.kernel_dirs = jupyter_path("kernels")

        return [
            KernelInfo(
                name=name,
                display_name=info.get("spec", {}).get("display_name", name),
                factory=partial(cls, kernel_name=name),
                kind="new",
                type=cls,
            )
            for name, info in manager.get_all_specs().items()
        ] + [
            KernelInfo(
                name=path.name,
                display_name=path.name,
                factory=partial(cls, connection_file=path),
                kind="existing",
                type=cls,
            )
            for path in UPath(jupyter_runtime_dir()).glob("kernel-*.json")
        ]

    def __init__(
        self,
        kernel_tab: KernelTab,
        default_callbacks: MsgCallbacks | None = None,
        allow_stdin: bool = False,
        *,
        kernel_name: str | None = None,
        connection_file: Path | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the JupyterKernel.

        Args:
            kernel_tab: The notebook this kernel belongs to
            allow_stdin: Whether the kernel is allowed to request input
            default_callbacks: The default callbacks to use on receipt of a message
            kernel_name: Name of the Jupyter kernel to launch
            connection_file: Path to a file from which to load or to which to save
                kernel connection information
            kwargs: Additional key-word arguments
        """
        super().__init__(
            kernel_tab=kernel_tab,
            allow_stdin=allow_stdin,
            default_callbacks=default_callbacks,
        )

        from euporie.core.kernel.jupyter_manager import (
            EuporieKernelManager,
            set_default_provisioner,
        )

        set_default_provisioner()

        if kernel_name is None and connection_file is not None:
            import json

            try:
                connection_info = json.loads(connection_file.read_text())
            except json.decoder.JSONDecodeError:
                connection_info = {}
            kernel_name = connection_info.get("kernel_name", "python3")

        if kernel_name is None and connection_file is None:
            raise ValueError("Must provide `kernel_name` or `connection_file`")

        self.connection_file = connection_file
        self.km = EuporieKernelManager(kernel_name=kernel_name)
        self.kc: KernelClient | None = None
        self.monitor_task: asyncio.Task | None = None
        self.poll_tasks: list[asyncio.Task] = []
        self.msg_id_callbacks: dict[str, MsgCallbacks] = defaultdict(
            # Return a copy of the default callbacks
            lambda: MsgCallbacks(dict(self.default_callbacks))  # type: ignore # mypy #8890
        )
        self.client_lock = threading.Lock()

        # Accessing the kernel spec causes `readline` to be imported, which causes the
        # terminal to be set to cooked mode on MacOS when run not on the main thread.
        # The import  process leading to this is:
        #   jupyter_client -> ipykernel -> ipython.core.debugger -> pdb -> readline
        # We deliberately access the kernelspec here in cooked mode, causing ptk to
        # return the terminal to raw mode when done
        if threading.current_thread() != threading.main_thread():
            with self.kernel_tab.app.input.cooked_mode():
                _ = self.km.kernel_spec

    def _set_living_status(self, alive: bool) -> None:
        """Set the life status of the kernel."""
        if not alive:
            self.status = "error"
            if (
                callable(dead_cb := self.default_callbacks.get("dead"))
                and not self.dead
            ):
                log.debug("Kernel %s appears to have died", self.id)
                self.dead = True
                dead_cb()

    async def monitor_status(self) -> None:
        """Regularly monitor the kernel status."""
        while True:
            await asyncio.sleep(1)
            # Check kernel is alive - use client rather than manager if we have one
            # as we could be connected to a kernel not started by the manager
            if self.kc and self.status != "starting":
                alive = await self.kc._async_is_alive()
                self._set_living_status(alive)
                # Stop the timer if the kernel is dead
                if not alive:
                    break
            else:
                break

    @property
    def missing(self) -> bool:
        """Return True if the requested kernel is not found."""
        from jupyter_client.kernelspec import NoSuchKernel

        try:
            self.km.kernel_spec  # noqa B018
        except NoSuchKernel:
            return True
        else:
            return self.km.kernel_spec is None

    @property
    def id(self) -> str | None:
        """Get the ID of the current kernel."""
        if self.km.has_kernel:
            return self.km.kernel_id
        else:
            return None

    async def stop_async(self, cb: Callable[[], Any] | None = None) -> None:
        """Stop the kernel asynchronously."""
        for task in self.poll_tasks:
            task.cancel()
        if self.kc is not None:
            self.kc.stop_channels()
        if self.km.has_kernel:
            await self.km.shutdown_kernel()
        log.debug("Kernel %s shutdown", self.id)

    async def start_async(self) -> None:
        """Start the kernel asynchronously and set its status."""
        from jupyter_core.paths import jupyter_runtime_dir

        if self.km.kernel_name is None:
            self.status = "error"
        log.debug("Starting kernel")
        self.status = "starting"

        # If we are connecting to an existing kernel, create a kernel client using
        # the given connection file
        runtime_dir = UPath(jupyter_runtime_dir())
        if (connection_file := self.connection_file) is None:
            id_ = str(uuid4())[:8]
            connection_file = runtime_dir / f"kernel-euporie-{id_}.json"
        connection_file_str = str(connection_file)
        self.km.connection_file = connection_file_str

        if connection_file.exists():
            log.debug(
                "Connecting to existing kernel using connection file '%s'",
                connection_file,
            )
            self.km.load_connection_file(connection_file_str)
            kc = self.km.client_factory(connection_file=connection_file_str)
            kc.load_connection_file()
            kc.start_channels()
            self.kc = kc

        # Otherwise, start a new kernel using the kernel manager
        else:
            runtime_dir.mkdir(exist_ok=True, parents=True)
            for attempt in range(1, 4):
                try:
                    # TODO - send stdout to log
                    await self.km.start_kernel(stdout=PIPE, stderr=STDOUT, text=True)
                except Exception as e:
                    log.error(
                        "Kernel '%s' could not start on attempt %s",
                        self.km.kernel_name,
                        attempt,
                    )
                    if attempt > 2:
                        continue
                    self.status = "error"
                    self.error = e
                else:
                    log.info("Started kernel %s", self.km.kernel_name)
                    # Create a client for the newly started kernel
                    if self.km.has_kernel:
                        self.kc = self.km.client()
                    break

        await self.post_start()

    @property
    def spec(self) -> dict[str, str]:
        """The kernelspec metadata for the current kernel instance."""
        assert self.km.kernel_spec is not None
        return {
            "name": self.km.kernel_name,
            "display_name": self.km.kernel_spec.display_name,
            "language": self.km.kernel_spec.language,
        }

    async def post_start(self) -> None:
        """Wait for the kernel to become ready."""
        from jupyter_client.kernelspec import NoSuchKernel

        try:
            ks = self.km.kernel_spec
        except NoSuchKernel as e:
            self.error = e
            self.status = "error"
            log.error("Selected kernel '%s' not registered", self.km.kernel_name)
        else:
            if ks is not None and self.kc is not None:
                log.debug("Waiting for kernel to become ready")
                try:
                    await self.kc._async_wait_for_ready(timeout=30)
                except RuntimeError as e:
                    log.error("Error connecting to kernel")
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
                    self.dead = False

                # Set username so we can identify our own messages
                self.kc.session.username = self._client_id

                # Send empty execution request to get current execution count
                self.kc.execute("", store_history=False, silent=True, allow_stdin=False)

            # Start monitoring the kernel status
            if self.monitor_task is not None:
                self.monitor_task.cancel()
            # If kernel already stopped (or failed to start), don't start monitoring
            if self.status == "idle":
                self.monitor_task = asyncio.create_task(self.monitor_status())

    def start(
        self, cb: Callable | None = None, wait: bool = False, timeout: int = 10
    ) -> None:
        """Start the kernel.

        Args:
            cb: An optional callback to run after the kernel has started
            wait: If :py:const:`True`, block until the kernel has started
            timeout: How long to wait until failure is assumed

        """
        from jupyter_client.kernelspec import NATIVE_KERNEL_NAME

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
        super().start(cb, wait, timeout)

    async def poll(self, channel: str) -> None:
        """Poll for messages on a channel, and signal when they arrive.

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
            own = rsp.get("parent_header", {}).get("username") == self._client_id
            if callable(handler := getattr(self, f"on_{channel}_{msg_type}", None)):
                handler(rsp, own)
            else:
                self.on_unhandled(channel, rsp, own)

    def on_unhandled(self, channel: str, rsp: dict[str, Any], own: bool) -> None:
        """Report unhandled messages to the debug log."""
        log.debug(
            "Unhandled %s message:\nparent_id = '%s'\ntype = '%s'\ncontent='%s'\nown: %s",
            channel,
            rsp.get("parent_header", {}).get("msg_id"),
            rsp["header"]["msg_type"],
            rsp.get("content"),
            own,
        )

    def on_stdin_input_request(self, rsp: dict[str, Any], own: bool) -> None:
        """Call ``get_input`` callback for a stdin input request message."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        content = rsp.get("content", {})
        if callable(get_input := self.msg_id_callbacks[msg_id].get("get_input")):
            get_input(
                content.get("prompt", ""),
                content.get("password", False),
            )

    def on_shell_status(self, rsp: dict[str, Any], own: bool) -> None:
        """Call ``set_execution_count`` callback for a shell status response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        content = rsp.get("content", {})
        status = rsp.get("content", {}).get("status", "")
        if (
            status == "ok"
            and (execution_count := content.get("execution_count"))
            and callable(
                set_execution_count := self.msg_id_callbacks[msg_id].get(
                    "set_execution_count"
                )
            )
        ):
            set_execution_count(execution_count)

    def on_shell_execute_reply(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for a shell execute reply response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        content = rsp.get("content", {})

        if self.kernel_tab.app.config.record_cell_timing and callable(
            set_metadata := self.msg_id_callbacks[msg_id]["set_metadata"]
        ):
            set_metadata(
                ("execution", "shell.execute_reply"),
                rsp["header"]["date"].isoformat(),
            )

        if (
            (execution_count := content.get("execution_count")) is not None
        ) and callable(
            set_execution_count := self.msg_id_callbacks[msg_id]["set_execution_count"]
        ):
            set_execution_count(execution_count)

        if payloads := content.get("payload", []):
            for payload in payloads:
                source = payload.get("source")

                if source == "page":
                    # Show pager output as a cell execution output
                    if callable(
                        add_output := self.msg_id_callbacks[msg_id]["add_output"]
                    ) and (data := payload.get("data", {})):
                        add_output(
                            new_output("execute_result", data=data),
                            own,
                        )
                elif source == "set_next_input":
                    if callable(
                        set_next_input := self.msg_id_callbacks[msg_id][
                            "set_next_input"
                        ]
                    ):
                        set_next_input(
                            payload.get("text", ""),
                            payload.get("replace", False),
                        )

                elif source == "edit_magic" and callable(
                    edit_magic := self.msg_id_callbacks[msg_id]["edit_magic"]
                ):
                    edit_magic(
                        payload.get("filename"),
                        int(payload.get("line_number") or 0),
                    )

        if content.get("status") == "ok" and callable(
            done := self.msg_id_callbacks[msg_id].get("done")
        ):
            done(content)

    def on_shell_kernel_info_reply(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for a shell kernel info response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(
            set_kernel_info := self.msg_id_callbacks[msg_id].get("set_kernel_info")
        ):
            set_kernel_info(rsp.get("content", {}))

    def on_shell_complete_reply(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for a shell completion reply response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(done := self.msg_id_callbacks[msg_id].get("done")):
            done(rsp.get("content", {}))

    def on_shell_history_reply(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for a shell history reply response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(done := self.msg_id_callbacks[msg_id].get("done")):
            done(rsp.get("content", {}))

    def on_shell_inspect_reply(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for a shell inspection reply response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(done := self.msg_id_callbacks[msg_id].get("done")):
            done(rsp.get("content", {}))

    def on_shell_is_complete_reply(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for a shell completeness reply response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(
            completeness_status := self.msg_id_callbacks[msg_id].get(
                "completeness_status"
            )
        ):
            completeness_status(rsp.get("content", {}))

    def on_iopub_shutdown_reply(self, rsp: dict[str, Any], own: bool) -> None:
        """Handle iopub shutdown reply messages."""
        if not rsp.get("content", {}).get("restart"):
            # Stop monitoring the kernel
            if self.monitor_task is not None:
                self.monitor_task.cancel()
            self._set_living_status(False)

    def on_iopub_status(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for an iopub status response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        status = rsp.get("content", {}).get("execution_state")

        self.status = status
        if callable(set_status := self.msg_id_callbacks[msg_id].get("set_status")):
            set_status(status)

        if status == "idle":
            if self.kernel_tab.app.config.record_cell_timing and callable(
                set_metadata := self.msg_id_callbacks[msg_id].get("set_metadata")
            ):
                set_metadata(
                    ("execution", "iopub.status.idle"),
                    rsp["header"]["date"].isoformat(),
                )

        elif status == "busy" and (
            self.kernel_tab.app.config.record_cell_timing
            and callable(
                set_metadata := self.msg_id_callbacks[msg_id].get("set_metadata")
            )
        ):
            set_metadata(
                ("execution", "iopub.status.busy"),
                rsp["header"]["date"].isoformat(),
            )

    def on_iopub_execute_input(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for an iopub execute input response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        content = rsp.get("content", {})

        if self.kernel_tab.app.config.record_cell_timing and callable(
            set_metadata := self.msg_id_callbacks[msg_id]["set_metadata"]
        ):
            set_metadata(
                ("execution", "iopub", "execute_input"),
                rsp["header"]["date"].isoformat(),
            )

        execution_count: int | None = None
        if (execution_count := content.get("execution_count")) and (
            callable(
                set_execution_count := self.msg_id_callbacks[msg_id][
                    "set_execution_count"
                ]
            )
        ):
            set_execution_count(execution_count)

        if callable(add_input := self.msg_id_callbacks[msg_id].get("add_input")):
            add_input(content, own)

    def on_iopub_display_data(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for an iopub display data response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(add_output := self.msg_id_callbacks[msg_id]["add_output"]):
            add_output(output_from_msg(rsp), own)

    def on_iopub_update_display_data(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for an iopub update display data response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(add_output := self.msg_id_callbacks[msg_id]["add_output"]):
            add_output(output_from_msg(rsp), own)

    def on_iopub_execute_result(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for an iopub execute result response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(add_output := self.msg_id_callbacks[msg_id]["add_output"]):
            add_output(output_from_msg(rsp), own)

        if (execution_count := rsp.get("content", {}).get("execution_count")) and (
            callable(
                set_execution_count := self.msg_id_callbacks[msg_id][
                    "set_execution_count"
                ]
            )
        ):
            set_execution_count(execution_count)

    def on_iopub_error(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for an iopub error response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id", "")
        if callable(add_output := self.msg_id_callbacks[msg_id].get("add_output")):
            add_output(output_from_msg(rsp), own)
        if callable(done := self.msg_id_callbacks[msg_id].get("done")):
            done(rsp.get("content", {}))

    def on_iopub_stream(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for an iopub stream response."""
        msg_id = rsp.get("parent_header", {}).get("msg_id")
        if callable(add_output := self.msg_id_callbacks[msg_id]["add_output"]):
            add_output(output_from_msg(rsp), own)

    def on_iopub_clear_output(self, rsp: dict[str, Any], own: bool) -> None:
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

    def on_iopub_comm_open(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for an comm open response."""
        # TODO
        # "If the target_name key is not found on the receiving side, then it should
        # immediately reply with a comm_close message to avoid an inconsistent state."
        #
        self.kernel_tab.comm_open(
            content=rsp.get("content", {}), buffers=rsp.get("buffers", [])
        )

    def on_iopub_comm_msg(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for an iopub comm message response."""
        self.kernel_tab.comm_msg(
            content=rsp.get("content", {}), buffers=rsp.get("buffers", [])
        )

    def on_iopub_comm_close(self, rsp: dict[str, Any], own: bool) -> None:
        """Call callbacks for an iopub comm close response."""
        self.kernel_tab.comm_close(
            content=rsp.get("content", {}), buffers=rsp.get("buffers", [])
        )

    def kc_comm(self, comm_id: str, data: dict[str, Any]) -> str | None:
        """Send a comm message on the shell channel."""
        content = {
            "comm_id": comm_id,
            "data": data,
        }
        if self.kc is not None:
            msg = self.kc.session.msg("comm_msg", content)
            with self.client_lock:
                self.kc.shell_channel.send(msg)
            return msg["header"]["msg_id"]
        else:
            log.info("Cannot send message when kernel has not started")
            return None

    def run(
        self,
        source: str,
        wait: bool = False,
        callback: Callable[..., None] | None = None,
        **callbacks: Callable[..., Any],
    ) -> None:
        """Run a cell using the notebook kernel and process the responses."""
        if self.kc is None:
            log.debug("Cannot run cell because kernel has not started")
            # TODO - queue cells for execution
        else:
            super().run(source, wait, callback, **callbacks)

    async def run_async(
        self, source: str, **local_callbacks: Unpack[MsgCallbacks]
    ) -> None:
        """Run the code cell and and set the response callbacks, optionally waiting."""
        if self.kc is None:
            return
        event = asyncio.Event()
        msg_id = self.kc.execute(
            source,
            store_history=True,
            allow_stdin=self.allow_stdin,
        )

        if done := local_callbacks.get("done"):

            def wrapped_done(content: dict[str, Any]) -> None:
                """Set the event after the ``done`` callback has completed."""
                # Run the original callback
                if callable(done):
                    done(content)
                # Set the event
                event.set()

            local_callbacks["done"] = wrapped_done

        self.msg_id_callbacks[msg_id].update(
            cast(
                "MsgCallbacks",
                {k: v for k, v in local_callbacks.items() if v is not None},
            )
        )
        # Wait for "done" callback to be called
        try:
            await asyncio.wait_for(event.wait(), timeout=None)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for kernel run response")

        # Clean up callbacks
        # await asyncio.sleep(0.1)
        # if msg_id in self.msg_id_callbacks:
        # del self.msg_id_callbacks[msg_id]

    def info(
        self,
        set_kernel_info: Callable[[dict[str, Any]], None] | None = None,
        set_status: Callable[[str], None] | None = None,
    ) -> None:
        """Request information about the kernel."""
        if self.kc is not None:

            def _set_status(status: str) -> None:
                """Set the kernel status based on the response of a kerne_info request."""
                self.status = status
                if callable(set_status):
                    set_status(status)

            msg_id = self.kc.kernel_info()
            callbacks = {
                "set_kernel_info": set_kernel_info,
                "set_status": _set_status,
            }
            self.msg_id_callbacks[msg_id].update(
                MsgCallbacks(filter(lambda x: x[1] is not None, callbacks.items()))  # type: ignore # mypy #8890
            )

    def comm_info(self, target_name: str | None = None) -> None:
        """Request information about the current comms."""
        if self.kc is not None:
            self.kc.comm_info(target_name=target_name)

    async def complete_async(
        self, source: str, cursor_pos: int, timeout: int = 60
    ) -> list[dict]:
        """Request code completions from the kernel, asynchronously."""
        results: list[dict] = []
        if not self.kc:
            return results

        event = asyncio.Event()

        def process_complete_reply(content: dict[str, Any]) -> None:
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

        msg_id = self.kc.complete(source, cursor_pos)
        self.msg_id_callbacks[msg_id].update({"done": process_complete_reply})

        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for kernel completion response")

        return results

    async def history_async(
        self,
        pattern: str = "",
        n: int = 1,
        hist_access_type: str = "search",
        timeout: int = 60,
    ) -> list[tuple[int, int, str]] | None:
        """Retrieve history from the kernel asynchronously."""
        await asyncio.sleep(0.1)  # Add a tiny timeout so we don't spam the kernel

        results: list[tuple[int, int, str]] = []

        if not self.kc:
            return results

        event = asyncio.Event()

        def process_history_reply(content: dict[str, Any]) -> None:
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
            log.debug("Timed out waiting for kernel history response")

        return results

    async def inspect_async(
        self,
        source: str,
        cursor_pos: int,
        detail_level: int = 0,
        timeout: int = 2,
    ) -> dict[str, Any]:
        """Retrieve introspection string from the kernel asynchronously."""
        await asyncio.sleep(0.1)  # Add a tiny timeout so we don't spam the kernel

        result: dict[str, Any] = {}

        if not self.kc:
            return result

        event = asyncio.Event()

        def process_inspect_reply(content: dict[str, Any]) -> None:
            """Process responses on the shell channel."""
            status = content.get("status", "")
            if status == "ok" and content.get("found", False):
                result.update(content.get("data", {}))
                event.set()

        log.debug("Requesting contextual help from the kernel")
        msg_id = self.kc.inspect(
            source, cursor_pos=cursor_pos, detail_level=detail_level
        )
        self.msg_id_callbacks[msg_id].update({"done": process_inspect_reply})

        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for kernel inspection response")

        return result

    async def is_complete_async(
        self,
        source: str,
        timeout: int | float = 0.1,
    ) -> dict[str, Any]:
        """Ask the kernel to determine if code is complete asynchronously."""
        result: dict[str, Any] = {}

        if not self.kc:
            return result

        event = asyncio.Event()

        def process_is_complete_reply(content: dict[str, Any]) -> None:
            """Process responses on the shell channel."""
            result.update(content)
            event.set()

        msg_id = self.kc.is_complete(source)
        self.msg_id_callbacks[msg_id].update(
            {"completeness_status": process_is_complete_reply}
        )

        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.TimeoutError:
            log.debug("Timed out waiting for kernel completion response")

        return result

    def input(self, text: str) -> None:
        """Send input to the kernel."""
        if self.kc:
            self.kc.input(text)

    def interrupt(self) -> None:
        """Interrupt the kernel.

        This is run in the main thread rather than on the event loop in the kernel's thread,
        because otherwise we would have to wait for currently running tasks on the
        kernel's event loop to finish.
        """
        if self.km.has_kernel:
            from jupyter_client import KernelManager

            log.debug("Interrupting kernel %s", self.id)
            KernelManager.interrupt_kernel(self.km)

    async def restart_async(self) -> None:
        """Restart the kernel asyncchronously."""
        log.debug("Restarting kernel `%s`", self.id)
        # Cancel polling tasks
        for task in self.poll_tasks:
            task.cancel()
        self.error = None
        self.status = "starting"
        try:
            await self.km.restart_kernel(now=True)
            await self.post_start()
        except asyncio.exceptions.InvalidStateError:
            await self.start_async()
        log.debug("Kernel %s restarted", self.id)

    def stop(self, cb: Callable | None = None, wait: bool = False) -> None:
        """Stop the current kernel.

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
            super().stop(cb, wait)

    async def shutdown_async(self) -> None:
        """Shut down the kernel and close the event loop if running in a thread."""
        # Stop monitoring the kernel
        if self.monitor_task is not None:
            self.monitor_task.cancel()
        # Clean up connection file
        self.km.cleanup_connection_file()
        # Stop kernel
        if self.km.has_kernel:
            await self.km.shutdown_kernel(now=True)
