"""Local Python interpreter kernel implementation."""

from __future__ import annotations

import asyncio
import io
import logging
import sys
import threading
from code import InteractiveInterpreter
from io import TextIOBase
from typing import TYPE_CHECKING, Any, Callable

from euporie.core.kernel.base import BaseKernel, MsgCallbacks

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal

    from euporie.core.tabs.kernel import KernelTab

log = logging.getLogger(__name__)


class LocalKernelIO(TextIOBase):
    """StringIO that calls a callback when written to."""

    def __init__(self, name: str, callback: Callable[[dict, bool], None]) -> None:
        """Create a new IO object for the local kernel.

        Args:
            name: The name of the stream (stdout or stderr)
            callback: The callback to add output to the kernel tab
        """
        self._name = name
        self._callback = callback
        self._buffer = ""

    def write(self, s: str) -> None:
        """Write the written data as a cell output."""
        if s:
            self._buffer += s
            if "\n" in self._buffer:
                lines = self._buffer.split("\n")
                # Keep any remaining text after last newline
                self._buffer = lines[-1]
                self._callback(
                    {
                        "output_type": "stream",
                        "name": self._name,
                        "text": "\n".join(lines[:-1]) + "\n",
                    },
                    True,
                )

    def flush(self) -> None:
        """Flush any remaining buffered content."""
        if self._buffer:
            self._callback(
                {"output_type": "stream", "name": self._name, "text": self._buffer},
                True,
            )
            self._buffer = ""


class LocalInterpreter(InteractiveInterpreter):
    """A Python interpreter which can be run locally."""


