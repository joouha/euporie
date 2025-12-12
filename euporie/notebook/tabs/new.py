"""Contain a placeholder tab."""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.mouse_events import MouseButton, MouseEventType

from euporie.core.bars.status import StatusContainer
from euporie.core.border import RoundedLine
from euporie.core.commands import get_cmd
from euporie.core.convert.datum import Datum
from euporie.core.data_structures import DiBool
from euporie.core.layout.containers import HSplit, VSplit, Window
from euporie.core.layout.decor import FocusedStyle, Pattern
from euporie.core.tabs.base import Tab
from euporie.core.widgets.display import Display
from euporie.core.widgets.file_browser import FileBrowser
from euporie.core.widgets.forms import BaseButton, Button
from euporie.core.widgets.layout import Border, Box
from euporie.core.widgets.logo import logo_medium
from euporie.notebook.tips import TIPS

if TYPE_CHECKING:
    from pathlib import Path

    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.mouse_events import MouseEvent

    from euporie.core.app.app import BaseApp
    from euporie.core.bars.status import StatusBarFields
    from euporie.core.commands import Command

log = logging.getLogger(__name__)


class NewTab(Tab):
    """Tab class for displaying files."""

    name = "New Tab"

    def __init__(self, app: BaseApp, path: Path | None = None) -> None:
        """Replace the main tab container."""
        super().__init__(app, path)
        self.container = self.load_container()

    def load_container(self) -> AnyContainer:
        """Abstract method for loading the notebook's main container."""
        pattern = Pattern(
            lambda: self.app.config.background_character,
            lambda: self.app.config.background_pattern,
        )

        cmds = [
            "new-notebook",
            "new-console",
            "new-text-file",
            "open-file",
            "show-command-palette",
        ]
        buttons = []
        for name in cmds:
            cmd = get_cmd(name)

            def _on_click(button: BaseButton, cmd: Command = cmd) -> None:
                cmd.run()

            buttons.append(
                FocusedStyle(
                    Button(
                        text=[
                            (f"class:icon {cmd.style} dim", cmd.icon),
                            ("", f"\n{cmd.menu_title}"),
                        ],
                        on_click=_on_click,
                        width=Dimension(preferred=17, max=17),
                        dont_extend_width=False,
                        show_borders=DiBool(False, False, False, False),
                    )
                )
            )
        cmds_section = StatusContainer(
            Border(
                Box(
                    HSplit(
                        buttons,
                        Window(height=Dimension(max=1)),
                        padding_char=" ",
                        padding=Dimension(max=1),
                    ),
                    padding=Dimension(max=1),
                ),
                title="Quick Actions",
                border=RoundedLine.grid,
                style="class:tab-padding",
            ),
            self._status,
        )

        tip = random.choice(TIPS)  # noqa: S311
        tip_display = Display(
            Datum(tip, format="markdown"),
            dont_extend_width=False,
            wrap_lines=True,
            width=Dimension(preferred=0),
        )

        def _tip_click(mouse_event: MouseEvent) -> NotImplementedOrNone:
            if (
                mouse_event.button == MouseButton.LEFT
                and mouse_event.event_type == MouseEventType.MOUSE_UP
            ):
                tip_display.datum = Datum(random.choice(TIPS), format="markdown")  # noqa: S311
                return None
            return NotImplemented

        tip_section = Border(
            Box(
                tip_display,
                padding=Dimension(max=1),
            ),
            title=[("", "💡 Tip of the Day", _tip_click)],
            border=RoundedLine.grid,
            style="class:tab-padding",
        )

        recent_files_section = Border(
            FileBrowser(
                path=lambda: self.app.config.recent_files,
                on_open=self.app.open_file,
                show_address_bar=False,
                show_icons=self.app.config.filters.show_file_icons,
                height=Dimension(min=3, max=10),
            ),
            title="Recent Files",
            border=RoundedLine.grid,
            style="class:tab-padding",
        )

        content = Border(
            Box(
                HSplit(
                    [
                        VSplit(
                            [
                                cmds_section,
                                HSplit(
                                    [
                                        Box(
                                            logo_medium,
                                            padding_top=Dimension(max=1),
                                            padding_bottom=Dimension(max=1),
                                        ),
                                        recent_files_section,
                                    ],
                                    padding=Dimension(max=1),
                                ),
                            ],
                            padding=Dimension(max=1),
                        ),
                        tip_section,
                    ],
                    padding=Dimension(max=1),
                ),
                padding_top=0,
                padding_left=Dimension(max=1),
                padding_right=Dimension(max=1),
                padding_bottom=0,
            ),
            border=RoundedLine.grid,
            style="class:tab-padding",
        )

        return HSplit(
            [pattern, VSplit([pattern, content, pattern]), pattern],
            style="class:new-tab",
        )

    def _status(self) -> StatusBarFields | None:
        """Load the default statusbar fields (run after keybindings are loaded)."""
        return (
            [
                [
                    ("", "Press "),
                    ("bold", get_cmd("new-notebook").key_str()),
                    ("", " to start a new notebook"),
                ],
            ],
            [[("", "Press "), ("bold", get_cmd("quit").key_str()), ("", " to quit")]],
        )
