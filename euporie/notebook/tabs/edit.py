"""Contain a tab for displaying files."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from prompt_toolkit.layout.containers import VSplit
from prompt_toolkit.layout.dimension import Dimension

from euporie.core.filters import insert_mode, replace_mode
from euporie.core.kernel import Kernel, MsgCallbacks
from euporie.core.key_binding.registry import load_registered_bindings
from euporie.core.lexers import detect_lexer
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.tabs.base import KernelTab
from euporie.core.widgets.inputs import KernelInput

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Callable

    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.app import BaseApp
    from euporie.core.comm.base import Comm
    from euporie.core.widgets.status_bar import StatusBarFields

log = logging.getLogger(__name__)


class EditorTab(KernelTab):
    """Tab class for editing text files."""

    name = "Text Editor"
    weight = 1
    mime_types: ClassVar[set[str]] = {"text/*"}

    allow_stdin = True

    def __init__(
        self,
        app: BaseApp,
        path: Path | None = None,
        kernel: Kernel | None = None,
        comms: dict[str, Comm] | None = None,
        use_kernel_history: bool = False,
    ) -> None:
        """Call when the tab is created."""
        self.default_callbacks = MsgCallbacks({})
        self._metadata = {}
        self.loaded = False

        super().__init__(app, path, kernel, comms, use_kernel_history)

    def post_init_kernel(self) -> None:
        """Load UI and file in background after kernel has inited."""
        # Load the UI
        self.container = self.load_container()
        self.app.layout.focus(self.container)

        # Read file
        self.load()

    def load(self) -> None:
        """Load the text file."""
        text = self.path.read_text() if self.path is not None else ""

        # Set text
        self.input_box.text = text
        self.input_box.buffer.on_text_changed += lambda b: setattr(self, "dirty", True)
        self.input_box.read_only = False
        self.loaded = True

        # Detect language
        lexer = detect_lexer(text[:1000], self.path)
        if lexer:
            self._metadata = {"kernelspec": {"language": lexer.name}}
        # Re-lex the file
        self.input_box.control._fragment_cache.clear()
        self.app.invalidate()

    @property
    def position(self) -> str:
        """Return the position of the cursor in the document."""
        doc = self.input_box.buffer.document
        return f"{doc.cursor_position_row + 1}:{doc.cursor_position_col}"

    def __pt_status__(self) -> StatusBarFields | None:
        """Return a list of statusbar field values shown then this tab is active."""
        if not self.loaded:
            return (["Loading…"], [])
        return (
            [
                ("I" if insert_mode() else ("o" if replace_mode() else ">")),
                self.position,
            ],
            [str(self.path)],
        )

    @property
    def path_name(self) -> str:
        """Return the path name."""
        if self.path is not None:
            return self.path.name
        else:
            return "(New file)"

    @property
    def title(self) -> str:
        """Return the tab title."""
        return ("* " if self.dirty else "") + self.path_name

    def load_container(self) -> AnyContainer:
        """Abcract method for loading the notebook's main container."""
        assert self.path is not None

        self.input_box = KernelInput(kernel_tab=self, right_margins=[], read_only=True)

        return VSplit(
            [
                self.input_box,
                MarginContainer(ScrollbarMargin(), target=self.input_box.window),
            ],
            width=Dimension(weight=1),
            height=Dimension(weight=1),
            key_bindings=load_registered_bindings("euporie.core.tabs.base.Tab"),
        )

    def save(self, path: Path | None = None, cb: Callable | None = None) -> None:
        """Save the current file."""
        if path is not None:
            self.path = path

        if self.path is None:
            if dialog := self.app.dialogs.get("save-as"):
                dialog.show(tab=self, cb=cb)
        else:
            log.debug("Saving file...")
            self.saving = True
            self.app.invalidate()

            # Save to a temp file, then replace the original
            temp_path = self.path.parent / f".{self.path.stem}.tmp{self.path.suffix}"
            log.debug("Using temporary file %s", temp_path.name)
            try:
                open_file = temp_path.open("w")
            except NotImplementedError:
                if dialog := self.app.dialogs.get("save-as"):
                    dialog.show(tab=self, cb=cb)
            else:
                try:
                    open_file.write(self.input_box.buffer.text)
                except Exception:
                    if dialog := self.app.dialogs.get("save-as"):
                        dialog.show(tab=self, cb=cb)
                else:
                    try:
                        temp_path.rename(self.path)
                    except Exception:
                        if dialog := self.app.dialogs.get("save-as"):
                            dialog.show(tab=self, cb=cb)
                    else:
                        self.dirty = False
                        self.saving = False
                        self.app.invalidate()
                        log.debug("File saved")
            # Run the callback
            if callable(cb):
                cb()
