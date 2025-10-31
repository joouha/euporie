"""Defines a web-view tab."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.containers import HSplit, VSplit
from prompt_toolkit.layout.dimension import Dimension
from upath import UPath

from euporie.core.app.current import get_app
from euporie.core.convert.mime import get_mime
from euporie.core.data_structures import DiBool
from euporie.core.layout.decor import FocusedStyle
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.tabs.base import Tab
from euporie.core.widgets.display import DisplayWindow
from euporie.core.widgets.forms import Button, Text
from euporie.web.widgets.webview import WebViewControl

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any, ClassVar

    from prompt_toolkit.layout.containers import AnyContainer

    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields

log = logging.getLogger(__name__)


class WebTab(Tab):
    """Tab class for displaying files."""

    name = "Web Viewer"
    weight = 2
    mime_types: ClassVar[set[str]] = {"text/html", "text/markdown"}

    def __init__(self, app: BaseApp, path: Path | None) -> None:
        """Call when the tab is created."""
        super().__init__(app, path)
        self.status: Callable[[], StatusBarFields] | None = None

        def _load() -> None:
            old_container = self.container
            self.container = self.load_container()
            if self.app.layout.has_focus(old_container):
                self.focus()
            self.app.invalidate()

        self._load_task = app.create_background_task(asyncio.to_thread(_load))

    def focus(self) -> None:
        """Focus the webview when this tab is focused."""
        self.app.layout.focus(self.webview)

    @property
    def title(self) -> str:
        """Return the tab title."""
        if (webview := getattr(self, "webview", None)) and (title := webview.title):
            return title
        if self.path is not None:
            return str(self.path.name) or str(self.path)
        else:
            return "<Web Page>"

    def load_url(self, url: str | Path, new_tab: bool = False, **kwargs: Any) -> bool:
        """Load a new URL, or the URL in the address-bar."""
        log.debug("Loading %s", url)
        self.webview.loading = True
        self.app.invalidate()
        if not url:
            return False
        if isinstance(url, str):
            url = UPath(url, protocol="https" if ":" not in url else None)
        if not new_tab and get_mime(url) in self.mime_types:
            self.webview.load_url(url, **kwargs)
        else:
            self.webview.loading = False
            get_app().open_file(url)
        return True

    def _url_loaded(self, webview: WebViewControl) -> None:
        """Trigger callback when the URL is loaded."""
        url = webview.url
        if url is not None:
            self.path = UPath(url)
            self.url_bar.text = str(url)
        # Focus the webview
        self.app.layout.current_control = self.webview

    def load_container(self) -> AnyContainer:
        """Abcract method for loading the notebook's main container."""
        assert self.path is not None
        path = self.path
        self.webview = WebViewControl(url=path, link_handler=self.load_url)
        self.webview.rendered += self._url_loaded

        def _status() -> StatusBarFields:
            return (self.webview.status if self.webview is not None else [], [])

        self.status = _status

        button_prev = Button(
            "◀",
            show_borders=DiBool(top=True, right=False, bottom=True, left=True),
            disabled=Condition(lambda: not self.webview.prev_stack[:-1]),
            on_click=lambda x: self.webview.nav_prev(),
        )
        button_next = Button(
            "▶",
            show_borders=DiBool(top=True, right=True, bottom=True, left=False),
            disabled=Condition(lambda: not self.webview.next_stack),
            on_click=lambda x: self.webview.nav_next(),
        )
        button_refresh = Button(
            "↻",
            on_click=lambda x: (self.load_url(self.path) and False) or None,
        )

        def _select_url() -> None:
            """Select all in url bar when it gains focus."""
            from prompt_toolkit.selection import SelectionState

            buffer = self.url_bar.buffer
            buffer.selection_state = SelectionState(0)
            buffer.cursor_position = len(buffer.text)
            buffer.selection_state.enter_shift_mode()

        self.url_bar = Text(
            text=str(path),
            show_borders=DiBool(top=True, right=False, bottom=True, left=True),
            accept_handler=lambda buf: self.load_url(buf.text),
            on_focus=_select_url,
        )
        button_go = Button(
            "➜",
            show_borders=DiBool(top=True, right=True, bottom=True, left=False),
            on_click=lambda x: (self.load_url(self.url_bar.text) and None)
            or None,  # Magical typing magic
        )

        return HSplit(
            [
                VSplit(
                    [
                        FocusedStyle(button_prev),
                        FocusedStyle(button_next),
                        FocusedStyle(button_refresh),
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

    def __pt_status__(self) -> StatusBarFields:
        """Return a list of statusbar field values shown then this tab is active."""
        if callable(self.status):
            return self.status()
        else:
            return ([], [])
