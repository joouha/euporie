"""Contain kernel tab base class."""

from __future__ import annotations

import asyncio
import logging
from abc import ABCMeta
from collections import deque
from functools import lru_cache, partial
from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

from prompt_toolkit.auto_suggest import DummyAutoSuggest, DynamicAutoSuggest
from prompt_toolkit.completion.base import (
    DynamicCompleter,
    _MergedCompleter,
)
from prompt_toolkit.history import DummyHistory, InMemoryHistory

from euporie.core.app.current import get_app
from euporie.core.comm.registry import open_comm
from euporie.core.commands import add_cmd
from euporie.core.completion import DeduplicateCompleter, KernelCompleter, LspCompleter
from euporie.core.diagnostics import Report
from euporie.core.filters import kernel_tab_has_focus
from euporie.core.format import LspFormatter
from euporie.core.history import KernelHistory
from euporie.core.inspection import (
    FirstInspector,
    KernelInspector,
    LspInspector,
)
from euporie.core.kernel import list_kernels
from euporie.core.kernel.base import NoKernel
from euporie.core.tabs.base import Tab

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path
    from typing import Any

    from prompt_toolkit.auto_suggest import AutoSuggest
    from prompt_toolkit.completion.base import Completer
    from prompt_toolkit.history import History

    from euporie.core.app.app import BaseApp
    from euporie.core.comm.base import Comm
    from euporie.core.format import Formatter
    from euporie.core.inspection import Inspector
    from euporie.core.kernel.base import BaseKernel, KernelFactory, MsgCallbacks
    from euporie.core.lsp import LspClient
    from euporie.core.widgets.inputs import KernelInput

log = logging.getLogger(__name__)


@lru_cache
def autosuggest_factory(kind: str, history: History) -> AutoSuggest:
    """Generate autosuggesters."""
    if kind == "smart":
        from euporie.core.suggest import SmartHistoryAutoSuggest

        return SmartHistoryAutoSuggest(history)
    elif kind == "simple":
        from euporie.core.suggest import SimpleHistoryAutoSuggest

        return SimpleHistoryAutoSuggest(history)
    else:
        from prompt_toolkit.auto_suggest import DummyAutoSuggest

        return DummyAutoSuggest()