class LocalPythonKernel(BaseKernel):
    """Run code in a local Python interpreter."""

    def __init__(
        self,
        kernel_tab: KernelTab,
        allow_stdin: bool = False,
        default_callbacks: dict | None = None,
    ) -> None:
        """Initialize the local Python interpreter kernel.

        Args:
            kernel_tab: The notebook this kernel belongs to
            allow_stdin: Whether the kernel is allowed to request input
            default_callbacks: The default callbacks to use on receipt of a message
            connection_file: Not used for local kernel
        """
        super().__init__(
            kernel_tab=kernel_tab,
            allow_stdin=allow_stdin,
            default_callbacks=default_callbacks,
        )
        self._interpreter = InteractiveInterpreter()
        self._execution_count = 0
        self._lock = threading.Lock()

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._setup_loop)
        self.thread.daemon = True
        self.thread.start()

    def _setup_loop(self) -> None:
        """Set the current loop the the kernel's event loop.

        This method is intended to be run in the kernel thread.
        """
        asyncio.set_event_loop(self.loop)
        self.status_change_event = asyncio.Event()
        self.loop.run_forever()

    @property
    def specs(self) -> dict[str, dict]:
        """Return available kernel specifications."""
        return {
            "local-python": {
                "spec": {
                    "argv": [sys.executable],
                    "env": {},
                    "display_name": "Local Python",
                    "language": "python",
                    "interrupt_mode": "message",
                    "metadata": {},
                }
            }
        }

    @property
    def missing(self) -> bool:
        """Return whether the kernel is missing."""
        return False

    @property
    def id(self) -> str | None:
        """Return the kernel ID."""
        return "local-python"

    @property
    def kc(self) -> None:
        """Return None as local kernels don't have a kernel client."""
        return None

    def info(
        self,
        set_kernel_info: Callable[[dict[str, Any]], None] | None = None,
        set_status: Callable[[str], None] | None = None,
    ) -> None:
        """Request information about the kernel.

        Args:
            set_kernel_info: Callback to set kernel info
            set_status: Callback to set kernel status
        """
        kernel_info = {
            "language_info": {
                "name": "python",
                "version": sys.version.split()[0],
                "mimetype": "text/x-python",
                "file_extension": ".py",
                "pygments_lexer": "ipython3",
                "codemirror_mode": {
                    "name": "python",
                    "version": 3,
                },
                "nbconvert_exporter": "python",
            },
            "implementation": "cpython",
            "implementation_version": sys.version.split()[0],
            "banner": f"Python {sys.version}",
            "help_links": [],
            "status": "ok",
        }

        if callable(set_kernel_info):
            set_kernel_info(kernel_info)

        if callable(set_status):
            set_status("idle")

    def start(
        self, cb: Callable | None = None, wait: bool = False, timeout: int = 10
    ) -> None:
        """Start the local interpreter."""
        self.status = "idle"
        if callable(cb):
            cb({"status": "ok"})

    def stop(self, cb: Callable | None = None, wait: bool = False) -> None:
        """Stop the local interpreter."""
        self.status = "stopped"
        if callable(cb):
            cb()

    async def run_async(
        self,
        source: str,
        wait: bool = False,
        callback: Callable[..., None] | None = None,
        **callbacks: Callable[..., Any],
    ) -> None:
        """Execute code in the local interpreter."""
        import ast

        callbacks = MsgCallbacks(
            {
                **self.default_callbacks,
                **{k: v for k, v in callbacks.items() if v is not None},
            }
        )

        add_output = callbacks["add_output"]
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = (
            LocalKernelIO("stdout", add_output),
            LocalKernelIO("stderr", add_output),
        )

        try:
            self.status = "busy"
            self._execution_count += 1

            # Set execution count
            if callable(set_execution_count := callbacks.get("set_execution_count")):
                set_execution_count(self._execution_count)

            # Parse the source into an AST
            tree = ast.parse(source)

            status = "ok"
            result = None

            if tree.body:
                # Split into statements and final expression
                last = tree.body[-1]
                is_last_expr = isinstance(last, ast.Expr)
                body = tree.body[:-1] if is_last_expr else tree.body

                with self._lock:
                    # Execute body
                    if body:
                        self._interpreter.runcode(
                            compile(
                                ast.Module(body=body, type_ignores=[]),
                                filename="<input>",
                                mode="exec",
                            )
                        )
                    # Last statement is an expression - eval it
                    if is_last_expr:
                        result = eval(  # noqa: S307
                            compile(
                                ast.Expression(body=last.value),
                                filename="<input>",
                                mode="eval",
                            ),
                            self._interpreter.locals,
                        )

            # If we got a result and have an output callback, display it
            if result is not None and callable(
                add_output := callbacks.get("add_output")
            ):
                add_output(
                    {
                        "output_type": "execute_result",
                        "execution_count": self._execution_count,
                        "data": {"text/plain": repr(result)},
                        "metadata": {},
                    },
                    True,
                )

            if callable(callback):
                callback({"status": status})

        finally:
            # Restore stdout/stderr
            sys.stdout, sys.stderr = old_stdout, old_stderr
            self._stdout = io.StringIO()
            self._stderr = io.StringIO()
            self.status = "idle"

    async def complete_async(self, code: str, cursor_pos: int) -> list[dict]:
        """Get code completions."""
        import rlcompleter

        # Create namespace for completer
        namespace = self._interpreter.locals
        completer = rlcompleter.Completer(namespace)

        # Find the last word before cursor
        tokens = code[:cursor_pos].split()
        if not tokens:
            return []

        word = tokens[-1]
        completions = []

        # Get all possible completions
        i = 0
        while True:
            completion = completer.complete(word, i)
            if completion is None:
                break
            completions.append({"text": completion, "start_position": -len(word)})
            i += 1

        return completions

    async def inspect_async(
        self,
        code: str,
        cursor_pos: int,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """Get code inspection/documentation."""
        import inspect

        # Try to get the object name at cursor position
        tokens = code[:cursor_pos].split()
        if not tokens:
            return None

        obj_name = tokens[-1]
        try:
            obj = eval(obj_name, self._interpreter.locals)  # noqa: S307
            doc = inspect.getdoc(obj)
            if doc and callable(callback):
                callback({"status": "ok", "data": {"text/plain": doc}, "found": True})
        except:  # noqa: E722
            if callable(callback):
                callback({"status": "ok", "data": {}, "found": False})

    async def is_complete_async(
        self,
        code: str,
        timeout: int | float = 0.1,
        wait: bool = False,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Check if code is complete."""
        try:
            # Try to compile the code
            compiled = code.compile(code, "<string>", "exec")
            status = "complete" if compiled else "incomplete"
        except SyntaxError as e:
            if e.msg == "unexpected EOF while parsing":
                status = "incomplete"
            else:
                status = "invalid"
        except Exception:
            status = "invalid"

        result = {"status": status}
        if callable(callback):
            callback(result)
        return result

    def interrupt(self) -> None:
        """Interrupt the kernel."""
        # Local interpreter runs in the main thread, so we can't really interrupt it

    async def restart_async(
        self, wait: bool = False, cb: Callable | None = None
    ) -> None:
        """Restart the kernel."""
        self._interpreter = InteractiveInterpreter()
        self._execution_count = 0
        if callable(cb):
            cb({"status": "ok"})

    async def shutdown_async(self, wait: bool = False) -> None:
        """Shutdown the kernel."""
        self.stop()
