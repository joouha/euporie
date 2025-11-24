"""Contain the command palette container."""

from __future__ import annotations

import logging
import re
from functools import partial
from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.key_binding.vi_state import InputMode
from prompt_toolkit.layout.containers import ScrollOffsets
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType

from euporie.core.app.current import get_app
from euporie.core.bars.status import StatusContainer
from euporie.core.commands import Command, add_cmd, commands
from euporie.core.key_binding.registry import register_bindings
from euporie.core.layout.containers import HSplit, VSplit, Window
from euporie.core.layout.decor import FocusedStyle
from euporie.core.margins import MarginContainer, ScrollbarMargin
from euporie.core.widgets.dialog import Dialog
from euporie.core.widgets.forms import Text

if TYPE_CHECKING:
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.controls import GetLinePrefixCallable

    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields

log = logging.getLogger(__name__)


class _CommandMatch(NamedTuple):
    length: int
    position: int
    command: Command


class CommandMenuControl(UIControl):
    """A filterable and navigable list of commands."""

    def __init__(self, command_palette: CommandPalette, width: int = 60) -> None:
        """Instantiate a new command list instance."""
        self.palette = command_palette
        self.width = width

    def create_content(self, width: int, height: int) -> UIContent:
        """Create a UIContent object for this control."""

        def get_line(i: int) -> StyleAndTextTuples:
            result: StyleAndTextTuples = []
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
            suffix = match.command.key_str() + " "

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

    def preferred_width(self, max_available_width: int) -> int | None:
        """Return the preferred width of the command list."""
        return min(self.width, max_available_width)

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int | None:
        """Return the preferred height of the command list."""
        return min(
            max_available_height // 2,
            len(self.palette.matches),
        )

    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone:
        """Handle clicking and scrolling mouse events."""
        if mouse_event.event_type in {
            MouseEventType.MOUSE_MOVE,
            MouseEventType.MOUSE_DOWN,
        }:
            self.palette.index = mouse_event.position.y

        elif mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.palette.index = mouse_event.position.y
            self.palette.accept()

        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            # Scroll up.
            self.palette.select(1)

        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            # Scroll down.
            self.palette.select(-1)

        return None


class CommandPalette(Dialog):
    """A command palette which allows searching the available commands."""

    index: int
    matches: list[_CommandMatch]

    title = "Search for a command"
    body_padding_top = 0
    body_padding_bottom = 0

    def __init__(self, app: BaseApp) -> None:
        """Instantiate a new command palette instance."""
        super().__init__(app=app)
        self.matches: list[_CommandMatch] = []
        self.index = 0

        self.last_focused: UIControl | None = None
        self._visible = False
        self.visible = Condition(lambda: self._visible)

        # self.kb = KeyBindings()
        self.kb.add("s-tab")(focus_previous)
        self.kb.add("tab")(focus_next)
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

        self.text_area = Text(
            multiline=False,
            accept_handler=self.accept,
            style="class:input",
            expand=False,
            placeholder="  Type to search…",
        )
        self.text_area.buffer.on_text_changed += self.text_changed

        self.body = StatusContainer(
            body=HSplit(
                [
                    VSplit(
                        [FocusedStyle(self.text_area)],
                        padding=1,
                    ),
                    VSplit(
                        [
                            window := Window(
                                CommandMenuControl(self),
                                scroll_offsets=ScrollOffsets(bottom=1),
                            ),
                            MarginContainer(ScrollbarMargin(), target=window),
                        ]
                    ),
                ],
            ),
            status=self.__pt_status__,
        )
        self.buttons = {}

    def load(self) -> None:
        """Reset the dialog ready for display."""
        self.text_area.buffer.text = ""
        self.to_focus = self.text_area
        app = get_app()
        app.vi_state.input_mode = InputMode.INSERT

    def select(self, n: int, event: KeyPressEvent | None = None) -> None:
        """Change the index of the selected command.

        Args:
            n: The relative amount by which to change the selected index
            event: Ignored

        """
        self.index += n
        self.index = min(len(self.matches) - 1, max(0, self.index))

    def text_changed(self, buffer: Buffer) -> None:
        """Call when the input text changes: filters the command list."""
        self.matches = []

        # Lookahead regex to manage overlapping matches
        regex = re.compile(
            "(?=({}))".format(".*?".join(map(re.escape, buffer.text))), re.IGNORECASE
        )
        for cmd in set(commands.values()):
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

    def accept(self, buffer: Buffer | None = None) -> bool:
        """Call on :kbd:`enter`: runs the selected command."""
        if self.matches:
            self.hide()
            self.matches[self.index].command.run()
            return True
        else:
            return False

    def __pt_status__(self) -> StatusBarFields | None:
        """Return a list of statusbar field values shown then this tab is active."""
        if self.matches:
            return ([self.matches[self.index].command.description], [])
        return None

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd()
    def _toggle_command_palette() -> None:
        """Show the command palette."""
        if command_palette := get_app().get_dialog("command-palette"):
            command_palette.toggle()

    @staticmethod
    @add_cmd(icon="", style="class:teal", menu_title="Command palette")
    def _show_command_palette() -> None:
        """Show the command palette."""
        if command_palette := get_app().get_dialog("command-palette"):
            command_palette.show()

    @staticmethod
    @add_cmd()
    def _hide_command_palette() -> None:
        """Hide the command palette."""
        if command_palette := get_app().get_dialog("command-palette"):
            command_palette.hide()

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.core.app.app:BaseApp": {
                "show-command-palette": "c-@",
            }
        }
    )