class KernelTab(Tab, metaclass=ABCMeta):
    """A Tab which connects to a kernel."""

    kernel_language: str
    _metadata: dict[str, Any]
    bg_init = False

    default_callbacks: MsgCallbacks
    allow_stdin: bool

    def __init__(
        self,
        app: BaseApp,
        path: Path | None = None,
        kernel: BaseKernel | None = None,
        comms: dict[str, Comm] | None = None,
        use_kernel_history: bool = False,
        connection_file: Path | None = None,
    ) -> None:
        """Create a new instance of a tab with a kernel."""
        # Init tab
        super().__init__(app, path)

        self.kernel: BaseKernel = NoKernel(self)
        self.lsps: list[LspClient] = []
        self.history: History = DummyHistory()
        self.inspectors: list[Inspector] = []
        self.inspector = FirstInspector(lambda: self.inspectors)
        self.suggester: AutoSuggest = DummyAutoSuggest()
        self.completers: list[Completer] = []
        self.completer = DeduplicateCompleter(
            DynamicCompleter(lambda: _MergedCompleter(self.completers))
        )
        self.formatters: list[Formatter] = self.app.formatters
        self.reports: WeakKeyDictionary[LspClient, Report] = WeakKeyDictionary()

        # The client-side comm states
        self.comms: dict[str, Comm] = {}
        # The current kernel input
        self._current_input: KernelInput | None = None

        if self.bg_init:
            # Load kernel in a background thread
            app.create_background_task(
                asyncio.to_thread(
                    self.init_kernel, kernel, comms, use_kernel_history, connection_file
                )
            )
        else:
            self.init_kernel(kernel, comms, use_kernel_history, connection_file)

    async def load_lsps(self) -> None:
        """Load the LSP clients."""
        path = self.path

        # Load list of LSP clients for the tab's language
        self.lsps.extend(self.app.get_language_lsps(self.language))

        # Wait for all lsps to be initialized, and setup hooks as they become ready
        async def _await_load(lsp: LspClient) -> LspClient:
            await lsp.initialized.wait()
            return lsp

        for ready in asyncio.as_completed([_await_load(lsp) for lsp in self.lsps]):
            lsp = await ready
            # Apply open, save, and close hooks to the tab
            change_handler = partial(lambda lsp, tab: self.lsp_change_handler(lsp), lsp)
            close_handler = partial(lambda lsp, tab: self.lsp_close_handler(lsp), lsp)
            before_save_handler = partial(
                lambda lsp, tab: self.lsp_before_save_handler(lsp), lsp
            )
            after_save_handler = partial(
                lambda lsp, tab: self.lsp_after_save_handler(lsp), lsp
            )

            self.on_close += close_handler
            self.on_change += change_handler
            self.before_save += before_save_handler
            self.after_save += after_save_handler

            # Listen for LSP diagnostics
            lsp.on_diagnostics += self.lsp_update_diagnostics

            # Add completer
            completer = LspCompleter(lsp=lsp, path=path)
            self.completers.append(completer)

            # Add inspector
            inspector = LspInspector(lsp, path)
            self.inspectors.append(inspector)

            # Add formatter
            formatter = LspFormatter(lsp, path)
            self.formatters.append(formatter)

            # Remove hooks if the LSP exits
            def lsp_unload(lsp: LspClient) -> None:
                self.on_change -= change_handler  # noqa: B023
                self.before_save -= before_save_handler  # noqa: B023
                self.after_save -= after_save_handler  # noqa: B023
                self.on_close -= close_handler  # noqa: B023
                if completer in self.completers:  # noqa: B023
                    self.completers.remove(completer)  # noqa: B023
                if inspector in self.completers:  # noqa: B023
                    self.inspectors.remove(inspector)  # noqa: B023
                if formatter in self.completers:  # noqa: B023
                    self.formatters.remove(formatter)  # noqa: B023
                if completer in self.completers:  # noqa: B023
                    self.completers.remove(completer)  # noqa: B023
                if inspector in self.inspectors:  # noqa: B023
                    self.inspectors.remove(inspector)  # noqa: B023
                if formatter in self.formatters:  # noqa: B023
                    self.formatters.remove(formatter)  # noqa: B023

            lsp.on_exit += lsp_unload

            # Remove the lsp exit handler if this tab closes
            self.on_close += lambda tab: (
                (lsp.on_exit.__isub__(lsp_unload) and None) or None  # noqa: B023
            )  # Magical typing

            # Tell the LSP we have an open file
            self.lsp_open_handler(lsp)

    def pre_init_kernel(self) -> None:
        """Run stuff before the kernel is loaded."""

    def post_init_kernel(self) -> None:
        """Run stuff after the kernel is loaded."""
        if not isinstance(self.kernel, NoKernel):
            self.metadata["kernelspec"] = self.kernel.spec

    def init_kernel(
        self,
        kernel: BaseKernel | None = None,
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
            from euporie.core.kernel import list_kernels

            kernel_name = self.kernel_name or self.app.config.kernel_name
            for info in list_kernels():
                if info.name == kernel_name:
                    factory = info.factory
                    break
            else:
                msg = (
                    f"Kernel '{self.kernel_display_name}' not found"
                    if self.kernel_name
                    else "No kernel selected"
                )
                self.change_kernel(msg=msg, startup=True)
                return
            self.kernel = factory(
                kernel_tab=self,
                allow_stdin=self.allow_stdin,
                default_callbacks=self.default_callbacks,
                **(
                    {"connection_file": connection_file}
                    if connection_file is not None
                    else {}
                ),
            )

        self.comms = comms or {}  # The client-side comm states
        self.completers.append(KernelCompleter(lambda: self.kernel))
        self.inspectors.append(KernelInspector(lambda: self.kernel))
        self.use_kernel_history = use_kernel_history
        self.history = (
            KernelHistory(lambda: self.kernel)
            if use_kernel_history
            else InMemoryHistory()
        )

        def _get_suggester() -> AutoSuggest | None:
            return autosuggest_factory(self.app.config.autosuggest, self.history)

        self.suggester = DynamicAutoSuggest(_get_suggester)

        self.app.create_background_task(self.load_lsps())

        self.post_init_kernel()

    def close(self, cb: Callable | None = None) -> None:
        """Shut down kernel when tab is closed."""
        if self.kernel is not None:
            self.kernel.shutdown()
        super().close(cb)

    def interrupt_kernel(self) -> None:
        """Interrupt the current `Notebook`'s kernel."""
        self.kernel.interrupt()

    def restart_kernel(self, cb: Callable | None = None) -> None:
        """Restart the current `Notebook`'s kernel."""

        def _cb(result: dict[str, Any]) -> None:
            self.kernel_started()
            if callable(cb):
                cb()

        if confirm := self.app.get_dialog("confirm"):
            confirm.show(
                message="Are you sure you want to restart the kernel?",
                cb=partial(self.kernel.restart, cb=_cb),
            )
        else:
            self.kernel.restart(cb=_cb)

    def kernel_started(self, result: dict[str, Any] | None = None) -> None:
        """Task to run when the kernel has started."""
        # Set kernel spec in metadata
        if self.kernel.status == "error":
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
        try:
            await self.history.load().__anext__()
        except StopAsyncIteration:
            pass

    @property
    def metadata(self) -> dict[str, Any]:
        """Return a dictionary to hold notebook / kernel metadata."""
        return self._metadata

    @property
    def kernel_name(self) -> str:
        """Return the name of the kernel defined in the notebook JSON."""
        return self.metadata.get("kernelspec", {}).get("name", "")

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

    @property
    def current_input(self) -> KernelInput:
        """Return the currently active kernel input, if any."""
        from euporie.core.widgets.inputs import KernelInput

        return self._current_input or KernelInput(self)

    def set_kernel_info(self, info: dict) -> None:
        """Handle kernel info requests."""
        self.metadata["language_info"] = info.get("language_info", {})

    def change_kernel(self, msg: str | None = None, startup: bool = False) -> None:
        """Prompt the user to select a new kernel."""
        kernel_infos = [x for x in list_kernels() if x.kind == "new"]

        # Warn the user if no kernels are installed
        if not kernel_infos:
            if startup and "no-kernels" in self.app.dialogs:
                self.app.dialogs["no-kernels"].show()
            return

        # Automatically select the only kernel if there is only one
        if startup and len(kernel_infos) <= 2:
            for info in kernel_infos:
                if info.type != NoKernel:
                    self.switch_kernel(info.factory)
                    return

        # Prompt user to select a kernel
        if dialog := self.app.get_dialog("change-kernel"):
            dialog.show(tab=self, message=msg)
            return

        if msg:
            log.warning(msg)

    def switch_kernel(self, factory: KernelFactory) -> None:
        """Shut down the current kernel and change to another."""
        if (old_kernel := self.kernel) is not None:
            old_kernel.shutdown(wait=True)
        kernel = factory(
            kernel_tab=self,
            default_callbacks=self.default_callbacks,
            allow_stdin=self.allow_stdin,
        )
        self.init_kernel(kernel)

    def kernel_died(self) -> None:
        """Call if the kernel dies."""
        import traceback

        log.info("".join(traceback.format_stack()))
        if confirm := self.app.get_dialog("confirm"):
            confirm.show(
                title="Kernel connection lost",
                message="The kernel appears to have died\n"
                "as it can no longer be reached.\n\n"
                "Do you want to restart the kernel?",
                cb=self.kernel.restart,
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

    def lsp_open_handler(self, lsp: LspClient) -> None:
        """Tell the LSP we opened a file."""
        lsp.open_doc(
            path=self.path, language=self.language, text=self.current_input.buffer.text
        )

    def lsp_change_handler(self, lsp: LspClient) -> None:
        """Tell the LSP server a file has changed."""
        lsp.change_doc(
            path=self.path,
            language=self.language,
            text=self.current_input.buffer.text,
        )

    def lsp_before_save_handler(self, lsp: LspClient) -> None:
        """Tell the the LSP we are about to save a document."""
        lsp.will_save_doc(self.path)

    def lsp_after_save_handler(self, lsp: LspClient) -> None:
        """Tell the the LSP we saved a document."""
        lsp.save_doc(self.path, text=self.current_input.buffer.text)

    def lsp_close_handler(self, lsp: LspClient) -> None:
        """Tell the LSP we opened a file."""
        lsp.close_doc(path=self.path)

    def lsp_update_diagnostics(self, lsp: LspClient) -> None:
        """Process a new diagnostic report from the LSP."""
        if (diagnostics := lsp.reports.pop(self.path.as_uri(), None)) is not None:
            self.reports[lsp] = Report.from_lsp(self.current_input.text, diagnostics)
            self.app.invalidate()

    def report(self) -> Report:
        """Return the current diagnostic reports."""
        return Report.from_reports(*self.reports.values())

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd(filter=kernel_tab_has_focus)
    def _change_kernel() -> None:
        """Change the notebook's kernel."""
        if isinstance(kt := get_app().tab, KernelTab):
            kt.change_kernel()
