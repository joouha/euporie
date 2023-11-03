"""Contain tab base classes."""

from __future__ import annotations

import contextlib
import logging
from abc import ABCMeta
from collections import deque
from functools import partial
from typing import TYPE_CHECKING, ClassVar

from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.layout.containers import Window, WindowAlign
from prompt_toolkit.layout.controls import FormattedTextControl

from euporie.core.comm.registry import open_comm
from euporie.core.commands import add_cmd
from euporie.core.completion import KernelCompleter
from euporie.core.config import add_setting
from euporie.core.current import get_app
from euporie.core.filters import kernel_tab_has_focus, tab_has_focus
from euporie.core.history import KernelHistory
from euporie.core.kernel import Kernel, MsgCallbacks
from euporie.core.key_binding.registry import (
    register_bindings,
)
from euporie.core.suggest import HistoryAutoSuggest
from euporie.core.utils import run_in_thread_with_context

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, Callable, Sequence

    from prompt_toolkit.auto_suggest import AutoSuggest
    from prompt_toolkit.completion.base import Completer
    from prompt_toolkit.history import History
    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.app import BaseApp
    from euporie.core.comm.base import Comm
    from euporie.core.widgets.status_bar import StatusBarFields

log = logging.getLogger(__name__)


class Tab(metaclass=ABCMeta):
    """Base class for interface tabs."""

    _registry: ClassVar[set[type[Tab]]] = set()
    name: str | None = None
    weight: int = 0
    mime_types: ClassVar[set[str]] = set()
    file_extensions: ClassVar[set[str]] = set()

    container: AnyContainer

    def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
        """Compile a registry of named tabs."""
        super().__init_subclass__(**kwargs)
        if cls.name:
            Tab._registry.add(cls)

    def __init__(self, app: BaseApp, path: Path | None = None) -> None:
        """Call when the tab is created."""
        self.app = app
        self.path = path
        self.container = Window(
            FormattedTextControl([("fg:#888888", "\nLoading…")], focusable=True),
            align=WindowAlign.CENTER,
        )

        self.dirty = False
        self.saving = False

    @property
    def title(self) -> str:
        """Return the tab title."""
        return ""

    def reset(self) -> "None":  # noqa B027
        """Reet the state of the tab."""

    def close(self, cb: Callable | None = None) -> None:
        """Close a tab with a callback.

        Args:
            cb: A function to call after the tab is closed.

        """
        # Run callback
        if callable(cb):
            cb()

    def focus(self) -> None:
        """Focus the tab (or make it visible)."""
        self.app.focus_tab(self)

    def _save(self, path: Path | None = None, cb: Callable | None = None) -> None:
        """Perform the file save in a background thread."""
        run_in_thread_with_context(self.save, path, cb)

    def save(self, path: Path | None = None, cb: Callable | None = None) -> None:
        """Save the current notebook."""
        raise NotImplementedError

    def __pt_status__(self) -> StatusBarFields | None:
        """Return a list of statusbar field values shown then this tab is active."""
        return ([], [])

    def __pt_container__(self) -> AnyContainer:
        """Return the main container object."""
        return self.container

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(filter=tab_has_focus, title="Refresh the current tab")
    def _refresh_tab() -> None:
        """Reload the tab contents and reset the tab."""
        if (tab := get_app().tab) is not None:
            tab.reset()

    # Depreciated v2.5.0
    @staticmethod
    @add_cmd(filter=tab_has_focus, title="Reset the current tab")
    def _reset_tab() -> None:
        log.warning(
            "The `reset-tab` command was been renamed to `refresh-tab` in v2.5.0,"
            " and will be removed in a future version"
        )
        Tab._refresh_tab()

    @staticmethod
    @add_cmd(filter=tab_has_focus)
    def _save_file() -> None:
        """Save the current file."""
        if (tab := get_app().tab) is not None:
            with contextlib.suppress(NotImplementedError):
                tab._save()

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.tabs.base.Tab": {
                "save-file": "c-s",
                "refresh-tab": "f5",
            }
        }
    )


