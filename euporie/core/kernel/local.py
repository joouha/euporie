"""Local Python interpreter kernel implementation."""

from __future__ import annotations

import io
import logging
import sys
import threading
from code import InteractiveInterpreter
from typing import TYPE_CHECKING, Any, Callable

from euporie.core.kernel.base import BaseKernel, MsgCallbacks

if TYPE_CHECKING:
    from pathlib import Path

    from euporie.core.tabs.kernel import KernelTab

log = logging.getLogger(__name__)


class LocalPythonKernel(BaseKernel):
    """Run code in a local Python interpreter."""

    def __init__(
        self,
        kernel_tab: KernelTab,
        allow_stdin: bool = False,
        default_callbacks: dict | None = None,
        connection_file: Path | None = None,
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
            connection_file=connection_file,
        )
        self._interpreter = InteractiveInterpreter()
        self._stdout = io.StringIO()
        self._stderr = io.StringIO()
        self._execution_count = 0
        self._lock = threading.Lock()

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

    def run(
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
        with self._lock:
            # Capture stdout/stderr
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = self._stdout, self._stderr

            try:
                self.status = "busy"
                self._execution_count += 1

                # Set execution count
                if callable(set_execution_count := callbacks.get("set_execution_count")):
                    set_execution_count(self._execution_count)

                # Run the code
                try:
                    # Parse the source into an AST
                    tree = ast.parse(source)

                    # No statements
                    if not tree.body:
                        result = None
                        status = "ok"
                    else:
                        # Split into statements and final expression
                        last = tree.body[-1]
                        is_expr = isinstance(last, ast.Expr)

                        # Execute all but the last statement
                        if len(tree.body) > 1:
                            exec_code = compile(ast.Module(body=tree.body[:-1], type_ignores=[]), "<string>", "exec")
                            self._interpreter.runcode(exec_code)

                        # Handle the last statement
                        if is_expr:
                            # Last statement is an expression - eval it
                            eval_code = compile(ast.Expression(body=last.value), "<string>", "eval")
                            result = eval(eval_code, self._interpreter.locals)
                        else:
                            # Last statement is not an expression - exec it
                            exec_code = compile(ast.Module(body=[last], type_ignores=[]), "<string>", "exec")
                            self._interpreter.runcode(exec_code)
                            result = None

                        status = "ok"

                    # If we got a result and have an output callback, display it
                    if result is not None and callable(add_output := callbacks.get("add_output")):
                        add_output(
                            {
                                "output_type": "execute_result",
                                "execution_count": self._execution_count,
                                "data": {"text/plain": repr(result)},
                                "metadata": {},
                            },
                            True,
                        )

                except Exception as e:
                    log.debug(e)
                    status = "error"

                # Get output
                output = self._stdout.getvalue()
                error = self._stderr.getvalue()

                # Call output callback if provided
                if callable(add_output := callbacks.get("add_output")):
                    if output:
                        add_output(
                            {"output_type": "stream", "name": "stdout", "text": output},
                            True,
                        )
                    if error:
                        add_output(
                            {"output_type": "stream", "name": "stderr", "text": error},
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

    def complete(self, code: str, cursor_pos: int) -> list[dict]:
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

    def inspect(
        self,
        code: str,
        cursor_pos: int,
        callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> Any:
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

    def is_complete(
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

    def restart(self, wait: bool = False, cb: Callable | None = None) -> None:
        """Restart the kernel."""
        self._interpreter = InteractiveInterpreter()
        self._execution_count = 0
        if callable(cb):
            cb({"status": "ok"})

    def shutdown(self, wait: bool = False) -> None:
        """Shutdown the kernel."""
        self.stop()
