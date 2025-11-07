"""Local Python interpreter kernel implementation."""

from __future__ import annotations

import ast
import code
import getpass
import logging
import os
import sys
import threading
import traceback
from asyncio import to_thread
from base64 import b64encode
from contextlib import AbstractContextManager, ExitStack
from functools import update_wrapper
from linecache import cache as line_cache
from pathlib import Path
from typing import TYPE_CHECKING, cast

from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import Python3TracebackLexer

from euporie.core.app.current import get_app
from euporie.core.kernel.base import BaseKernel, KernelInfo, MsgCallbacks

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, ClassVar, TextIO, Unpack

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

    # Registry for magic commands
    magics: ClassVar[
        dict[str, Callable[[list[str], MsgCallbacks, LocalPythonKernel], Any]]
    ] = {}

    @classmethod
    def register_magic(
        cls, name: str
    ) -> Callable[
        [Callable[[list[str], MsgCallbacks, LocalPythonKernel], Any]],
        Callable[[list[str], MsgCallbacks, LocalPythonKernel], Any],
    ]:
        """Register a new magic command.

        Args:
            name: The magic command name (without the % prefix)

        Returns:
            Decorator function that registers the magic handler
        """

        def decorator(
            func: Callable[[list[str], MsgCallbacks, LocalPythonKernel], Any],
        ) -> Callable[[list[str], MsgCallbacks, LocalPythonKernel], Any]:
            cls.magics[name] = func
            return func

        return decorator

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

    def init_venv(self) -> None:
        """Add the current venv to sys.path so we can import modules from it.

        This isn't perfect: it doesn't use the Python interpreter with which the
        virtualenv was built, and it ignores the --no-site-packages option. A warning
        will appear suggesting the user installs euporie in the virtualenv or to use a
        Jupyter kernel, but for many cases, it probably works well enough.

        Adapted from :py:mod:`IPython`.
        """
        # Check if we are in a virtual environment
        if "VIRTUAL_ENV" not in os.environ:
            return
        elif os.environ["VIRTUAL_ENV"] == "":
            log.warning(
                "The virtual environment path is set to '': "
                "please check if this is intentional."
            )
            return

        # Follow sys.executable symlink trail, recoding all paths along the way
        # We need to check all of these
        paths = [Path(sys.executable)]
        while (path := paths[-1]).is_symlink():
            new_path = path.readlink()
            if not new_path.is_absolute():
                new_path = path.parent / new_path
            paths.append(new_path)

        # Get the venv path
        p_venv = Path(os.environ["VIRTUAL_ENV"]).resolve()
        # In Cygwin paths like "c:\..." and '\cygdrive\c\...' are possible
        if len(p_venv.parts) > 2 and p_venv.parts[1] == "cygdrive":
            drive_name = p_venv.parts[2]
            p_venv = (drive_name + ":/") / Path(*p_venv.parts[3:])

        # Check if the executable is already inside or has access to the virtualenv
        if any(p_venv == p.parents[1].resolve() for p in paths):
            return

        # Locate the site-packages of the virtual environment
        if sys.platform == "win32":
            virtual_env = str(Path(os.environ["VIRTUAL_ENV"], "Lib", "site-packages"))
        else:
            import re

            virtual_env_path = Path(
                os.environ["VIRTUAL_ENV"], "lib", "python{}.{}", "site-packages"
            )
            p_ver = tuple(str(x) for x in sys.version_info[:2])

            # Predict version from py[thon]-x.x in the $VIRTUAL_ENV
            re_m = re.search(r"\bpy(?:thon)?([23])\.(\d+)\b", os.environ["VIRTUAL_ENV"])
            if re_m:
                predicted_path = Path(str(virtual_env_path).format(*re_m.groups()))
                if predicted_path.exists():
                    p_ver = re_m.groups()

            virtual_env = str(virtual_env_path).format(*p_ver)

        if self.kernel_tab.app.config.warn_venv:
            log.warning("Attempting to work in virtualenv %r.", virtual_env)
            log.warning(
                "If you encounter problems, please install euporie inside the virtual "
                "environment, or use a Jupyter kernel."
            )
        import site

        sys.path.insert(0, virtual_env)
        site.addsitedir(virtual_env)

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
        self.init_venv()

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
            Terminal256Formatter(style=self.kernel_tab.app.config.syntax_theme),
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

    async def _handle_magic(self, source: str, callbacks: MsgCallbacks) -> bool:
        """Detect and handle special %magics.

        Args:
            source: The source code to check for magic commands
            callbacks: Message callbacks for output

        Returns:
            True if a magic command was handled, False otherwise
        """
        # Store callbacks in thread local storage
        self._thread_local.callbacks = callbacks

        with self.hook_manager:
            stripped_src = source.strip()
            if not stripped_src.startswith("%"):
                return False
            # Warn if there are extra lines
            lines = stripped_src.splitlines()
            if len(lines) > 1 and not stripped_src.startswith("%%"):
                print(  # noqa: T201
                    "Warning: Magics cannot be mixed with Python code in the same cell",
                    file=sys.stderr,
                )
                return True

            parts = source.strip().split()
            magic_name = parts[0].removeprefix("%")
            args = parts[1:]

            if magic_name in self.magics:
                handler = self.magics[magic_name]
                maybe_awaitable = handler(args, callbacks, self)
                if hasattr(maybe_awaitable, "__await__"):
                    await maybe_awaitable
                return True
            return False

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

        # Handle magics before normal execution
        handled = await self._handle_magic(source, callbacks)

        if not handled:
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

            # Execute the code
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
            ("_repr_json_", "application/json"),
        ]:
            if hasattr(obj, method) and (output := getattr(obj, method)()) is not None:
                if isinstance(output, tuple):
                    output, metadata = output
                data[mime] = output
        if not data:
            data = {"text/plain": repr(obj)}

    return data, metadata