class KernelTab(Tab, metaclass=ABCMeta):
    """A Tab which connects to a kernel."""

    kernel: Kernel
    kernel_language: str
    _metadata: dict[str, Any]
    bg_init = True

    default_callbacks: MsgCallbacks
    allow_stdin: bool

    def __init__(
        self,
        app: BaseApp,
        path: Path | None = None,
        kernel: Kernel | None = None,
        comms: dict[str, Comm] | None = None,
        use_kernel_history: bool = False,
        connection_file: Path | None = None,
    ) -> None:
        """Create a new instance of a tab with a kernel."""
        # Init tab
        super().__init__(app, path)

        if self.bg_init:
            # Load kernel in a background thread
            run_in_thread_with_context(
                partial(
                    self.init_kernel, kernel, comms, use_kernel_history, connection_file
                )
            )
        else:
            self.init_kernel(kernel, comms, use_kernel_history, connection_file)

    def pre_init_kernel(self) -> None:
        """Run stuff before the kernel is loaded."""

    def post_init_kernel(self) -> None:
        """Run stuff after the kernel is loaded."""

    def init_kernel(
        self,
        kernel: Kernel | None = None,
        comms: dict[str, Comm] | None = None,
        use_kernel_history: bool = False,
        connection_file: Path | None = None,
    ) -> None:
        """Set up the tab's kernel and related components."""
        self.pre_init_kernel()

        self.kernel_queue: deque[Callable] = deque()

        if kernel:
            self.kernel = kernel
            self.kernel.default_callbacks = self.default_callbacks
        else:
            self.kernel = Kernel(
                kernel_tab=self,
                allow_stdin=self.allow_stdin,
                default_callbacks=self.default_callbacks,
                connection_file=connection_file,
            )
        self.comms: dict[str, Comm] = comms or {}  # The client-side comm states
        self.completer: Completer = KernelCompleter(self.kernel)
        self.use_kernel_history = use_kernel_history
        self.history: History = (
            KernelHistory(self.kernel) if use_kernel_history else InMemoryHistory()
        )
        self.suggester: AutoSuggest = HistoryAutoSuggest(self.history)

        self.post_init_kernel()

    def close(self, cb: Callable | None = None) -> None:
        """Shut down kernel when tab is closed."""
        if hasattr(self, "kernel"):
            self.kernel.shutdown()
        super().close(cb)

    def interrupt_kernel(self) -> None:
        """Interrupt the current `Notebook`'s kernel."""
        self.kernel.interrupt()

    def restart_kernel(self, cb: Callable | None = None) -> None:
        """Restart the current `Notebook`'s kernel."""

        def _cb(result: dict[str, Any]) -> None:
            if callable(cb):
                cb()

        if confirm := self.app.dialogs.get("confirm"):
            confirm.show(
                message="Are you sure you want to restart the kernel?",
                cb=partial(self.kernel.restart, cb=_cb),
            )
        else:
            self.kernel.restart(cb=_cb)

    def kernel_started(self, result: dict[str, Any] | None = None) -> None:
        """Task to run when the kernel has started."""
        # Check kernel has not failed
        if not self.kernel_name or self.kernel.missing:
            if not self.kernel_name:
                msg = "No kernel selected"
            else:
                msg = f"Kernel '{self.kernel_display_name}' not installed"
            self.change_kernel(
                msg=msg,
                startup=True,
            )

        elif self.kernel.status == "error":
            self.report_kernel_error(self.kernel.error)

        else:
            # Wait for an idle kernel
            if self.kernel.status != "idle":
                self.kernel.wait_for_status("idle")

            # Load widget comm info
            # self.kernel.comm_info(target_name="jupyter.widget")

            # Load kernel info
            self.kernel.info(set_kernel_info=self.set_kernel_info)

            # Load kernel history
            if self.use_kernel_history:
                self.app.create_background_task(self.load_history())

            # Run queued kernel tasks when the kernel is idle
            log.debug("Running %d kernel tasks", len(self.kernel_queue))
            while self.kernel_queue:
                self.kernel_queue.popleft()()

        self.app.invalidate()

    def report_kernel_error(self, error: Exception | None) -> None:
        """Report a kernel error to the user."""
        log.debug("Kernel error", exc_info=error)

    async def load_history(self) -> None:
        """Load kernel history."""
        with contextlib.suppress(StopAsyncIteration):
            await self.history.load().__anext__()

    @property
    def metadata(self) -> dict[str, Any]:
        """Return a dictionary to hold notebook / kernel metadata."""
        return self._metadata

    @property
    def kernel_name(self) -> str:
        """Return the name of the kernel defined in the notebook JSON."""
        return self.metadata.get("kernelspec", {}).get(
            "name", self.app.config.kernel_name
        )

    @kernel_name.setter
    def kernel_name(self, value: str) -> None:
        """Return the name of the kernel defined in the notebook JSON."""
        self.metadata.setdefault("kernelspec", {})["name"] = value

    @property
    def language(self) -> str:
        """Return the name of the kernel defined in the notebook JSON."""
        return self.metadata.get("kernelspec", {}).get("language")

    @property
    def kernel_display_name(self) -> str:
        """Return the display name of the kernel defined in the notebook JSON."""
        return self.metadata.get("kernelspec", {}).get("display_name", self.kernel_name)

    @property
    def kernel_lang_file_ext(self) -> str:
        """Return the display name of the kernel defined in the notebook JSON."""
        return self.metadata.get("language_info", {}).get("file_extension", ".py")

    def set_kernel_info(self, info: dict) -> None:
        """Handle kernel info requests."""
        self.metadata["language_info"] = info.get("language_info", {})

    def change_kernel(self, msg: str | None = None, startup: bool = False) -> None:
        """Prompt the user to select a new kernel."""
        kernel_specs = self.kernel.specs

        # Warn the user if no kernels are installed
        if not kernel_specs:
            if startup and "no-kernels" in self.app.dialogs:
                self.app.dialogs["no-kernels"].show()
            return

        # Automatically select the only kernel if there is only one
        if startup and len(kernel_specs) == 1:
            self.kernel.change(next(iter(kernel_specs)))
            return

        self.app.dialogs["change-kernel"].show(
            tab=self, message=msg, kernel_specs=kernel_specs
        )

    def comm_open(self, content: dict, buffers: Sequence[bytes]) -> None:
        """Register a new kernel Comm object in the notebook."""
        comm_id = str(content.get("comm_id"))
        self.comms[comm_id] = open_comm(
            comm_container=self, content=content, buffers=buffers
        )

    def comm_msg(self, content: dict, buffers: Sequence[bytes]) -> None:
        """Respond to a Comm message from the kernel."""
        comm_id = str(content.get("comm_id"))
        if comm := self.comms.get(comm_id):
            comm.process_data(content.get("data", {}), buffers)

    def comm_close(self, content: dict, buffers: Sequence[bytes]) -> None:
        """Close a notebook Comm."""
        comm_id = content.get("comm_id")
        if comm_id in self.comms:
            del self.comms[comm_id]

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(filter=kernel_tab_has_focus)
    def _change_kernel() -> None:
        """Change the notebook's kernel."""
        if isinstance(kt := get_app().tab, KernelTab):
            kt.change_kernel()

    # ################################### Settings ####################################

    add_setting(
        name="kernel_name",
        flags=["--kernel-name", "--kernel"],
        type_=str,
        help_="The name of the kernel to start by default",
        default="python3",
        description="""
            The name of the kernel selected automatically by the console app or in new
            notebooks. If set to an empty string, the user will be asked which kernel
            to launch.
        """,
    )

    add_setting(
        name="record_cell_timing",
        title="cell timing recording",
        flags=["--record-cell-timing"],
        type_=bool,
        help_="Should timing data be recorded in cell metadata.",
        default=False,
        schema={
            "type": "boolean",
        },
        description="""
            When set, execution timing data will be recorded in cell metadata.
        """,
    )
