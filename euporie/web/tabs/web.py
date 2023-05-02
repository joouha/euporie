"""Defines a web-view tab."""


from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.containers import HSplit, VSplit
from prompt_toolkit.layout.dimension import Dimension

from euporie.core.data_structures import DiBool
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.tabs.base import Tab
from euporie.core.widgets.decor import FocusedStyle
from euporie.core.widgets.display import DisplayWindow
from euporie.core.widgets.forms import Button, Text
from euporie.web.widgets.webview import WebViewControl

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Sequence

    from prompt_toolkit.formatted_text import AnyFormattedText
    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.app import BaseApp

log = logging.getLogger(__name__)


class WebTab(Tab):
    """Tab class for displaying files."""

    name = "Web Viewer"
    weight = 2
    mime_types = {"text/html"}

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
        self.webview.load_url(url)
        return True

    def _url_loaded(self, webview: WebViewControl) -> None:
        """Trigger callback when the URL is loaded."""
        url = webview.url
        self.path = url
        self.url_bar.text = str(url)

    def load_container(self) -> AnyContainer:
        """Abcract method for loading the notebook's main container."""
        assert self.path is not None

        self.webview = WebViewControl(url=self.path)
        self.webview.rendered += self._url_loaded

        button_prev = Button(
            "◀",
            show_borders=DiBool(top=True, right=False, bottom=True, left=True),
            disabled=Condition(lambda: not self.webview.prev_stack),
            on_click=lambda x: self.webview.nav_prev(),
        )
        button_next = Button(
            "▶",
            show_borders=DiBool(top=True, right=True, bottom=True, left=False),
            disabled=Condition(lambda: not self.webview.next_stack),
            on_click=lambda x: self.webview.nav_next(),
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
                        window := DisplayWindow(self.webview),
                        MarginContainer(ScrollbarMargin(), target=window),
                    ]
                ),
            ],
            width=Dimension(weight=1),
            height=Dimension(weight=1),
        )
