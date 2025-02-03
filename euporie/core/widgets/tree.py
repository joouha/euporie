"""Define a tree-view widget."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from typing import Any

    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.key_binding.key_bindings import NotImplementedOrNone


class JsonView:
    """A JSON-view container."""

    def __init__(
        self, data: Any, title: str | None = None, expanded: bool = False
    ) -> None:
        """Create a new instance."""
        self.data = data
        self.title = "root" if title is None else title
        self.start_expanded = expanded
        self._toggled_paths: set[tuple[str, ...]] = set()
        self.container = Window(
            FormattedTextControl(self._get_formatted_text, focusable=True),
            style="class:tree",
        )

    def _get_value_style(self, value: Any) -> str:
        """Return the style for a given value type."""
        return {
            str: "class:pygments.literal.string",
            int: "class:pygments.literal.number",
            float: "class:pygments.literal.number",
            bool: "class:pygments.keyword.constant",
        }.get(type(value), "")

    def _format_value(self, value: Any) -> tuple[str, str]:
        """Return the formatted value and its style."""
        if isinstance(value, (list, dict)):
            length = len(value)
            if isinstance(value, list):
                return f" [] {length} items", "class:pygments.comment"
            return f" {{}} {length} items", "class:pygments.comment"
        return repr(value), self._get_value_style(value)

    def _get_formatted_text(self) -> StyleAndTextTuples:
        """Generate the complete tree view as formatted text."""
        result: StyleAndTextTuples = []
        toggled_paths = self._toggled_paths
        start_expanded = self.start_expanded
        toggle = self._toggle
        format_value = self._format_value

        def format_node(
            data: Any, path: tuple[str, ...], indent: int, key: str
        ) -> None:
            is_expanded = (path in toggled_paths) ^ start_expanded
            has_children = isinstance(data, (dict, list))
            mouse_handler = partial(toggle, path=path)

            value, style = format_value(data)
            row: StyleAndTextTuples = [
                # Add indentation
                ("", "  " * indent),
                # Add toggle symbol
                (
                    ("class:pygments.operator", "▼" if is_expanded else "▶")
                    if has_children
                    else ("", " ")
                ),
                ("", " "),
                ("class:pygments.keyword", str(key)),
                ("class:pygments.punctuation", ": "),
                (style, value),
                ("", "\n"),
            ]

            # Apply mouse_handler to rows with children
            if has_children:
                row = [(style, text, mouse_handler) for (style, text, *_) in row]

            result.extend(row)

            if is_expanded and has_children:
                if isinstance(data, list):
                    data = {str(i): v for i, v in enumerate(data)}

                for k, v in data.items():
                    new_path = (*path, str(k)) if path else (str(k),)
                    format_node(v, new_path, indent + 1, k)

        format_node(self.data, (), 0, self.title)
        return result

    def _toggle(
        self, mouse_event: MouseEvent, path: tuple[str, ...]
    ) -> NotImplementedOrNone:
        """Toggle the expansion state of a node."""
        if (
            mouse_event.button == MouseButton.LEFT
            and mouse_event.event_type == MouseEventType.MOUSE_UP
        ):
            if path in self._toggled_paths:
                self._toggled_paths.remove(path)
            else:
                self._toggled_paths.add(path)
            return None
        return NotImplemented

    def __pt_container__(self) -> Window:
        """Return the tree-view container's content."""
        return self.container
