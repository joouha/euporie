"""Contain a container for the cell output area."""

from __future__ import annotations

import logging
from pathlib import PurePath
from typing import TYPE_CHECKING, NamedTuple

from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.containers import DynamicContainer
from prompt_toolkit.layout.dimension import Dimension

from euporie.core.app.current import get_app
from euporie.core.commands import add_cmd
from euporie.core.convert.registry import find_route
from euporie.core.filters import pager_has_focus
from euporie.core.key_binding.registry import (
    load_registered_bindings,
    register_bindings,
)
from euporie.core.layout.containers import DummyContainer, HSplit
from euporie.core.layout.decor import Line
from euporie.core.widgets.cell_outputs import CellOutput, CellOutputDataElement
from euporie.core.widgets.display import Display
from euporie.core.widgets.layout import Box

if TYPE_CHECKING:
    from typing import Any

    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import AnyDimension

    from euporie.core.widgets.cell_outputs import CellOutputElement, OutputParent

log = logging.getLogger(__name__)


class PagerState(NamedTuple):
    """A named tuple which describes the state of a pager."""

    code: str
    cursor_pos: int
    data: dict


class PagerOutputDataElement(CellOutputDataElement):
    """A cell output element which display data."""

    def __init__(
        self,
        mime: str,
        data: dict[str, Any],
        metadata: dict,
        parent: OutputParent | None,
    ) -> None:
        """Create a new data output element instance.

        Args:
            mime: The mime-type of the data to display
            data: The data to display
            metadata: Any metadata relating to the data
            parent: The parent container the output-element is attached to
        """
        from euporie.core.convert.datum import Datum
        from euporie.core.convert.formats import BASE64_FORMATS
        from euporie.core.convert.mime import MIME_FORMATS

        # Get internal format
        format_ = "ansi"
        mime_path = PurePath(mime)
        for mime_type, data_format in MIME_FORMATS.items():
            if mime_path.match(mime_type):
                if data_format in BASE64_FORMATS:
                    data_format = f"base64-{data_format}"
                if find_route(data_format, "ft") is not None:
                    format_ = data_format
                    break

        self._datum = Datum(data, format_)
        self.container = Display(
            self._datum,
            focusable=True,
            focus_on_click=True,
            wrap_lines=True,
            always_hide_cursor=True,
            style="class:pager",
            scrollbar_autohide=False,
            dont_extend_height=True,
            height=lambda: Dimension(
                max=int(get_app().output.get_size().rows // 3.5),
            ),
        )


class PagerOutput(CellOutput):
    """Display pager output."""

    def make_element(self, mime: str) -> CellOutputElement:
        """Create a container for the pager output mime-type if it doesn't exist.

        Args:
            mime: The mime-type to make the container for

        Returns:
            A :class:`PagerOutputDataElement` container for the currently selected mime-type.
        """
        self._selected_mime = None
        return PagerOutputDataElement(
            mime=self.selected_mime,
            data=self.data[self.selected_mime],
            metadata=self.json.get("metadata", {}).get(self.selected_mime, {}),
            parent=self.parent,
        )


class Pager:
    """Interactive help pager.

    A pager which displays information at the bottom of a tab.

    """

    def __init__(self, height: AnyDimension | None = None) -> None:
        """Create a new page instance."""
        self._state: PagerState | None = None
        self.visible = Condition(
            lambda: self.state is not None and bool(self.state.data)
        )
        self.output = PagerOutput({}, None)

        inner = HSplit(
            [
                Line(
                    char="▅",
                    height=1,
                    collapse=False,
                    style="class:pager.border",
                ),
                Box(self.output, padding=0, padding_left=1),
            ],
            style="class:pager",
            key_bindings=load_registered_bindings(
                "euporie.core.widgets.pager:Pager",
                config=get_app().config,
            ),
            height=height,
        )
        dummy = DummyContainer()
        self.container = DynamicContainer(lambda: inner if self.visible() else dummy)

    def focus(self) -> None:
        """Focus the pager."""
        get_app().layout.focus(self)

    def hide(self) -> None:
        """Clear and hide the pager."""
        if self.visible():
            self.state = None
            # Focus previous control if this pager has focus
            layout = get_app().layout
            if layout.has_focus(self):
                previous_control = layout.previous_control
                if previous_control in layout.find_all_controls():
                    layout.focus(previous_control)

    @property
    def state(self) -> PagerState | None:
        """Return the pager's current state."""
        return self._state

    @state.setter
    def state(self, new: PagerState | None) -> None:
        """Set the pager's current state."""
        self._state = new
        if new is not None:
            self.output.json = {"data": new.data}
            self.output.update()
        get_app().invalidate()

    def __pt_container__(self) -> AnyContainer:
        """Return the pager container."""
        return self.container

    # ################################## Commands #####################################

    @staticmethod
    @add_cmd(filter=pager_has_focus)
    def _close_pager() -> None:
        """Close the pager."""
        app = get_app()
        if app.pager is not None:
            app.pager.hide()

    # ################################# Keybindings ###################################

    register_bindings(
        {
            "euporie.core.widgets.pager:Pager": {
                "close-pager": ["escape", "q"],
            }
        }
    )
