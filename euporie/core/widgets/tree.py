"""Defines a tree-view widget."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from typing import Any, Optional

    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone


class JsonView:
    """A JSON-view contiainer."""

    def __init__(
        self, data: "Any", title: "Optional[str]" = None, expanded: "bool" = True
    ) -> "None":
        """Create a new instance."""
        if title is None:
            self.title = "root"
        else:
            self.title = title
        self.expanded = expanded

        self.children = []
        self.value_style = ""
        self.value = ""

        if isinstance(data, list):
            data = dict(enumerate(data))
            self.value = f"[] {len(data)} items"
            self.value_style = "class:pygments.comment"
        if isinstance(data, dict):
            self.value = f"{{}} {len(data)} items"
            self.value_style = "class:pygments.comment"
            self.children = [
                JsonView(data=value, title=key, expanded=expanded)
                for key, value in data.items()
            ]
        else:
            self.value = f"{data!r}"
            self.value_style = {
                str: "class:pygments.literal.string",
                int: "class:pygments.literal.number",
                float: "class:pygments.literal.number",
                bool: "class:pygments.keyword.constant",
            }.get(type(data), "")

        self.container = HSplit(
            [
                Window(
                    FormattedTextControl(self.format_title),
                    dont_extend_height=True,
                ),
                ConditionalContainer(
                    VSplit(
                        [
                            Window(
                                width=2,
                                char="  ",
                                style="",
                            ),
                            HSplit(self.children),
                        ]
                    ),
                    filter=Condition(lambda: self.expanded and bool(self.children)),
                ),
            ],
            style="class:tree",
        )

    def toggle(self, mouse_event: "MouseEvent") -> "NotImplementedOrNone":
        """Toggle the expansion state."""
        if (
            mouse_event.button == MouseButton.LEFT
            and mouse_event.event_type == MouseEventType.MOUSE_UP
        ):
            self.expanded = not self.expanded
            return None
        return NotImplemented

    def format_title(self) -> "StyleAndTextTuples":
        """Return the tree node toggle and title."""
        return cast(
            "StyleAndTextTuples",
            [
                ("class:pygments.operator", "⮟" if self.expanded else "⮞", self.toggle)
                if self.children
                else ("", " ", self.toggle),
                ("", " ", self.toggle),
                ("class:pygments.keyword", f"{self.title}", self.toggle),
                ("class:pygments.punctuation", ": ", self.toggle),
                (self.value_style, self.value, self.toggle),
            ],
        )

    def __pt_container__(self):
        return self.container
