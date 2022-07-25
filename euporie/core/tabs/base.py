"""Contains tab base classes."""

from __future__ import annotations

import logging
from abc import ABCMeta
from typing import TYPE_CHECKING

from prompt_toolkit.filters import buffer_has_focus
from prompt_toolkit.history import ThreadedHistory
from prompt_toolkit.layout.containers import Window

from euporie.core.app import get_app
from euporie.core.comm.registry import open_comm
from euporie.core.commands import add_cmd
from euporie.core.completion import KernelCompleter
from euporie.core.filters import display_has_focus, kernel_tab_has_focus
from euporie.core.history import KernelHistory
from euporie.core.kernel import Kernel, MsgCallbacks
from euporie.core.suggest import HistoryAutoSuggest

if TYPE_CHECKING:
    from os import PathLike
    from typing import Any, Callable, Dict, Optional, Sequence

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

    def __init__(
        self, app: "Optional[BaseApp]" = None, path: "Optional[PathLike]" = None
    ):
        """Called when the tab is created."""
        self.app: "BaseApp" = app or get_app()
        self.app.container_statuses[self] = self.statusbar_fields
        self.container = Window()

    def statusbar_fields(
        self,
    ) -> "tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]":
        """Returns a list of statusbar field values shown then this tab is active."""
        return ([], [])

    @property
    def title(self) -> "str":
        """Return the tab title."""
        return ""

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
    kernel_name: "str"
    kernel_display_name: "str"
    kernel_language: "str"
    kernel_lang_file_ext: "str"
    metadata: "Dict[str, Any]"

    default_callbacks: "MsgCallbacks"
    allow_stdin: "bool"

    def __init__(
        self,
        app: "Optional[BaseApp]" = None,
        path: "Optional[PathLike]" = None,
        use_kernel_history: "bool" = None,
    ) -> "None":
        """Create a new instance of a tab with a kernel."""
        super().__init__(app, path)

        self.kernel: "Kernel" = Kernel(
            kernel_tab=self,
            allow_stdin=self.allow_stdin,
            default_callbacks=self.default_callbacks,
        )
        self.comms: "Dict[str, Comm]" = {}  # The client-side comm states
        self.completer = KernelCompleter(self.kernel)
        self.history = KernelHistory(self.kernel) if use_kernel_history else None
        self.suggester = HistoryAutoSuggest(self.history)

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

    @property
    def kernel_name(self) -> "str":
        """Return the name of the kernel defined in the notebook JSON."""
        return self.metadata.get("kernelspec", {}).get("name")

    @property
    def language(self) -> "str":
        """Return the name of the kernel defined in the notebook JSON."""
        return self.metadata.get("kernelspec", {}).get("language")

    @kernel_name.setter
    def kernel_name(self, name: "str") -> "None":
        """Set the kernel name."""
        self.metadata.setdefault("kernelspec", {})["name"] = name

    @property
    def kernel_display_name(self) -> "str":
        """Return the display name of the kernel defined in the notebook JSON."""
        return self.metadata.get("kernelspec", {}).get("display_name", "")

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
            self.kernel.change(list(kernel_specs)[0], self.metadata)
            return

        self.app.dialogs["change-kernel"].show(
            tab=self, message=msg, kernel_specs=kernel_specs
        )

    def comm_open(self, content: "Dict", buffers: "Sequence[bytes]") -> "None":
        """Register a new kernel Comm object in the notebook."""
        comm_id = str(content.get("comm_id"))
        self.comms[comm_id] = open_comm(
            comm_container=self, content=content, buffers=buffers
        )

    def comm_msg(self, content: "Dict", buffers: "Sequence[bytes]") -> "None":
        """Respond to a Comm message from the kernel."""
        comm_id = str(content.get("comm_id"))
        if comm := self.comms.get(comm_id):
            comm.process_data(content.get("data", {}), buffers)

    def comm_close(self, content: "Dict", buffers: "Sequence[bytes]") -> "None":
        """Close a notebook Comm."""
        comm_id = content.get("comm_id")
        if comm_id in self.comms:
            del self.comms[comm_id]

    # ################################### Commands ####################################

    @add_cmd(
        filter=kernel_tab_has_focus,
    )
    @staticmethod
    def _change_kernel() -> "None":
        """Change the notebook's kernel."""
        if isinstance(kt := get_app().tab, KernelTab):
            kt.change_kernel()
