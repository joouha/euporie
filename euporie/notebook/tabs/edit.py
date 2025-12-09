"""Contain a tab for displaying files."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, ClassVar

from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.layout.dimension import Dimension

from euporie.core.filters import insert_mode, replace_mode
from euporie.core.kernel.base import BaseKernel, MsgCallbacks
from euporie.core.key_binding.registry import load_registered_bindings
from euporie.core.lexers import detect_lexer
from euporie.core.tabs.kernel import KernelTab
from euporie.core.widgets.inputs import KernelInput

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from prompt_toolkit.layout.containers import AnyContainer, Window

    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields
    from euporie.core.comm.base import Comm

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
        kernel: BaseKernel | None = None,
        comms: dict[str, Comm] | None = None,
        use_kernel_history: bool = False,
    ) -> None:
        """Call when the tab is created."""
        self.default_callbacks = MsgCallbacks({})
        self._metadata = {"kernelspec": {"name": "none"}}
        self.loaded = False

        super().__init__(app, path, kernel, comms, use_kernel_history)

    def post_init_kernel(self) -> None:
        """Load UI and file in background after kernel has inited."""
        # Load the UI
        self.container = self.load_container()
        self.app.layout.focus(self.container)
        # Continue loading tab
        super().post_init_kernel()
        # Read file
        self.load()

    def load(self) -> None:
        """Load the text file."""
        try:
            text = self.path.read_text() if self.path is not None else ""
        except FileNotFoundError:
            text = ""

        # Set text
        self.input_box.text = text
        self.input_box.buffer.on_text_changed += lambda b: setattr(self, "dirty", True)
        self.input_box.read_only = False
        self.loaded = True

        # Detect language
        lexer = detect_lexer(text[:1000], self.path)
        if lexer:
            self._metadata = {"kernelspec": {"language": lexer.name.casefold()}}
        # Re-lex the file
        self.input_box.control._fragment_cache.clear()
        self.app.invalidate()

    def close(self, cb: Callable | None = None) -> None:
        """Check if the user want to save an unsaved notebook, then close the file.

        Args:
            cb: A callback to run if after closing the notebook.

        """
        if self.dirty and (unsaved := self.app.get_dialog("unsaved")):
            unsaved.show(
                tab=self,
                cb=partial(super().close, cb),
            )
        else:
            super().close(cb)

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
            ],
            [self.position, str(self.path)],
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
        """Load the "tab"'s main container."""
        assert self.path is not None

        self.input_box = self._current_input = KernelInput(
            kernel_tab=self,
            completer=self.completer,
            read_only=True,
            name="code",
            formatters=self.formatters,
            language=lambda: self.language,
            inspector=self.inspector,
            on_text_changed=lambda buf: self.on_change(),
            diagnostics=self.report,
            relative_line_numbers=self.app.config.filters.relative_line_numbers,
        )

        return HSplit(
            [self.input_box],
            width=Dimension(weight=1),
            height=Dimension(weight=1),
            key_bindings=load_registered_bindings(
                "euporie.core.tabs.base:Tab",
                config=self.app.config,
            ),
        )

    def write_file(self, path: Path) -> None:
        """Write the file's text data to a path.

        Args:
            path: An path at which to save the file

        """
        path.write_text(self.input_box.buffer.text)

    def __pt_searchables__(self) -> list[Window]:
        """Searchable buffers in the tab."""
        return [self.input_box.window]