class BaseHook(AbstractContextManager):
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

    def __init__(self, kernel: LocalPythonKernel) -> None:
        """Initialize the display hook.

        Args:
            kernel: The kernel instance to hook
        """
        super().__init__(kernel)
        self._prev: Callable[[object], Any]

    def __enter__(self) -> DisplayHook:
        """Replace sys.displayhook with this hook."""
        self._prev = sys.displayhook
        sys.displayhook = self
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Restore previous displayhook."""
        sys.displayhook = self._prev

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

    def __init__(self, kernel: LocalPythonKernel) -> None:
        """Initialize the display global.

        Args:
            kernel: The kernel instance to hook
        """
        super().__init__(kernel)

    def __enter__(self) -> DisplayGlobal:
        """Add display() to kernel locals."""
        self._kernel.locals["display"] = self
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Remove display() from kernel locals."""
        self._kernel.locals.pop("display", None)

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
            if raw:
                data = obj
                obj_metadata: dict[str, Any] = {}
            else:
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
        self._prev: object = None
        update_wrapper(self, input)

    def __enter__(self) -> InputBuiltin:
        """Replace input or getpass with this hook."""
        if self._is_password:
            self._prev = getpass.getpass
            getpass.getpass = self  # type: ignore[assignment]
        else:
            self._prev = self._kernel.locals.get("input")
            self._kernel.locals["input"] = self
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Restore previous input or getpass."""
        if self._is_password:
            getpass.getpass = self._prev  # type: ignore[assignment]
        else:
            if self._prev is not None:
                self._kernel.locals["input"] = self._prev
            else:
                self._kernel.locals.pop("input", None)

    def __call__(
        self,
        prompt: str = "",
        stream: TextIO | None = None,
        echo_char: str | None = None,
    ) -> str:
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
        self._prev: object = None

    @property
    def buffer(self) -> str:
        """Get the thread-local buffer for this stream."""
        if not hasattr(self._thread_local, "buffer"):
            self._thread_local.buffer = ""
        return self._thread_local.buffer

    @buffer.setter
    def buffer(self, value: str) -> None:
        self._thread_local.buffer = value

    def __enter__(self) -> StreamWrapper:
        """Replace sys stream with this hook."""
        self._prev = getattr(sys, self.name)
        setattr(sys, self.name, self)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Restore previous stream and flush any buffered content."""
        self.flush()
        setattr(sys, self.name, self._prev)

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

    def isatty(self) -> bool:
        """Make users of this stream believe it is as TTY."""
        return True


