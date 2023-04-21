"""Defines a web-view tab."""


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.layout.containers import HSplit, VSplit
from prompt_toolkit.layout.dimension import Dimension

from euporie.core.convert.core import get_format
from euporie.core.data_structures import DiBool
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.tabs.base import Tab
from euporie.core.widgets.decor import FocusedStyle
from euporie.core.widgets.display import Display
from euporie.core.widgets.forms import Button, Text

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Sequence

    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.app import BaseApp

log = logging.getLogger(__name__)


class WebTab(Tab):
    """Tab class for displaying files."""

    def __init__(self, app: BaseApp, path: Path | None = None) -> None:
        """Call when the tab is created."""
        super().__init__(app, path)

        self.container = self.load_container()

        if self.path:
            self.load_url(self.path)

    def statusbar_fields(
        self,
    ) -> tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]:
        """Return a list of statusbar field values shown then this tab is active."""
        return ([str(self.path)], [])

    @property
    def title(self) -> str:
        """Return the tab title."""
        if self.path is not None:
            return str(self.path.name) or str(self.path)
        else:
            return "<Web Page>"

    def load_url(self, url: str | Path | None = None) -> bool:
        """Load a new URL, or the URL in the address-bar."""
        if url == "":
            return False

        if url is None:
            url = self.url_bar.text

        log.debug("Loading %s", url)

        url = UPath(url).resolve()
        self.path = url
        self.url_bar.text = str(url)

        self.display.path = url
        self.display.format_ = get_format(url, default="html")
        self.display.data = url.read_bytes()

        return True

    def load_container(self) -> AnyContainer:
        """Abcract method for loading the notebook's main container."""
        assert self.path is not None

        button_prev = Button(
            "◀",
            show_borders=DiBool(top=True, right=False, bottom=True, left=True),
            # on_click=lambda x: self.navigate_next(),
        )
        button_next = Button(
            "▶",
            show_borders=DiBool(top=True, right=True, bottom=True, left=False),
            # on_click=lambda x: self.navigate_prev(),
        )
        self.url_bar = Text(
            text=str(self.path),
            show_borders=DiBool(top=True, right=False, bottom=True, left=True),
            accept_handler=lambda buf: self.load_url(buf.text),
        )
        button_go = Button(
            "➜",
            show_borders=DiBool(top=True, right=True, bottom=True, left=False),
            on_click=lambda x: (self.load_url() and None) or None,  # typing magic
        )

        self.display = Display(
            data="",
            format_="html",
            path=self.path,
            focusable=True,
            focus_on_click=True,
            always_hide_cursor=True,
            dont_extend_height=False,
            scrollbar=False,
        )

        return HSplit(
            [
                VSplit(
                    [
                        FocusedStyle(button_prev),
                        FocusedStyle(button_next),
                        FocusedStyle(self.url_bar),
                        FocusedStyle(button_go),
                    ],
                    style="class:tab.toolbar",
                ),
                VSplit(
                    [
                        self.display,
                        MarginContainer(ScrollbarMargin(), target=self.display.window),
                    ]
                ),
            ],
            width=Dimension(weight=1),
            height=Dimension(weight=1),
        )
