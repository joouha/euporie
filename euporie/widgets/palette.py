"""Contains the command palette container."""

from __future__ import annotations

import logging
import re
from functools import partial
from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    HSplit,
    ScrollOffsets,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.widgets.base import Box, Frame, Shadow, TextArea

from euporie.app.current import get_tui_app as get_app
from euporie.commands.base import Command
from euporie.commands.registry import commands
from euporie.key_binding.util import format_keys

if TYPE_CHECKING:
    from typing import Optional

    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.controls import GetLinePrefixCallable

    from euporie.app.base import StatusBarFields

log = logging.getLogger(__name__)


_CommandMatch = NamedTuple(
    "_CommandMatch",
    [("length", int), ("position", int), ("command", Command)],
)


class CommandMenuControl(UIControl):
    """A filterable and navigable list of commands."""

    def __init__(self, command_palette: "CommandPalette", width: "int" = 60) -> "None":
        """Instantiates a new command list instance."""
        self.palette = command_palette
        self.width = width

    # def is_focusable(self) -> "bool":
    # return True

    def create_content(self, width: "int", height: "int") -> "UIContent":
        """Create a UIContent object for this control."""

        def get_line(i: "int") -> "StyleAndTextTuples":
            result: "StyleAndTextTuples" = []
            match = self.palette.matches[i]

            # Set style depending on row number / selection status
            if i == self.palette.index:
                style = "class:palette.item.selected"
            elif (i + 1) % 2 == 0:
                style = "class:palette.item.alt"
            else:
                style = "class:palette.item"

            # Calculate prefix
            if match.command.toggled is not None and match.command.toggled():
                prefix = " ✓ "
            else:
                prefix = "   "

            # Calculate suffix
            if match.command.keys:
                suffix = format_keys(match.command.keys)[0] + " "
            else:
                suffix = ""

            # Add prefix with status for toggle commands
            result.append((style, prefix))

            # Get list of input character and search text
            chars = list(self.palette.text_area.text)
            text = match.command.title.ljust(width - len(prefix) - len(suffix))
            # Add text before the match
            result.append((style, text[: match.position]))
            # Format text, undelining matching characters
            for c in text[match.position : match.position + match.length]:
                if chars and c.lower() == chars[0].lower():
                    result.append((style + " underline", c))
                    del chars[0]
                else:
                    result.append((style, c))
            # Add text after the match
            result.append((style, text[match.position + match.length :]))

            # Add suffix with key-binding
            result.append((style + " italic", suffix))

            return result

        return UIContent(
            get_line=get_line,
            cursor_position=Point(x=0, y=self.palette.index * 1 or 0),
            line_count=len(self.palette.matches),
        )

    def preferred_width(self, max_available_width: "int") -> "Optional[int]":
        """Returns the preferred width of the command list."""
        return min(self.width, max_available_width)

    def preferred_height(
        self,
        width: "int",
        max_available_height: "int",
        wrap_lines: "bool",
        get_line_prefix: "Optional[GetLinePrefixCallable]",
    ) -> "Optional[int]":
        """Returns the preferred height of the command list."""
        return min(
            max_available_height // 2,
            len(self.palette.matches),
        )

    def mouse_handler(self, mouse_event: "MouseEvent") -> "NotImplementedOrNone":
        """Handle clicking and scrolling mouse events."""
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.palette.index = mouse_event.position.y
            self.palette.accept()

        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            # Scroll up.
            self.palette.select(1)

        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            # Scroll down.
            self.palette.select(-1)

        return None


