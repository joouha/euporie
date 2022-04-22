"""Defines a tab bar widget for switching between tabs."""

import logging
from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseEventType

if TYPE_CHECKING:
    from typing import Callable, Optional

    from prompt_toolkit.formatted_text.base import StyleAndTextTuples
    from prompt_toolkit.layout.containers import Container
    from prompt_toolkit.mouse_events import MouseEvent

    from euporie.app.base import EuporieApp
    from euporie.tabs.base import Tab

log = logging.getLogger(__name__)


class TabBar:
    """A tab-bar which shows and switches between currently opened tabs."""

    bg_char = "▁"

    def _get_tab_fragments(self) -> "StyleAndTextTuples":
        result: "StyleAndTextTuples" = [("", self.bg_char)]

        any_active = any(self.app.layout.has_focus(tab) for tab in self.app.tabs)
        for tab in self.app.tabs:
            active = self.app.layout.has_focus(tab)
            if active:
                self.last_active: "Optional[Tab]" = tab
            elif not any_active:
                active = tab == self.last_active
            style = f"class:tab-bar.tab{',active' if active else ''}"

            click_to_focus = self.on_click(tab.focus)
            result.extend(
                [
                    (f"{style},tab-bar.tab.edge", "▏ ", click_to_focus),
                    (style, f"{tab.title}", click_to_focus),
                    (
                        f"{style},tab-bar.tab.close",
                        " ✖",
                        self.on_click(partial(self.app.close_tab, tab)),
                    ),
                    (f"{style},tab-bar.tab.edge", "▕", click_to_focus),
                    ("", self.bg_char),
                ]
            )
        result.extend([("", self.bg_char)])

        return result

    def _get_header_fragments(self) -> "StyleAndTextTuples":
        result: "StyleAndTextTuples" = []

        any_active = any(self.app.layout.has_focus(tab) for tab in self.app.tabs)
        for tab in self.app.tabs:
            active = self.app.layout.has_focus(tab)
            if active:
                self.last_active = tab
            elif not any_active:
                active = tab == self.last_active

            result.extend(
                [
                    (" ", " "),
                    (
                        f"class:tab-bar.tab.head{',active' if active else ''}",
                        self.bg_char * (len(tab.title) + 4 + 1),
                    ),
                ]
            )

        return result

    def __init__(self, app: "EuporieApp") -> "None":
        """Creates a new tab bar instance.

        Args:
            app: The euporie application instance the tab bar is for

        """
        self.app = app
        self.container = HSplit(
            [
                Window(
                    FormattedTextControl(self._get_header_fragments),
                    height=1,
                ),
                Window(
                    FormattedTextControl(self._get_tab_fragments),
                    height=1,
                    char=self.bg_char,
                ),
            ],
            style="class:tab-bar",
        )
        self.last_active = None

    def on_click(self, func: "Callable") -> "Callable[[MouseEvent], None]":
        """Generate a mouse event handler which calls a function on click."""

        def _handler(mouse_event: "MouseEvent") -> "None":
            if mouse_event.event_type == MouseEventType.MOUSE_DOWN:
                func()
            elif mouse_event.event_type == MouseEventType.SCROLL_UP:
                self.app.tab_idx -= 1
            elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                self.app.tab_idx += 1

        return _handler

    def __pt_container__(self) -> "Container":
        """Return the widget's container."""
        return self.container


"""
Some tab design ideas:

▔▒▒▒▒▔▔▒▒▒▒▔
▒▒▒▒▒▒▒▒▒▒▒▒

 🬦█████🬓 ▗████▖
████████████████

╭──────╮ ╭───────╮
│ File │ │ Tab 2 │
▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

🬞🬭🬭🬭🬭🬭🬭🬏 🬞🬭🬭🬭🬭🬭🬭🬏
▐ File ▌ ▐ File ▌
▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
 ▁▁▁▁▁▁   ▁▁▁▁▁▁
╱ File ╲ ╱ File ╲
▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

██████████████████████
██ File ██ File ██
▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒

"""
