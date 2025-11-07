"""Base class for euporie kernels."""

from __future__ import annotations

import asyncio
import concurrent
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, NamedTuple, TypedDict, overload

from euporie.core.async_utils import get_or_create_loop, run_coro_async, run_coro_sync

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, Literal, Protocol, TypeVar, Unpack

    from euporie.core.tabs.kernel import KernelTab

    class KernelFactory(Protocol):
        """Type for kernel factory functions."""

        def __call__(
            self,
            kernel_tab: KernelTab,
            default_callbacks: MsgCallbacks | None = None,
            allow_stdin: bool = False,
            **kwargs: Any,
        ) -> BaseKernel:
            """Signature for creating a new Kernel instance."""

    T = TypeVar("T")

log = logging.getLogger(__name__)


class KernelInfo(NamedTuple):
    """Named tuple representing a launchable kernel."""

    name: str
    display_name: str
    type: type[BaseKernel]
    kind: Literal["new", "existing"]
    factory: KernelFactory


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


class BaseKernel(ABC):
    """Abstract base class for euporie kernels."""

    @classmethod
    def variants(cls) -> list[KernelInfo]:
        """Return a list of parameterized variants of this kernel."""
        return []

    def __init__(
        self,
        kernel_tab: KernelTab,
        default_callbacks: MsgCallbacks | None = None,
        allow_stdin: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the kernel.

        Args:
            kernel_tab: The notebook this kernel belongs to
            allow_stdin: Whether the kernel is allowed to request input
            default_callbacks: The default callbacks to use on receipt of a message
            **kwargs: Additional keyword arguments passed to parent classes
        """
        self.loop = get_or_create_loop("kernel")

        self.kernel_tab = kernel_tab
        self.allow_stdin = allow_stdin
        self._status = "stopped"
        self.error: Exception | None = None
        self.dead = False
        self.status_change_event = asyncio.Event()
        self.coros: dict[str, concurrent.futures.Future] = {}
        self.msg_id_callbacks: dict[str, MsgCallbacks] = {}

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

    @property
    @abstractmethod
    def spec(self) -> dict[str, str]:
        """The kernelspec metadata for the current kernel instance."""

    @overload
    def _aodo(
        self,
        coro: Coroutine[Any, Any, T],
        wait: Literal[True] = True,
        callback: Callable | None = None,
        timeout: int | float | None = None,
        single: bool = False,
    ) -> T | None: ...
    @overload
    def _aodo(
        self,
        coro: Coroutine[Any, Any, T],
        wait: Literal[False] = False,
        callback: Callable | None = None,
        timeout: int | float | None = None,
        single: bool = False,
    ) -> concurrent.futures.Future: ...
    @overload
    def _aodo(
        self,
        coro: Coroutine[Any, Any, T],
        wait: bool = False,
        callback: Callable | None = None,
        timeout: int | float | None = None,
        single: bool = False,
    ) -> T | None | concurrent.futures.Future: ...
    def _aodo(self, coro, wait=False, callback=None, timeout=None, single=False):
        """Schedule a coroutine in the kernel's event loop.

        Optionally waits for the results (blocking the main thread). Optionally
        schedules a callback to run when the coroutine has completed or timed out.

        Args:
            coro: The coroutine to run
            wait: If :py:const:`True`, block until the coroutine completes
            callback: A function to run when the coroutine completes. The result from
                the coroutine will be passed as an argument
            timeout: The number of seconds to allow the coroutine to run if waiting
            single: If :py:const:`True`, any futures for previous instances of the
                coroutine will be cancelled

        Returns:
            The result of the coroutine if wait=True, otherwise a Future

        """
        if wait:
            # Synchronous/blocking execution
            result = None
            try:
                result = run_coro_sync(coro, loop=self.loop)
            except concurrent.futures.TimeoutError:
                log.error("Operation '%s' timed out", coro)
                return result
            finally:
                if callable(callback):
                    callback(result)
            return result
        else:
            # Asynchronous execution with optional callback
            return run_coro_async(
                coro,
                loop=self.loop,
                cancel_previous=single,
                previous_tasks=self.coros,
                callback=callback,
            )

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

    def start(
        self, cb: Callable | None = None, wait: bool = False, timeout: int = 10
    ) -> None:
        """Start the kernel.

        Args:
            cb: An optional callback to run after the kernel has started
            wait: If :py:const:`True`, block until the kernel has started
            timeout: How long to wait until failure is assumed

        """
        self._aodo(
            self.start_async(),
            timeout=timeout,
            wait=wait,
            callback=cb,
        )

    @abstractmethod
    async def start_async(self) -> None:
        """Start the kernel."""

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

    @abstractmethod
    async def run_async(
        self, source: str, **local_callbacks: Unpack[MsgCallbacks]
    ) -> None:
        """Execute code in the kernel asynchronously."""

    def complete(self, source: str, cursor_pos: int) -> list[dict]:
        """Request code completions from the kernel.

        Args:
            source: The code string to retrieve completions for
            cursor_pos: The position of the cursor in the code string

        Returns:
            A list of dictionaries defining completion entries. The dictionaries
            contain ``text`` (the completion text), ``start_position`` (the stating
            position of the completion text), and optionally ``display_meta``
            (a string containing additional data about the completion type)

        """
        return (
            self._aodo(
                self.complete_async(source, cursor_pos),
                wait=True,
                single=True,
            )
            or []
        )

    @abstractmethod
    async def complete_async(self, source: str, cursor_pos: int) -> list[dict]:
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
        source: str,
        cursor_pos: int,
        detail_level: int = 0,
        timeout: int = 2,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Request code inspection from the kernel.

        Args:
            source: The code string to retrieve completions for
            cursor_pos: The position of the cursor in the code string
            detail_level: Level of detail for the inspection (0-2)
            timeout: Number of seconds to wait for inspection results
            callback: A function to run when the inspection result arrives. The result
                is passed as an argument.

        Returns:
            A string containing useful information about the code at the current cursor
            position

        """
        return (
            self._aodo(
                self.inspect_async(source, cursor_pos, detail_level),
                wait=True,
                callback=callback,
                single=True,
            )
            or {}
        )

    @abstractmethod
    async def inspect_async(
        self,
        source: str,
        cursor_pos: int,
        detail_level: int = 0,
        timeout: int = 2,
    ) -> dict[str, Any]:
        """Get code inspection/documentation asynchronously."""

    def is_complete(
        self,
        source: str,
        timeout: int | float = 0.1,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Request code completeness status from the kernel.

        Args:
            source: The code string to check the completeness status of
            timeout: How long to wait for a kernel response
            wait: Whether to wait for the response
            callback: A function to run when the inspection result arrives. The result
                is passed as an argument.

        Returns:
            A string describing the completeness status

        """
        return (
            self._aodo(
                self.is_complete_async(source, timeout), wait=True, callback=callback
            )
            or {}
        )

    @abstractmethod
    async def is_complete_async(
        self,
        source: str,
        timeout: int | float = 0.1,
    ) -> dict[str, Any]:
        """Check if code is complete asynchronously."""

    @abstractmethod
    def input(self, text: str) -> None:
        """Send input to the kernel."""

    @abstractmethod
    def interrupt(self) -> None:
        """Interrupt the kernel."""

    def restart(self, wait: bool = False, cb: Callable | None = None) -> None:
        """Restart the current kernel."""
        self._aodo(
            self.restart_async(),
            wait=wait,
            callback=cb,
        )

    @abstractmethod
    async def restart_async(self) -> None:
        """Restart the kernel asynchronously."""

    def shutdown(self, wait: bool = False, cb: Callable | None = None) -> None:
        """Shutdown the kernel.

        This is intended to be run when the notebook is closed: the
        :py:class:`~euporie.core.kernel.base.BaseKernel` cannot be restarted after this.

        Args:
            wait: Whether to block until shutdown completes
            cb: Callback run after shutdown completes

        """
        self._aodo(self.shutdown_async(), wait=wait, callback=cb)

    @abstractmethod
    async def shutdown_async(self) -> None:
        """Shutdown the kernel asynchronously."""

    @property
    @abstractmethod
    def missing(self) -> bool:
        """Return whether the kernel is missing."""

    @property
    @abstractmethod
    def id(self) -> str | None:
        """Return the kernel ID."""

    @abstractmethod
    def info(
        self,
        set_kernel_info: Callable[[dict[str, Any]], None] | None = None,
        set_status: Callable[[str], None] | None = None,
    ) -> None:
        """Request information about the kernel."""

    def kc_comm(self, comm_id: str, data: dict[str, Any]) -> str | None:
        """By default kernels do not implement COMM communication."""
        log.warning("The %s kernel does not implement COMMs", self.__class__.__name__)
        return None

    def comm_info(self, target_name: str | None = None) -> None:
        """Request information about the current comms.

        Does nothing by default.
        """


class NoKernel(BaseKernel):
    """A `None` kernel."""

    @classmethod
    def variants(cls) -> list[KernelInfo]:
        """Return available kernel specifications."""
        return [
            KernelInfo(
                name="none",
                display_name="No Kernel",
                factory=cls,
                kind="new",
                type=cls,
            )
        ]

    @property
    def spec(self) -> dict[str, str]:
        """The kernelspec metadata for the current kernel instance."""
        raise NotImplementedError()

    async def start_async(self) -> None:
        """Start the kernel."""
        self.status = "idle"
        return

    async def run_async(
        self, source: str, **local_callbacks: Unpack[MsgCallbacks]
    ) -> None:
        """Execute code in the kernel asynchronously."""
        return None

    async def is_complete_async(
        self,
        source: str,
        timeout: int | float = 0.1,
    ) -> dict[str, Any]:
        """Check if code is complete asynchronously."""
        raise NotImplementedError()

    async def complete_async(self, source: str, cursor_pos: int) -> list[dict]:
        """Get code completions asynchronously."""
        raise NotImplementedError()

    async def inspect_async(
        self,
        source: str,
        cursor_pos: int,
        detail_level: int = 0,
        timeout: int = 2,
    ) -> dict[str, Any]:
        """Get code inspection/documentation asynchronously."""
        raise NotImplementedError()

    def input(self, text: str) -> None:
        """Send input to the kernel."""
        # Do nothing

    def interrupt(self) -> None:
        """Interrupt the kernel."""
        # Do nothing

    async def restart_async(self) -> None:
        """Restart the kernel asynchronously."""
        # Do nothing

    async def shutdown_async(self) -> None:
        """Shutdown the kernel asynchronously."""
        # Do nothing

    @property
    def missing(self) -> bool:
        """Return whether the kernel is missing."""
        raise NotImplementedError()

    @property
    def id(self) -> str | None:
        """Return the kernel ID."""
        raise NotImplementedError()

    def info(
        self,
        set_kernel_info: Callable[[dict[str, Any]], None] | None = None,
        set_status: Callable[[str], None] | None = None,
    ) -> None:
        """Request information about the kernel."""
        raise NotImplementedError()
