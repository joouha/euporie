"""Contains a tab for displaying files."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.layout.containers import VSplit
from prompt_toolkit.layout.dimension import Dimension

from euporie.core.kernel import Kernel, MsgCallbacks
from euporie.core.lexers import detect_lexer

# from euporie.core.margins import MarginContainer
from euporie.core.tabs.base import KernelTab
from euporie.core.widgets.inputs import KernelInput

if TYPE_CHECKING:
    from typing import Sequence

    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.layout.containers import AnyContainer
    from upath import UPath

    from euporie.core.app import BaseApp
    from euporie.core.comm.base import Comm

log = logging.getLogger(__name__)


class EditorTab(KernelTab):
    """Tab class for editing text files."""

    allow_stdin = True
    _metadata = {}

    def __init__(
        self,
        app: "BaseApp",
        path: "UPath|None" = None,
        kernel: "Kernel|None" = None,
        comms: "dict[str, Comm]|None" = None,
        use_kernel_history: "bool" = False,
    ) -> "None":
        """Called when the tab is created."""
        self.default_callbacks = MsgCallbacks({})
        super().__init__(app, path, kernel, comms, use_kernel_history)

        # Load file
        if self.path is not None:
            text = self.path.read_text()
        else:
            text = ""

        # Detect language
        lexer = detect_lexer(text, path)
        self._metadata = {"kernelspec": {"language": lexer.name}}

        # Load UI
        self.container = self.load_container()

        self.input_box.text = text

    def statusbar_fields(
        self,
    ) -> "tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]":
        """Returns a list of statusbar field values shown then this tab is active."""
        return ([str(self.path)], [])

    @property
    def title(self) -> "str":
        """Return the tab title."""
        if self.path is not None:
            return str(self.path.name)
        else:
            return "<New File>"

    def load_container(self) -> "AnyContainer":
        """Abscract method for loading the notebook's main container."""
        assert self.path is not None

        self.input_box = KernelInput(kernel_tab=self)

        return VSplit(
            [
                self.input_box,
                # MarginContainer(ScrollbarMargin(), target=self.input_box.window),
            ],
            width=Dimension(weight=1),
            height=Dimension(weight=1),
        )
