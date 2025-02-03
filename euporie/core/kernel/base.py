"""Base class for euporie kernels."""

from __future__ import annotations

import abc
import asyncio
import concurrent
import logging
import threading
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any

    from euporie.core.tabs.kernel import KernelTab

log = logging.getLogger(__name__)

_THREAD: list[threading.Thread | None] = [None]
_LOOP: list[asyncio.AbstractEventLoop | None] = [None]


class MsgCallbacks(TypedDict, total=False):
    """Typed dictionary for named message callbacks."""

    get_input: Callable[[str, bool], None] | None
    set_execution_count: Callable[[int], None] | None
    add_output: Callable[[dict[str, Any], bool], None] | None
    add_input: Callable[[dict[str, Any], bool], None] | None
    clear_output: Callable[[bool], None] | None
    done: Callable[[dict[str, Any]], None] | None
    set_metadata: Callable[[tuple[str, ...], Any], None] | None
    set_status: Callable[[str], None] | None
    set_kernel_info: Callable[[dict[str, Any]], None] | None
    completeness_status: Callable[[dict[str, Any]], None] | None
    dead: Callable[[], None] | None
    # Payloads
    page: Callable[[list[dict], int], None] | None
    set_next_input: Callable[[str, bool], None] | None
    edit_magic: Callable[[str, int], None] | None
    ask_exit: Callable[[bool], None] | None


def get_loop() -> asyncio.AbstractEventLoop:
    """Create or return the conversion IO loop.

    The loop will be running on a separate thread.
    """
    if _LOOP[0] is None:
        loop = asyncio.new_event_loop()
        _LOOP[0] = loop
        thread = threading.Thread(
            target=loop.run_forever, name="EuporieKernelLoop", daemon=True
        )
        thread.start()
        _THREAD[0] = thread
    assert _LOOP[0] is not None
    # Check we are not already in the conversion event loop
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None
    if _LOOP[0] is running_loop:
        raise NotImplementedError("Cannot nest event loop access")
    return _LOOP[0]


