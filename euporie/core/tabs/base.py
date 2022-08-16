"""Contains tab base classes."""

from __future__ import annotations

import logging
from abc import ABCMeta
from collections import deque
from typing import TYPE_CHECKING

from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.layout.containers import Window

from euporie.core.app import get_app
from euporie.core.comm.registry import open_comm
from euporie.core.commands import add_cmd
from euporie.core.completion import KernelCompleter
from euporie.core.config import add_setting
from euporie.core.filters import kernel_tab_has_focus
from euporie.core.history import KernelHistory
from euporie.core.kernel import Kernel, MsgCallbacks
from euporie.core.suggest import HistoryAutoSuggest

if TYPE_CHECKING:
    from typing import Any, Callable, Deque, Optional, Sequence

    from prompt_toolkit.auto_suggest import AutoSuggest
    from prompt_toolkit.completion.base import Completer
    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.history import History
    from prompt_toolkit.layout.containers import AnyContainer
    from upath import UPath

    from euporie.core.app import BaseApp
    from euporie.core.comm.base import Comm

log = logging.getLogger(__name__)


class Tab(metaclass=ABCMeta):
    """Base class for interface tabs."""

    container: "AnyContainer"

    def __init__(self, app: "BaseApp", path: "Optional[UPath]" = None):
        """Called when the tab is created."""
        self.app = app
        self.path = path
        self.app.container_statuses[self] = self.statusbar_fields
        self.container = Window()
        self.kernel_queue: "Deque[Callable]" = deque()

    def statusbar_fields(
        self,
    ) -> "tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]":
        """Returns a list of statusbar field values shown then this tab is active."""
        return ([], [])

    @property
    def title(self) -> "str":
        """Return the tab title."""
        return ""

    def reset(self) -> "None":
        """Reset the state of the tab."""

    def close(self, cb: "Optional[Callable]" = None) -> "None":
        """Function to close a tab with a callback.

        Args:
            cb: A function to call after the tab is closed.

        """
        if self in self.app.container_statuses:
            del self.app.container_statuses[self]
        if callable(cb):
            cb()

    def focus(self) -> "None":
        """Focuses the tab (or make it visible)."""
        self.app.focus_tab(self)

    def save(self, path: "UPath" = None) -> "None":
        """Save the current notebook."""
        raise NotImplementedError

    def __pt_container__(self) -> "AnyContainer":
        """Return the main container object."""
        return self.container


