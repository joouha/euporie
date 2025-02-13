"""Local Python interpreter kernel implementation."""

from __future__ import annotations

import ast
import code
import getpass
import logging
import sys
import threading
import traceback
from asyncio import to_thread
from functools import update_wrapper
from linecache import cache as line_cache
from typing import TYPE_CHECKING, cast

from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import Python3TracebackLexer

from euporie.core.app.current import get_app
from euporie.core.kernel.base import BaseKernel, KernelInfo, MsgCallbacks

if TYPE_CHECKING:
    from typing import Any, Callable, Unpack

    from euporie.core.tabs.kernel import KernelTab

log = logging.getLogger(__name__)


class LocalPythonKernel(BaseKernel):
    """Run code in a local Python interpreter."""

    @classmethod
    def variants(cls) -> list[KernelInfo]:
        """Return available kernel specifications."""
        return [
            KernelInfo(
                name="local-python",
                display_name="Local Python",
                factory=cls,
                kind="new",
                type=cls,
            )
        ]

    # Thread-local storage for callbacks during execution
    _thread_local = threading.local()

    def __init__(
        self,
        kernel_tab: KernelTab,
        default_callbacks: MsgCallbacks | None = None,
        allow_stdin: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the local Python interpreter kernel.

        Args:
            kernel_tab: The notebook this kernel belongs to
            allow_stdin: Whether the kernel is allowed to request input
            default_callbacks: The default callbacks to use on receipt of a message
            connection_file: Not used for local kernel
            **kwargs: Additional keyword arguments
        """
        super().__init__(
            kernel_tab=kernel_tab,
            allow_stdin=allow_stdin,
            default_callbacks=default_callbacks,
        )
        # Create interpreter with callback for error handling
        self.locals: dict[str, object] = {}
        self.execution_count = 0
        self.kc = None
        self._input_event = threading.Event()
        self._input_buffer: str | None = None
        self.hook_manager = HookManager(self)

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
            "help_links": ["https://euporie.readthedocs.io/"],
            "status": "ok",
        }

        if callable(set_kernel_info):
            set_kernel_info(kernel_info)

        if callable(set_status):
            set_status(self.status)

    async def start_async(self) -> None:
        """Start the local interpreter."""
        self.error = None
        self.status = "idle"
        self.locals.clear()
        self.execution_count = 0
        if callable(
            set_execution_count := self.default_callbacks.get("set_execution_count")
        ):
            set_execution_count(self.execution_count)

    @property
    def spec(self) -> dict[str, str]:
        """The kernelspec metadata for the current kernel instance."""
        return {
            "name": "local-python",
            "display_name": "Local Python",
            "language": "python",
        }

    def stop(self, cb: Callable | None = None, wait: bool = False) -> None:
        """Stop the local interpreter."""
        self.status = "stopped"
        if callable(cb):
            cb()

    def showtraceback(
        self, filename: str, cb: Callable[[dict[str, Any], bool], None] | None
    ) -> None:
        """Format and display tracebacks for exceptions."""
        typ, value, tb = sys.exc_info()
        stack_summary = list(traceback.extract_tb(tb))

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
        if callable(cb):
            cb(
                {
                    "output_type": "error",
                    "ename": "Exception" if typ is None else typ.__name__,
                    "evalue": str(value),
                    "traceback": colored_traceback.splitlines(),
                },
                True,
            )

    def _execute_code(
        self,
        body: list[ast.stmt],
        last: ast.stmt | None,
        filename: str,
        callbacks: MsgCallbacks,
    ) -> None:
        """Execute code in the interpreter.

        Args:
            body: List of statements to execute
            last: Optional final expression to evaluate
            filename: Source filename for tracebacks
            callbacks: Message callbacks
        """
        # Store callbacks in thread local storage
        self._thread_local.callbacks = callbacks
        add_output = callbacks["add_output"]

        with self.hook_manager:
            # Execute body
            try:
                if body:
                    exec(  # noqa: S102
                        compile(
                            ast.Module(body=body, type_ignores=[]),
                            filename=filename,
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
                self.showtraceback(filename, cb=add_output)
                if callable(done := callbacks.get("done")):
                    done({"status": "error"})

    async def run_async(
        self, source: str, **local_callbacks: Unpack[MsgCallbacks]
    ) -> None:
        """Execute code in the local interpreter."""
        callbacks = MsgCallbacks(
            {
                **self.default_callbacks,
                **cast(
                    "MsgCallbacks",
                    {k: v for k, v in local_callbacks.items() if v is not None},
                ),
            }
        )

        self.status = "busy"

        # Set execution count
        self.execution_count += 1
        if callable(set_execution_count := callbacks.get("set_execution_count")):
            set_execution_count(self.execution_count)

        # Add source to line cache (for display in tracebacks)
        filename = f"<input_{self.execution_count}>"
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
            return
        else:
            if not tree.body:
                return

        # Split into statements and final expression
        body = tree.body
        last = None
        if isinstance(tree.body[-1], ast.Expr):
            last = tree.body.pop()

        # Execute the code in a thread
        await to_thread(self._execute_code, body, last, filename, callbacks)

        self.status = "idle"

        if callable(done := callbacks.get("done")):
            done({"status": "ok"})

    async def complete_async(self, source: str, cursor_pos: int) -> list[dict]:
        """Get code completions."""
        import rlcompleter

        completer = rlcompleter.Completer(self.locals)

        # Find the last word before cursor
        tokens = source[:cursor_pos].split()
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
        source: str,
        cursor_pos: int,
        detail_level: int = 0,
        timeout: int = 2,
    ) -> dict[str, Any]:
        """Get code inspection/documentation."""
        import inspect

        if not source:
            return {}

        # Find the start of the word (going backwards from cursor)
        start = cursor_pos
        while (start >= 0 and source[start - 1].isalnum()) or source[start - 1] in "._":
            start -= 1
        # Find the end of the word (going forwards from cursor)
        end = cursor_pos
        while end < len(source) and (source[end].isalnum() or source[end] in "._"):
            end += 1
        # Extract the complete word
        obj_name = source[start:end].strip()
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
        source: str,
        timeout: int | float = 0.1,
    ) -> dict[str, Any]:
        """Check if code is complete."""
        try:
            compiled = code.compile_command(
                source, f"<input_{self.execution_count}>", "exec"
            )
        except Exception:
            status = "invalid"
        else:
            status = "incomplete" if compiled is None else "complete"

        result = {"status": status, "indent": "    " if source[-1:] in ":({[" else ""}
        return result

    def input(self, text: str) -> None:
        """Send input to the kernel.

        Args:
            text: The input text to provide
        """
        self._input_buffer = text
        self._input_event.set()

    def interrupt(self) -> None:
        """Interrupt the kernel."""
        log.warning("Cannot interrupt kernel %r", self)

    async def restart_async(
        self, wait: bool = False, cb: Callable | None = None
    ) -> None:
        """Restart the kernel."""
        await self.start_async()
        if callable(cb):
            cb({"status": "ok"})

    async def shutdown_async(self, wait: bool = False) -> None:
        """Shutdown the kernel."""
        self.stop()


def get_display_data(obj: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Get display data and metadata for an object.

    Args:
        obj: Object to get display data for

    Returns:
        Tuple of (data, metadata) dictionaries
    """
    data = {}
    metadata = {}

    if hasattr(obj, "_repr_mimebundle_"):
        output = obj._repr_mimebundle_()
        if isinstance(output, tuple):
            data, metadata = output
        else:
            data = output
    else:
        for method, mime in [
            ("_repr_latex_", "text/latex"),
            ("_repr_html_", "text/html"),
            ("_repr_markdown_", "text/markdown"),
            ("_repr_svg_", "image/svg+xml"),
            ("_repr_jpeg_", "image/jpeg"),
            ("_repr_png_", "image/png"),
        ]:
            if hasattr(obj, method) and (output := getattr(obj, method)()) is not None:
                data[mime] = output
        if not data:
            data = {"text/plain": repr(obj)}

    return data, metadata


class BaseHook:
    """Base class providing access to thread-specific callbacks."""

    def __init__(self, kernel: LocalPythonKernel) -> None:
        """Initialize the base hook.

        Args:
            kernel: The kernel instance to hook
        """
        self._kernel = kernel

    @property
    def callbacks(self) -> MsgCallbacks:
        """Get callbacks for current thread."""
        return getattr(
            self._kernel._thread_local, "callbacks", self._kernel.default_callbacks
        )


class DisplayHook(BaseHook):
    """Hook for sys.displayhook that dispatches to thread-specific callbacks."""

    def __call__(self, value: Any) -> None:
        """Handle display of values."""
        if value is None:
            return

        if callbacks := self.callbacks:
            # Store value in kernel locals
            self._kernel.locals[f"_{self._kernel.execution_count}"] = value

            # Get display data and metadata
            data, metadata = get_display_data(value)

            if callable(callback := callbacks.get("add_output")):
                callback(
                    {
                        "output_type": "execute_result",
                        "execution_count": self._kernel.execution_count,
                        "data": data,
                        "metadata": metadata,
                    },
                    True,
                )


class DisplayGlobal(BaseHook):
    """A display() function that dispatches to thread-specific callbacks.

    This class implements the global display() function used to show rich output
    in notebooks. It routes display calls to the appropriate output callbacks.
    """

    def __call__(
        self,
        *objs: Any,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        transient: dict[str, Any] | None = None,
        display_id: str | None = None,
        raw: bool = False,
        clear: bool = False,
        **kwargs: Any,
    ) -> None:
        """Handle display of values in the notebook.

        Args:
            *objs: Objects to display. Each object will be displayed in sequence.
            include: List of MIME types to include in the output. If specified,
                only these MIME types will be included.
            exclude: List of MIME types to exclude from the output. These MIME
                types will be filtered out.
            metadata: Additional metadata to attach to the display data.
            transient: Transient data that is used for display but not persisted
                in the notebook document.
            display_id: Unique identifier for the display. Can be used to update
                this display output later.
            raw: If True, skip MIME type transformation/formatting of the objects.
            clear: If True, clear the output before displaying new content.
            **kwargs: Additional display arguments passed to the frontend.
        """
        add_output = self.callbacks.get("add_output")
        if not callable(add_output):
            return

        for obj in objs:
            data, obj_metadata = get_display_data(obj)

            # Filter mime types
            if include:
                data = {k: v for k, v in data.items() if k in include}
            if exclude:
                data = {k: v for k, v in data.items() if k not in exclude}

            # Merge metadata
            if metadata:
                obj_metadata.update(metadata)

            add_output(
                {
                    "output_type": "display_data",
                    "data": data,
                    "metadata": obj_metadata,
                    "transient": transient,
                    "display_id": display_id,
                },
                True,
            )


class InputBuiltin(BaseHook):
    """Hook for input and getpass that dispatches to thread-specific callbacks."""

    def __init__(self, kernel: LocalPythonKernel, is_password: bool = False) -> None:
        """Initialize the input hook.

        Args:
            kernel: The kernel instance to hook
            is_password: Whether this is for password input
        """
        super().__init__(kernel)
        self._is_password = is_password
        update_wrapper(self, input)

    def __call__(self, prompt: str = "", stream: Any = None) -> str:
        """Get input from user via callback."""
        if (callbacks := self.callbacks) and (get_input := callbacks.get("get_input")):
            # Clear any previous input
            self._kernel._input_event.clear()
            self._kernel._input_buffer = None

            # Request input via callback
            get_input(prompt, self._is_password)

            # Wait for input to be provided
            self._kernel._input_event.wait()

            # Return the input, or empty string if none provided
            return self._kernel._input_buffer or ""
        return ""


class StreamWrapper(BaseHook):
    """Hook for stdout/stderr that dispatches to thread-specific callbacks."""

    def __init__(self, name: str, kernel: LocalPythonKernel) -> None:
        """Initialize the stream hook.

        Args:
            name: Name of the stream (stdout/stderr)
            kernel: The kernel instance to hook
        """
        BaseHook.__init__(self, kernel)
        self.name = name
        self._thread_local = threading.local()

    @property
    def buffer(self) -> str:
        """Get the thread-local buffer for this stream."""
        if not hasattr(self._thread_local, "buffer"):
            self._thread_local.buffer = ""
        return self._thread_local.buffer

    @buffer.setter
    def buffer(self, value: str) -> None:
        self._thread_local.buffer = value

    def _send(self, text: str, callbacks: MsgCallbacks) -> None:
        """Send text to the frontend via callback."""
        if callable(callback := callbacks.get("add_output")):
            callback(
                {"output_type": "stream", "name": self.name, "text": text},
                True,
            )

    def write(self, text: str) -> int:
        """Write output using callback for current thread."""
        if not isinstance(text, str):
            raise TypeError(f"write() argument must be str, not {type(text)}")
        if not text or not (callbacks := self.callbacks):
            return 0

        # Handle any buffered content plus new text
        all_text = self.buffer + text
        lines = all_text.splitlines(keepends=True)
        if lines[-1].endswith("\n"):
            self.buffer = ""
        else:
            self.buffer = lines[-1]
            lines = lines[:-1]
        if lines:
            # Send complete lines immediately
            self._send("".join(lines), callbacks)

        return len(text)

    def flush(self) -> None:
        """Flush any buffered content."""
        if self.buffer and (callbacks := self.callbacks):
            self._send(self.buffer, callbacks)
            self.buffer = ""


class HookManager:
    """Context manager for hooking stdout/stderr/displayhook."""

    def __init__(self, kernel: LocalPythonKernel) -> None:
        """Initialize the hook manager.

        Args:
            kernel: The kernel instance to hook
        """
        # Create hook instances
        self.stdout = StreamWrapper("stdout", kernel)
        self.stderr = StreamWrapper("stderr", kernel)
        self.displayhook = DisplayHook(kernel)
        self.display = DisplayGlobal(kernel)
        self.input = InputBuiltin(kernel, is_password=False)
        self.getpass = InputBuiltin(kernel, is_password=True)
        # Store original objects
        self.og_stdout = sys.stdout
        self.og_stderr = sys.stderr
        self.og_displayhook = sys.displayhook
        self.og_getpass = getpass.getpass
        # Track hook depth
        self._depth = 0
        self._kernel = kernel

    def __enter__(self) -> None:
        """Replace objects with hooks."""
        if self._depth == 0:
            # Replace system streams
            sys.stdout = self.stdout
            sys.stderr = self.stderr
            sys.displayhook = self.displayhook
            # Replace getpass
            getpass.getpass = self.getpass
            # Add input to kernel locals
            self._kernel.locals["input"] = self.input
            # Add display to kernel locals
            self._kernel.locals["display"] = self.display
        self._depth += 1

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Restore original objects."""
        self._depth -= 1
        if self._depth == 0:
            # Restore system streams
            sys.stdout = self.og_stdout
            sys.stderr = self.og_stderr
            sys.displayhook = self.og_displayhook
            # Restore getpass
            getpass.getpass = self.og_getpass
            # Remove input from kernel locals
            self._kernel.locals.pop("input", None)
            self._kernel.locals.pop("display", None)
        # Flush any remaining stream outputs
        self.stdout.flush()
        self.stderr.flush()
