"""Contains a tab for displaying files."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.layout.containers import VSplit
from prompt_toolkit.layout.dimension import Dimension

from euporie.core.convert.base import get_format
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.tabs.base import Tab
from euporie.core.widgets.display import Display

if TYPE_CHECKING:
    from typing import Optional, Sequence

    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.layout.containers import AnyContainer
    from upath import UPath

    from euporie.core.app import BaseApp

log = logging.getLogger(__name__)


class DisplayTab(Tab):
    """Tab class for displaying files."""

    def __init__(self, app: "BaseApp", path: "Optional[UPath]" = None) -> "None":
        """Called when the tab is created."""
        super().__init__(app, path)
        if self.path is not None:
            self.container = self.load_container()

    def statusbar_fields(
        self,
    ) -> "tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]":
        """Returns a list of statusbar field values shown then this tab is active."""
        return ([str(self.path)], [])

    @property
    def title(self) -> "str":
        """Return the tab title."""
        if self.path is not None:
            return str(self.path.name) or str(self.path)
        else:
            return "<file>"

    def load_container(self) -> "AnyContainer":
        """Abscract method for loading the notebook's main container."""
        assert self.path is not None

        self.display = Display(
            data=self.path.read_bytes(),
            format_=get_format(self.path),
            path=self.path,
            focusable=True,
            focus_on_click=True,
            always_hide_cursor=True,
            dont_extend_height=False,
            scrollbar=False,
        )
        return VSplit(
            [
                self.display,
                MarginContainer(ScrollbarMargin(), target=self.display.window),
            ],
            width=Dimension(weight=1),
            height=Dimension(weight=1),
        )