class CommandPalette:
    """A command palette which allows searching the available commands."""

    index: "int"
    matches: "list[_CommandMatch]"

    def __init__(self) -> "None":
        """Instantiates a new command palette instance."""
        self.matches: "list[_CommandMatch]" = []
        self.index = 0

        self.last_focused: "Optional[UIControl]" = None
        self._visible = False
        self.visible = Condition(lambda: self._visible)

        self.kb = KeyBindings()
        self.kb.add("s-tab")(focus_previous)
        self.kb.add("tab")(focus_next)
        self.kb.add("escape")(self.hide)
        self.kb.add("up", filter=Condition(lambda: bool(self.matches)))(
            partial(self.select, -1)
        )
        self.kb.add("down", filter=Condition(lambda: bool(self.matches)))(
            partial(self.select, 1)
        )
        self.kb.add("pageup", filter=Condition(lambda: bool(self.matches)))(
            partial(self.select, -10)
        )
        self.kb.add("pagedown", filter=Condition(lambda: bool(self.matches)))(
            partial(self.select, 10)
        )
        self.kb.add("home", filter=Condition(lambda: bool(self.matches)))(
            partial(lambda e: self.select(-self.index))
        )
        self.kb.add("end", filter=Condition(lambda: bool(self.matches)))(
            partial(lambda e: self.select(len(self.matches)))
        )

        self.text_area = TextArea(
            multiline=False,
            accept_handler=self.accept,
        )
        self.text_area.buffer.on_text_changed += self.text_changed
        scroll_bar_margin = ScrollbarMargin(display_arrows=True)
        scroll_bar_margin.up_arrow_symbol = "▲"
        scroll_bar_margin.down_arrow_symbol = "▼"

        self.container = ConditionalContainer(
            Shadow(
                body=Frame(
                    body=Box(
                        body=HSplit(
                            [
                                VSplit(
                                    [self.text_area],
                                    padding=1,
                                ),
                                Window(
                                    CommandMenuControl(self),
                                    scroll_offsets=ScrollOffsets(bottom=1),
                                    right_margins=[scroll_bar_margin],
                                ),
                            ],
                        ),
                        padding=Dimension(preferred=1, max=1),
                        padding_bottom=0,
                        padding_top=0,
                    ),
                    title="Search for a command",
                    key_bindings=self.kb,
                    modal=True,
                    style="class:dialog.body",
                )
            ),
            filter=self.visible,
        )

        get_app().container_statuses[self] = self.statusbar_fields

    def statusbar_fields(
        self,
    ) -> "StatusBarFields":
        """Returns a list of statusbar field values shown then this tab is active."""
        if self.matches:
            return ([self.matches[self.index].command.description], [])
        else:
            return ([], [])

    def select(self, n: "int", event: "KeyPressEvent" = None) -> "None":
        """Change the index of the selected command.

        Args:
            n: The relative amount by which to change the selected index
            event: Ignored

        """
        self.index += n
        self.index = min(len(self.matches) - 1, max(0, self.index))

    def text_changed(self, buffer: "Buffer") -> "None":
        """Called when the input text changes: filters the command list."""
        self.matches = []

        # Lookahead regex to manage overlapping matches
        regex = re.compile(
            "(?=({0}))".format(".*?".join(map(re.escape, buffer.text))), re.IGNORECASE
        )
        for cmd in commands.values():
            if not cmd.hidden():
                matches = list(regex.finditer(cmd.title))
                if matches:
                    # Prefer the match closest to the left, then shortest.
                    best = min(matches, key=lambda m: (len(m.group(1)), m.start()))
                    self.matches.append(
                        _CommandMatch(len(best.group(1)), best.start(), cmd)
                    )
        self.matches = sorted(self.matches, key=lambda m: (m.length, m.position))

        # Ensure the selected index is within the list of matches
        self.index = min(len(self.matches) - 1, max(0, self.index))

    def hide(self, event: "KeyPressEvent" = None) -> "None":
        """Hides the command palette and returns focus to what was focused before."""
        self._visible = False
        app = get_app()
        if (
            self.last_focused is not None
            and self.last_focused in app.layout.find_all_controls()
        ):
            app.layout.focus(self.last_focused)
        app.has_dialog = False

    def accept(self, buffer: "Optional[Buffer]" = None) -> "bool":
        """Called on :kbd:`enter`: runs the selected command."""
        if self.matches:
            self.hide()
            self.matches[self.index].command.run()
            return True
        else:
            return False

    def show(self) -> "None":
        """Displays and focuses the command palette."""
        self._visible = True
        self.text_area.text = ""
        app = get_app()
        self.last_focused = app.layout.current_control
        app.layout.focus(self.text_area)
        app.has_dialog = True

    def toggle(self) -> "None":
        """Shows or hides the command palette."""
        if self._visible:
            self.hide()
        else:
            self.show()

    def __pt_container__(self) -> "ConditionalContainer":
        """Return the main container object."""
        return self.container
