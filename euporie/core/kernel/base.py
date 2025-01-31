"""Base class for euporie kernels."""

from __future__ import annotations

import abc
import logging
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any

    from euporie.core.tabs.kernel import KernelTab

log = logging.getLogger(__name__)


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


class BaseKernel(abc.ABC):
    """Abstract base class for euporie kernels."""

    def __init__(
        self,
        kernel_tab: KernelTab,
        allow_stdin: bool = False,
        default_callbacks: MsgCallbacks | None = None,
        connection_file: Path | None = None,
    ) -> None:
        """Initialize the kernel.

        Args:
            kernel_tab: The notebook this kernel belongs to
            allow_stdin: Whether the kernel is allowed to request input
            default_callbacks: The default callbacks to use on receipt of a message
            connection_file: Path to a file from which to load or to which to save
                kernel connection information
        """
        self.kernel_tab = kernel_tab
        self.allow_stdin = allow_stdin
        self._status = "stopped"
        self.error: Exception | None = None
        self.dead = False

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
    def status(self) -> str:
        """Get the current kernel status."""
        return self._status

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

    async def stop_(self, cb: Callable | None = None) -> None:
        """Stop the kernel asynchronously."""
        self.stop(cb)

    @abc.abstractmethod
    def run(
        self,
        source: str,
        wait: bool = False,
        callback: Callable[..., None] | None = None,
        **callbacks: Callable[..., Any],
    ) -> None:
        """Execute code in the kernel."""

    async def run_(
        self,
        source: str,
        wait: bool = False,
        callback: Callable[..., None] | None = None,
        **callbacks: Callable[..., Any],
    ) -> None:
        """Execute code in the kernel asynchronously."""
        self.run(source, wait, callback, **callbacks)

    @abc.abstractmethod
    def complete(self, code: str, cursor_pos: int) -> list[dict]:
        """Get code completions."""

    async def complete_(self, code: str, cursor_pos: int) -> list[dict]:
        """Get code completions asynchronously."""
        return self.complete(code, cursor_pos)

    @abc.abstractmethod
    def inspect(
        self,
        code: str,
        cursor_pos: int,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> Any:
        """Get code inspection/documentation."""

    async def inspect_(
        self,
        code: str,
        cursor_pos: int,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> Any:
        """Get code inspection/documentation asynchronously."""
        return self.inspect(code, cursor_pos, callback)

    @abc.abstractmethod
    def is_complete(
        self,
        code: str,
        timeout: int | float = 0.1,
        wait: bool = False,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Check if code is complete."""

    async def is_complete_(
        self,
        code: str,
        timeout: int | float = 0.1,
    ) -> dict[str, Any]:
        """Check if code is complete asynchronously."""
        return self.is_complete(code, timeout)

    @abc.abstractmethod
    def interrupt(self) -> None:
        """Interrupt the kernel."""

    @abc.abstractmethod
    def restart(self, wait: bool = False, cb: Callable | None = None) -> None:
        """Restart the kernel."""

    async def restart_(self) -> None:
        """Restart the kernel asynchronously."""
        self.restart()

    @abc.abstractmethod
    def shutdown(self, wait: bool = False) -> None:
        """Shutdown the kernel."""

    async def shutdown_(self) -> None:
        """Shutdown the kernel asynchronously."""
        self.shutdown()

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