class BaseKernel(abc.ABC):
    """Abstract base class for euporie kernels."""

    def __init__(
        self,
        kernel_tab: KernelTab,
        allow_stdin: bool = False,
        default_callbacks: MsgCallbacks | None = None,
    ) -> None:
        """Initialize the kernel.

        Args:
            kernel_tab: The notebook this kernel belongs to
            allow_stdin: Whether the kernel is allowed to request input
            default_callbacks: The default callbacks to use on receipt of a message
        """
        self.loop = get_loop()
        self.kernel_tab = kernel_tab
        self.allow_stdin = allow_stdin
        self._status = "stopped"
        self.error: Exception | None = None
        self.dead = False
        self.coros: dict[str, concurrent.futures.Future] = {}
        self.status_change_event = asyncio.Event()

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

    def _aodo(
        self,
        coro: Coroutine,
        wait: bool = False,
        callback: Callable | None = None,
        timeout: int | float | None = None,
        single: bool = False,
    ) -> Any:
        """Schedule a coroutine in the kernel's event loop.

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
                future.add_done_callback(lambda f: callback(f.result()))
                return None
            return None

    @property
    def status(self) -> str:
        """Retrieve the current kernel status.

        Returns:
            The kernel status

        """
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        """Set the kernel status."""
        self.status_change_event.set()
        self._status = value
        self.status_change_event.clear()

    def wait_for_status(self, status: str = "idle") -> None:
        """Block until the kernel reaches a given status value."""
        if self.status != status:

            async def _wait() -> None:
                while self.status != status:
                    await asyncio.wait_for(
                        self.status_change_event.wait(), timeout=None
                    )

            self._aodo(_wait(), wait=True)

    @status.setter
    def status(self, value: str) -> None:
        """Set the kernel status."""
        self._status = value

    @abc.abstractmethod
    def start(
        self, cb: Callable | None = None, wait: bool = False, timeout: int = 10
    ) -> None:
        """Start the kernel."""

    @abc.abstractmethod
    def stop(self, cb: Callable | None = None, wait: bool = False) -> None:
        """Stop the kernel."""
        log.debug("Stopping kernel %s (wait=%s)", self.id, wait)
        if not wait:
            self.interrupt()
        self._aodo(self.stop_async(), callback=cb, wait=wait)

    async def stop_async(self, cb: Callable | None = None) -> None:
        """Stop the kernel asynchronously."""
        self.stop(cb)

    def run(
        self,
        source: str,
        wait: bool = False,
        callback: Callable[..., None] | None = None,
        **callbacks: Callable[..., Any],
    ) -> None:
        """Execute code in the kernel."""
        self._aodo(
            self.run_async(source, **callbacks),
            wait=wait,
            callback=callback,
        )

    @abc.abstractmethod
    async def run_async(
        self,
        source: str,
        wait: bool = False,
        **callbacks: Callable[..., Any],
    ) -> None:
        """Execute code in the kernel asynchronously."""

    def complete(self, code: str, cursor_pos: int) -> list[dict]:
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
            self.complete_async(code, cursor_pos),
            wait=True,
            single=True,
        )

    @abc.abstractmethod
    async def complete_async(self, code: str, cursor_pos: int) -> list[dict]:
        """Get code completions asynchronously."""

    def history(
        self, pattern: str = "", n: int = 1, hist_access_type: str = "search"
    ) -> list[tuple[int, int, str]] | None:
        """Retrieve history from the kernel.

        Args:
            pattern: The pattern to search for
            n: the number of history items to return
            hist_access_type: How to access the history ('range', 'tail' or 'search')

        Returns:
            A list of history items, consisting of tuples (session, line_number, input)

        """
        return self._aodo(
            self.history_async(pattern, n, hist_access_type),
            wait=True,
            single=True,
        )

    async def history_async(
        self,
        pattern: str = "",
        n: int = 1,
        hist_access_type: str = "search",
        timeout: int = 1,
    ) -> list[tuple[int, int, str]] | None:
        """Retrieve history from the kernel asynchronously."""
        return []

    def inspect(
        self,
        code: str,
        cursor_pos: int,
        detail_level: int = 0,
        timeout: int = 2,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> str:
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
            self.inspect_async(code, cursor_pos, detail_level),
            wait=False,
            callback=callback,
            single=True,
        )

    @abc.abstractmethod
    async def inspect_async(
        self,
        code: str,
        cursor_pos: int,
        detail_level: int = 0,
        timeout: int = 2,
    ) -> None:
        """Get code inspection/documentation asynchronously."""

    def is_complete(
        self,
        code: str,
        timeout: int | float = 0.1,
        wait: bool = False,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
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
            self.is_complete_async(code, timeout),
            wait=wait,
            callback=callback,
        )

    @abc.abstractmethod
    async def is_complete_async(
        self,
        code: str,
        timeout: int | float = 0.1,
    ) -> dict[str, Any]:
        """Check if code is complete asynchronously."""

    @abc.abstractmethod
    def interrupt(self) -> None:
        """Interrupt the kernel."""

    def restart(self, wait: bool = False, cb: Callable | None = None) -> None:
        """Restart the current kernel."""
        self._aodo(
            self.restart_async(),
            wait=wait,
            callback=cb,
        )

    @abc.abstractmethod
    async def restart_async(self) -> None:
        """Restart the kernel asynchronously."""

    def shutdown(self, wait: bool = False) -> None:
        """Shutdown the kernel.

        This is intended to be run when the notebook is closed: the
        :py:class:`~euporie.core.kernel.base.BaseKernel` cannot be restarted after this.

        Args:
            wait: Whether to block until shutdown completes

        """
        self._aodo(self.shutdown_async(), wait=wait)

    @abc.abstractmethod
    async def shutdown_async(self) -> None:
        """Shutdown the kernel asynchronously."""

    @property
    @abc.abstractmethod
    def specs(self) -> dict[str, dict]:
        """Return available kernel specifications."""

    @property
    @abc.abstractmethod
    def missing(self) -> bool:
        """Return whether the kernel is missing."""

    @property
    @abc.abstractmethod
    def id(self) -> str | None:
        """Return the kernel ID."""

    @property
    def kc(self) -> None:
        """Return None as local kernels don't have a kernel client."""
        return None
