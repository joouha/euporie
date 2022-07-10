"""Contains a container for the cell output area."""

import logging
from pathlib import PurePath
from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    HSplit,
)
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import Box

from euporie.core.app import get_app
from euporie.core.commands import add_cmd
from euporie.core.convert.base import MIME_FORMATS, find_route
from euporie.core.filters import pager_has_focus
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.widgets.cell_outputs import CellOutput, CellOutputDataElement
from euporie.core.widgets.decor import Line
from euporie.core.widgets.display import Display

if TYPE_CHECKING:
    from typing import Any, Dict, Optional

    from euporie.core.widgets.cell_outputs import CellOutputElement, OutputParent

log = logging.getLogger(__name__)


PagerState = NamedTuple(
    "PagerState",
    [("code", str), ("cursor_pos", int), ("response", dict)],
)


class PagerOutputDataElement(CellOutputDataElement):
    """A cell output element which display data."""

    def __init__(
        self,
        mime: "str",
        data: "Dict[str, Any]",
        metadata: "Dict",
        parent: "Optional[OutputParent]",
    ) -> "None":
        """Create a new data output element instance.

        Args:
            mime: The mime-type of the data to display
            data: The data to display
            metadata: Any metadata relating to the data
            parent: The parent container the output-element is attached to
        """
        # Get internal format
        format_ = "ansi"
        mime_path = PurePath(mime)
        for format_mime, mime_format in MIME_FORMATS.items():
            if mime_path.match(format_mime):
                if find_route(mime_format, "formatted_text") is not None:
                    format_ = mime_format
                    break

        self.container = Display(
            data=data,
            format_=format_,
            focusable=True,
            focus_on_click=True,
            show_scrollbar=True,
            wrap_lines=True,
            always_hide_cursor=True,
            style="class:pager",
        )


class PagerOutput(CellOutput):
    """Display pager output."""

    @property
    def container(self) -> "CellOutputElement":
        """Creates a container for the pager output mime-type if it doesn't exist.

        Returns:
            A :class:`PagerOutputDataElement` container for the currently selected mime-type.
        """
        if self.selected_mime not in self._containers:
            self._containers[self.selected_mime] = PagerOutputDataElement(
                mime=self.selected_mime,
                data=self.data[self.selected_mime],
                metadata=self.json.get("metadata", {}).get(self.selected_mime, {}),
                parent=self.parent,
            )
        return self._containers[self.selected_mime]


class Pager:
    """A pager which displays information at the bottom of a tab."""

    def __init__(self) -> "None":
        """Create a new page instance."""
        self._state: "Optional[PagerState]" = None
        self.visible = Condition(
            lambda: self.state is not None and bool(self.state.response.get("found"))
        )
        self.output = PagerOutput({}, None)
        self.container = ConditionalContainer(
            HSplit(
                [
                    Line(
                        height=1,
                        collapse=False,
                        style="class:pager.border",
                    ),
                    Box(
                        DynamicContainer(lambda: self.output),
                        padding=0,
                        padding_left=1,
                    ),
                ],
                height=Dimension(min=5, max=15),
                style="class:pager",
                key_bindings=load_registered_bindings("widgets.pager"),
            ),
            filter=self.visible,
        )

    def focus(self) -> "None":
        """Focus the pager."""
        get_app().layout.focus(self)

    def hide(self) -> "None":
        """Clear and hide the pager."""
        self.state = None
        layout = get_app().layout
        previous_control = layout.previous_control
        if previous_control in layout.find_all_controls():
            layout.focus(previous_control)

    @property
    def state(self) -> "Optional[PagerState]":
        """Return the pager's current state."""
        return self._state

    @state.setter
    def state(self, new: "Optional[PagerState]") -> "None":
        """Set the pager's current state."""
        self._state = new
        if new is not None:
            self.output.json = new.response

    def __pt_container__(self):
        """Return the pager container."""
        return self.container


@add_cmd(filter=pager_has_focus)
def close_pager() -> "None":
    """Close the pager."""
    app = get_app()
    if app.pager is not None:
        app.pager.hide()


register_bindings(
    {
        "widgets.pager": {
            "close-pager": ["escape", "q"],
        }
    }
)
