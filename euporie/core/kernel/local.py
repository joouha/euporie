"""Local Python interpreter kernel implementation."""

from __future__ import annotations

import logging
import sys
import threading
import traceback
from contextlib import redirect_stderr, redirect_stdout
from io import TextIOBase
from linecache import cache as line_cache
from typing import TYPE_CHECKING, Any, Callable

from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import Python3TracebackLexer

from euporie.core.app.current import get_app
from euporie.core.kernel.base import BaseKernel, MsgCallbacks

if TYPE_CHECKING:
    from euporie.core.tabs.kernel import KernelTab

log = logging.getLogger(__name__)


class StdStream(TextIOBase):
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
        # Create interpreter with callback for error handling
        self.locals = {}
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
                "pygments_lexer": "python3",
                "codemirror_mode": {
                    "name": "python",
                    "version": sys.version_info.major,
                },
                "nbconvert_exporter": "python",
            },
            "implementation": sys.implementation.name,
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

    def showtraceback(self, filename: str, cb: Callable[dict[str, Any], bool]) -> None:
        """Format and display tracebacks for exceptions."""
        typ, value, tb = sys.exc_info()
        stack_summary = traceback.extract_tb(tb)

        # Filter items from stack prior to executed code
        for i, frame in enumerate(stack_summary):
            if frame.filename == filename:
                stack_summary = stack_summary[i:]
                break
        else:
            stack_summary = []

        # Format the traceback text
        traceback_text = "".join(
            [
                *traceback.format_list(stack_summary),
                *traceback.format_exception_only(typ, value),
            ]
        )

        # Color the traceback using Pygments
        colored_traceback = highlight(
            traceback_text,
            Python3TracebackLexer(),
            Terminal256Formatter(style=get_app().config.syntax_theme),
        ).rstrip()

        # Send the error through the callback
        cb(
            {
                "output_type": "error",
                "ename": typ.__name__,
                "evalue": str(value),
                "traceback": colored_traceback.splitlines(),
            },
            own=True,
        )

    async def run_async(
        self,
        source: str,
        wait: bool = False,
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

        def displayhook(value: Any) -> None:
            # Save reference to output
            self.locals[f"_{self._execution_count}"] = value
            # Display output
            if value is not None:
                if hasattr(value, "_repr_mimebundle_"):
                    data = value._repr_mimebundle_()
                else:
                    data = {}
                    for method, mime in [
                        # ("_repr_javascript_", "application/javascript"),
                        ("_repr_latex_", "text/latex"),
                        ("_repr_html_", "text/html"),
                        ("_repr_markdown_", "text/markdown"),
                        ("_repr_svg_", "image/svg+xml"),
                        ("_repr_jpeg_", "image/jpeg"),
                        ("_repr_png_", "image/png"),
                        # ("_repr_pretty_", "text/plain"),
                    ]:
                        if (
                            hasattr(value, method)
                            and (output := getattr(value, method)()) is not None
                        ):
                            data[mime] = output
                    if not data:
                        data = {"text/plain": repr(value)}
                add_output(
                    {
                        "output_type": "execute_result",
                        "execution_count": self._execution_count,
                        "data": data,
                        "metadata": {},
                    },
                    True,
                )

        with (
            redirect_stdout(StdStream("stdout", add_output)),
            redirect_stderr(StdStream("stderr", add_output)),
        ):
            self.status = "busy"
            self._execution_count += 1

            # Set execution count
            if callable(set_execution_count := callbacks.get("set_execution_count")):
                set_execution_count(self._execution_count)

            filename = f"<input_{self._execution_count}>"
            line_cache[filename] = (
                len(source),
                None,
                source.splitlines(keepends=True),
                filename,
            )
            try:
                # Parse the source into an AST
                tree = ast.parse(source, filename=filename)
            except Exception:
                # Check for syntax errors
                self.showtraceback(filename, cb=callbacks["add_output"])
            else:
                if tree.body:
                    # Split into statements and final expression
                    body = tree.body
                    last = None
                    if isinstance(tree.body[-1], ast.Expr):
                        last = tree.body.pop()

                    with self._lock:
                        # Execute body
                        try:
                            sys.displayhook = displayhook
                            if body:
                                exec(  # noqa: S102
                                    compile(
                                        ast.Module(body=body, type_ignores=[]),
                                        # ast.Interactive(body),
                                        filename=filename,
                                        # mode="single",
                                        mode="exec",
                                    ),
                                    self.locals,
                                )
                            # Last statement is an expression - eval it
                            if last is not None:
                                exec(  # noqa: S102
                                    compile(
                                        ast.Interactive([last]),
                                        filename=filename,
                                        mode="single",
                                    ),
                                    self.locals,
                                )
                        except SystemExit:
                            get_app().exit()
                        except Exception:
                            log.exception("")
                            try:
                                self.showtraceback(filename, cb=callbacks["add_output"])
                            except Exception:
                                log.exception("")
                        finally:
                            sys.displayhook = sys.__displayhook__

        self.status = "idle"

    async def complete_async(self, code: str, cursor_pos: int) -> list[dict]:
        """Get code completions."""
        import rlcompleter

        completer = rlcompleter.Completer(self.locals)

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
        detail_level: int = 0,
        timeout: int = 2,
    ) -> dict[str, Any]:
        """Get code inspection/documentation."""
        import inspect

        # Find the start of the word (going backwards from cursor)
        start = cursor_pos
        while (start >= 0 and code[start - 1].isalnum()) or code[start - 1] in "._":
            start -= 1
        # Find the end of the word (going forwards from cursor)
        end = cursor_pos
        while end < len(code) and (code[end].isalnum() or code[end] in "._"):
            end += 1
        # Extract the complete word
        obj_name = code[start:end].strip()
        if not obj_name:
            return {}
        try:
            obj = eval(obj_name, self.locals)  # noqa: S307
        except Exception:
            return {}
        else:
            if doc := inspect.getdoc(obj):
                return {"text/plain": doc}
        return {}

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
            compiled = code.compile(code, "<input>", "exec")
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
        self.locals.clear()
        self._execution_count = 0
        if callable(cb):
            cb({"status": "ok"})

    async def shutdown_async(self, wait: bool = False) -> None:
        """Shutdown the kernel."""
        self.stop()