class KernelTab(Tab, metaclass=ABCMeta):
    """A Tab which connects to a kernel."""

    kernel: "Kernel"
    kernel_language: "str"
    _metadata: "dict[str, Any]"

    default_callbacks: "MsgCallbacks"
    allow_stdin: "bool"

    def __init__(
        self,
        app: "BaseApp",
        path: "Optional[UPath]" = None,
        kernel: "Optional[Kernel]" = None,
        comms: "Optional[dict[str, Comm]]" = None,
        use_kernel_history: "bool" = False,
    ) -> "None":
        """Create a new instance of a tab with a kernel."""
        super().__init__(app, path)

        if kernel:
            self.kernel = kernel
            self.kernel.default_callbacks = self.default_callbacks
        else:
            self.kernel = Kernel(
                kernel_tab=self,
                allow_stdin=self.allow_stdin,
                default_callbacks=self.default_callbacks,
            )
        self.comms: "dict[str, Comm]" = comms or {}  # The client-side comm states
        self.completer: "Completer" = KernelCompleter(self.kernel)
        self.use_kernel_history = use_kernel_history
        self.history: "History" = (
            KernelHistory(self.kernel) if use_kernel_history else InMemoryHistory()
        )
        self.suggester: "AutoSuggest" = HistoryAutoSuggest(self.history)

    def interrupt_kernel(self) -> "None":
        """Interrupt the current `Notebook`'s kernel."""
        self.kernel.interrupt()

    def restart_kernel(self) -> "None":
        """Restarts the current `Notebook`'s kernel."""
        if confirm := self.app.dialogs.get("confirm"):
            confirm.show(
                message="Are you sure you want to restart the kernel?",
                cb=self.kernel.restart,
            )
        else:
            self.kernel.restart()

    def kernel_started(self, result: "Optional[dict[str, Any]]" = None) -> "None":
        """Tasks to run when the kernel has started."""
        # Check kernel has not failed
        if not self.kernel_name or self.kernel.missing or self.kernel.status == "error":
            return

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

    async def load_history(self) -> "None":
        """Load kernel history."""
        try:
            await self.history.load().__anext__()
        except StopAsyncIteration:
            pass

    @property
    def metadata(self) -> "dict[str, Any]":
        """Return a dictionary to hold notebook / kernel metadata."""
        return self._metadata

    @property
    def kernel_name(self) -> "str":
        """Return the name of the kernel defined in the notebook JSON."""
        return self.metadata.get("kernelspec", {}).get(
            "name", self.app.config.kernel_name
        )

    @kernel_name.setter
    def kernel_name(self, value: "str") -> "None":
        """Return the name of the kernel defined in the notebook JSON."""
        self.metadata.setdefault("kernelspec", {})["name"] = value

    @property
    def language(self) -> "str":
        """Return the name of the kernel defined in the notebook JSON."""
        return self.metadata.get("kernelspec", {}).get("language")

    @property
    def kernel_display_name(self) -> "str":
        """Return the display name of the kernel defined in the notebook JSON."""
        return self.metadata.get("kernelspec", {}).get("display_name", self.kernel_name)

    @property
    def kernel_lang_file_ext(self) -> "str":
        """Return the display name of the kernel defined in the notebook JSON."""
        return self.metadata.get("language_info", {}).get("file_extension", ".py")

    def set_kernel_info(self, info: "dict") -> "None":
        """Handle kernel info requests."""
        self.metadata["language_info"] = info.get("language_info", {})

    def change_kernel(
        self, msg: "Optional[str]" = None, startup: "bool" = False
    ) -> None:
        """Prompt the user to select a new kernel."""
        kernel_specs = self.kernel.specs

        # Warn the user if no kernels are installed
        if not kernel_specs:
            if startup and "no-kernels" not in self.app.dialogs:
                self.app.dialogs["no-kernels"].show()
            return

        # Automatically select the only kernel if there is only one
        if startup and len(kernel_specs) == 1:
            self.kernel.change(list(kernel_specs)[0])
            return

        self.app.dialogs["change-kernel"].show(
            tab=self, message=msg, kernel_specs=kernel_specs
        )

    def comm_open(self, content: "dict", buffers: "Sequence[bytes]") -> "None":
        """Register a new kernel Comm object in the notebook."""
        comm_id = str(content.get("comm_id"))
        self.comms[comm_id] = open_comm(
            comm_container=self, content=content, buffers=buffers
        )

    def comm_msg(self, content: "dict", buffers: "Sequence[bytes]") -> "None":
        """Respond to a Comm message from the kernel."""
        comm_id = str(content.get("comm_id"))
        if comm := self.comms.get(comm_id):
            comm.process_data(content.get("data", {}), buffers)

    def comm_close(self, content: "dict", buffers: "Sequence[bytes]") -> "None":
        """Close a notebook Comm."""
        comm_id = content.get("comm_id")
        if comm_id in self.comms:
            del self.comms[comm_id]

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(
        filter=kernel_tab_has_focus,
    )
    def _change_kernel() -> "None":
        """Change the notebook's kernel."""
        if isinstance(kt := get_app().tab, KernelTab):
            kt.change_kernel()

    # ################################### Settings ####################################

    add_setting(
        name="kernel_name",
        flags=["--kernel-name"],
        type_=str,
        help_="The name of the kernel to start by default",
        default="python3",
        description="""
            The name of the kernel selected automatically by the console app or in new
            notebooks. If set to an empty string, the user will be asked which kernel
            to launch.
        """,
    )
