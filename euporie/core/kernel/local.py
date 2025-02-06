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
from contextlib import ExitStack
from functools import wraps
from io import TextIOWrapper
from linecache import cache as line_cache
from typing import TYPE_CHECKING, ClassVar, cast

from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import Python3TracebackLexer

from euporie.core.app.current import get_app
from euporie.core.kernel.base import BaseKernel, KernelInfo, MsgCallbacks

if TYPE_CHECKING:
    from typing import Any, Callable, Unpack

    from euporie.core.tabs.kernel import KernelTab

log = logging.getLogger(__name__)


def display(
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
    """Display objects using rich representation.

    Args:
        *objs: Objects to display
        include: List of mime types to include
        exclude: List of mime types to exclude
        metadata: Additional metadata to include
        transient: Transient data associated with the display
        display_id: Identifier for updating display data
        raw: Skip transformation/formatting
        clear: Clear output before displaying
        **kwargs: Additional display arguments
    """
    raise RuntimeError("Display function not properly initialized")


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
        self._execution_count = 0
        self.kc = None
        self._input_event = threading.Event()
        self._input_buffer = None

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

    def _get_display_data(self, obj: Any) -> tuple[dict[str, Any], dict[str, Any]]:
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
                if (
                    hasattr(obj, method)
                    and (output := getattr(obj, method)()) is not None
                ):
                    data[mime] = output
            if not data:
                data = {"text/plain": repr(obj)}

        return data, metadata

    def _make_display_func(self) -> Callable:
        """Create a display function bound to a kernel instance."""

        @wraps(display)
        def _display(
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
            if not hasattr(self._thread_local, "callbacks"):
                return

            add_output = self._thread_local.callbacks.get("add_output")
            if not callable(add_output):
                return

            for obj in objs:
                data, obj_metadata = self._get_display_data(obj)

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

        return _display

    def _displayhook(self, value: Any) -> None:
        """Handle display of expression values.

        Args:
            value: The value to display
        """
        # Save reference to output
        self.locals[f"_{self._execution_count}"] = value

        # Display output
        if value is not None and hasattr(self._thread_local, "callbacks"):
            add_output = self._thread_local.callbacks.get("add_output")
            if callable(add_output):
                data, metadata = self._get_display_data(value)
                add_output(
                    {
                        "output_type": "execute_result",
                        "execution_count": self._execution_count,
                        "data": data,
                        "metadata": metadata,
                    },
                    True,
                )

    def _execute_code(
        self,
        body: list[ast.stmt],
        last: ast.Expr | None,
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

        # Add display function to locals
        self.locals["display"] = self._make_display_func()
        # Add input functions to locals
        self.locals["input"] = self._make_input_func()

        stdout = StreamWrapper("stdout", self)
        stderr = StreamWrapper("stderr", self)
        hook_stdout = SysHookManager(sys, "stdout", stdout)
        hook_stderr = SysHookManager(sys, "stderr", stderr)
        hook_display = SysHookManager(sys, "displayhook", self._displayhook)
        hook_getpass = SysHookManager(
            getpass, "getpass", self._make_input_func(is_password=True)
        )

        with ExitStack() as stack:
            # Set up stack
            stack.enter_context(hook_stdout)
            stack.enter_context(hook_stderr)
            stack.callback(stdout.flush)
            stack.callback(stderr.flush)
            stack.enter_context(hook_display)
            stack.enter_context(hook_getpass)

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
        self._execution_count += 1
        if callable(set_execution_count := callbacks.get("set_execution_count")):
            set_execution_count(self._execution_count)

        # Add source to line cache (for display in tracebacks)
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
                source, f"<input_{self._execution_count}>", "exec"
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

    def _make_input_func(self, is_password: bool = False) -> Callable[[str], str]:
        """Create an input function that uses the kernel's input mechanism.

        Args:
            is_password: Whether this is for password input (don't echo)

        Returns:
            An input function that uses kernel callbacks
        """

        @wraps(input)
        def _input(prompt: str = "") -> str:
            """Get input from the user.

            Args:
                prompt: Text to display when requesting input

            Returns:
                The input string from the user
            """
            # Clear any previous input
            self._input_event.clear()
            self._input_buffer = None

            # Request input via callback
            if hasattr(self._thread_local, "callbacks"):
                get_input = self._thread_local.callbacks.get("get_input")
                if callable(get_input):
                    get_input(prompt, is_password)

            # Wait for input to be provided
            self._input_event.wait()

            # Return the input, or empty string if none provided
            return self._input_buffer or ""

        return _input

    def interrupt(self) -> None:
        """Interrupt the kernel."""
        log.warning("Cannot interrupt kernel %r", self)

    async def restart_async(
        self, wait: bool = False, cb: Callable | None = None
    ) -> None:
        """Restart the kernel."""
        self.locals.clear()
        self._execution_count = 0
        await self.start_async()
        if callable(cb):
            cb({"status": "ok"})

    async def shutdown_async(self, wait: bool = False) -> None:
        """Shutdown the kernel."""
        self.stop()


class SysHookManager:
    """Manages system hooks with depth tracking."""

    _depths: ClassVar[dict[object, int]] = {}
    _lock = threading.Lock()

    def __init__(self, parent: object, name: str, replacement: object) -> None:
        """Initialize the stream manager.

        Args:
            parent: The owner of the object being replaced
            name: The name of the attribute being replaced
            replacement: The replacement
        """
        self.parent = parent
        self.name = name
        self.original = getattr(parent, name)
        self.replacement = replacement
        with self._lock:
            self._depths.setdefault((parent, name), 0)

    def __enter__(self) -> None:
        """Set up stream redirection."""
        with self._lock:
            self._depths[self.parent, self.name] += 1
        setattr(self.parent, self.name, self.replacement)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Tear down stream redirection."""
        with self._lock:
            if self._depths[self.parent, self.name] > 0:
                self._depths[self.parent, self.name] -= 1
            if self._depths[self.parent, self.name] == 0:
                setattr(self.parent, self.name, self.original)


class StreamWrapper(TextIOWrapper):
    """StringIO that calls a callback when written to."""

    # Class-level storage for thread-local state
    _thread_local = threading.local()

    def __init__(
        self,
        name: str,
        kernel: LocalPythonKernel,
    ) -> None:
        """Create a new IO object for the local kernel.

        Args:
            name: The name of the stream being wrapped
            kernel: The kernel instance
        """
        self._name = name
        self._kernel = kernel
        self._buffer = ""

    def write(self, s: str) -> int:
        """Write the written data as a cell output."""
        if s:
            self._buffer += s
            if "\n" in self._buffer:
                lines = self._buffer.split("\n")
                # Keep any remaining text after last newline
                self._buffer = lines[-1]
                callback = self._kernel._thread_local.callbacks.get("add_output")
                if callable(callback):
                    callback(
                        {
                            "output_type": "stream",
                            "name": self._name,
                            "text": "\n".join(lines[:-1]) + "\n",
                        },
                        True,
                    )
        return len(s)

    def flush(self) -> None:
        """Flush any remaining buffered content."""
        if self._buffer:
            if hasattr(self._kernel._thread_local, "callbacks"):
                callback = self._kernel._thread_local.callbacks.get("add_output")
                if callable(callback):
                    callback(
                        {
                            "output_type": "stream",
                            "name": self._name,
                            "text": self._buffer,
                        },
                        True,
                    )
            self._buffer = ""