class MatplotlibHook(BaseHook):
    """Hook for matplotlib figure display during code execution."""

    def __init__(self, kernel: LocalPythonKernel) -> None:
        """Initialize the matplotlib hook.

        Args:
            kernel: The kernel instance to hook
        """
        super().__init__(kernel)
        self._configured = False

    def __enter__(self) -> MatplotlibHook:
        """Configure matplotlib for inline display."""
        self.configure_inline_backend()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Display any active matplotlib figures."""
        self.display_figures()

    def configure_inline_backend(self) -> None:
        """Configure matplotlib for inline figure display.

        This monkey-patches the matplotlib Figure class to add a _repr_png_
        method, enabling figures to be automatically displayed as
        cell output in Euporie's notebook interface.
        """
        if self._configured:
            return

        try:
            import matplotlib
        except ImportError:
            log.debug("matplotlib not available - skipping inline configuration")
            return
        except Exception:
            log.exception("Failed to configure matplotlib for inline display")
            return

        try:
            import io

            matplotlib.use("Agg")  # Use non-interactive backend
            import matplotlib.figure as mfig

            def _repr_png_(fig: Any) -> str:
                """Generate base64 PNG representation of figure."""
                buf = io.BytesIO()
                fig.savefig(buf, format="png", bbox_inches="tight")
                data = buf.getvalue()
                return b64encode(data).decode()

            mfig.Figure._repr_png_ = _repr_png_
            self._configured = True
        except Exception:
            log.exception("Failed to configure matplotlib backend")

    def display_figures(self) -> None:
        """Display any active matplotlib figures as cell output.

        This is called when exiting the hook manager to automatically render
        figures that were created during code execution.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            pass
        except Exception as e:
            log.debug("Error displaying matplotlib figures: %s", e)
        else:
            if (callbacks := self.callbacks) and callable(
                cb := callbacks.get("add_output")
            ):
                for num in plt.get_fignums():
                    fig = plt.figure(num)
                    from euporie.core.kernel.local import get_display_data

                    data, metadata = get_display_data(fig)
                    cb(
                        {
                            "output_type": "display_data",
                            "data": data,
                            "metadata": metadata,
                        },
                        True,
                    )
                    plt.close(fig)


class HookManager:
    """Context manager for hooking stdout/stderr/displayhook.

    Manages nested entry/exit of multiple hooks with centralized depth tracking.
    Hooks are only actually patched on first entry and unpatched on final exit.
    """

    def __init__(self, kernel: LocalPythonKernel) -> None:
        """Initialize the hook manager.

        Args:
            kernel: The kernel instance to hook
        """
        self._kernel = kernel
        self._depth = 0
        self._stack: ExitStack | None = None
        # Create hook instances
        self._hooks = [
            StreamWrapper("stdout", kernel),
            StreamWrapper("stderr", kernel),
            DisplayHook(kernel),
            DisplayGlobal(kernel),
            InputBuiltin(kernel, is_password=False),
            InputBuiltin(kernel, is_password=True),
            MatplotlibHook(kernel),
        ]

    def __enter__(self) -> HookManager:
        """Enter the hook context, patching on first entry."""
        if self._depth == 0:
            self._stack = ExitStack()
            for hook in self._hooks:
                self._stack.enter_context(hook)
        self._depth += 1
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the hook context, unpatching on final exit."""
        self._depth -= 1
        if self._depth == 0 and self._stack is not None:
            self._stack.close()
            self._stack = None


# Magic command implementations


@LocalPythonKernel.register_magic("pip")
async def magic_pip(
    args: list[str], callbacks: MsgCallbacks, kernel: LocalPythonKernel
) -> None:
    """Run pip commands locally, using micropip if available (e.g., in Pyodide).

    Args:
        args: Command-line arguments to pass to pip
        callbacks: Message callbacks for output
        kernel: The kernel instance
    """
    # Try using micropip (for Pyodide environments)
    try:
        import micropip  # type: ignore[import-not-found]
    except ImportError:
        pass
    else:
        if not args:
            return
        cmd = args[0]
        func = getattr(micropip, cmd, None)
        if not callable(func):
            print(f"Unknown micropip command: {cmd}", file=sys.stderr)  # noqa: T201
            return

        result = func(*args[1:]) if cmd != "install" else func(args[1:])
        if hasattr(result, "__await__"):
            await result
        else:
            # Show result if it returns something
            if result is not None:
                print(str(result))  # noqa: T201
        return

    # Try importing pip & bootstrap if missing
    import runpy

    old_argv = sys.argv
    try:
        try:
            import pip as pip
        except ImportError:
            # Install pip using ensurepip if missing
            sys.argv = []
            try:
                runpy.run_module("ensurepip", run_name="__main__")
            except SystemExit:
                pass
        sys.argv = ["pip", *args]
        try:
            runpy.run_module("pip", run_name="__main__")
        except SystemExit:
            # pip exits with sys.exit(), which is expected
            pass
    finally:
        sys.argv = old_argv
