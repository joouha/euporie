"""Container class for cell output."""

from __future__ import annotations

import logging
from pathlib import PurePath
from typing import TYPE_CHECKING, cast

from prompt_toolkit.filters import Condition
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.containers import to_container
from prompt_toolkit.layout.controls import FormattedTextControl

from euporie.app import get_app
from euporie.output.control import (
    HTMLControl,
    ImageControl,
    LatexControl,
    MarkdownControl,
    OutputControl,
    SVGControl,
)
from euporie.text import ANSI

if TYPE_CHECKING:
    from typing import Any, Optional, Protocol

    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.controls import UIControl
    from prompt_toolkit.layout.mouse_handlers import MouseHandlers
    from prompt_toolkit.layout.screen import Screen, WritePosition

    from euporie.cell import Cell
    from euporie.graphics.base import TerminalGraphic

    class ParentContainer(Protocol):
        last_write_position: "Optional[WritePosition]"


__all__ = ["Output"]

log = logging.getLogger(__name__)

BLING_SCORES = {
    "image/*": 0,
    "text/html": 1,
    "text/markdown": 2,
    "text/x-markdown": 2,
    "text/x-python-traceback": 3,
    "text/stderr": 4,
    "text/*": 5,
    "*": 6,
}


def _calculate_bling(item: tuple[str, str]) -> int:
    """Scores the richness of mime output types."""
    mime, _ = item
    for bling_path, score in BLING_SCORES.items():
        if PurePath(mime).match(bling_path):
            return score
    else:
        return 999


class Output:
    """A prompt-toolkit compatible container for rendered cell outputs."""

    def __init__(self, index: "int", json: "dict[str, Any]", parent: "Cell"):
        """Instantiate an Output container object.

        Args:
            index: The position of this output in the list of the parent cell's outputs
            json: A reference to the notebook json branch corresponding to this output
            parent: A reference to the parent cell to which this output belongs
        """
        self.index = index
        self.json = json
        self.parent = parent
        self.style = ""
        self.content: AnyContainer = Window()

        control: "UIControl"

        bg_color = {"light": "#FFFFFF", "dark": "#000000"}.get(
            json.get("metadata", {}).get("needs_background")
        )
        # TODO - force image dimensions based on metadata, e.g.:
        # metadata": {
        #    "image/jpeg": {
        #        "height": 200,
        #        "width": 100
        #    }
        # }

        # Sort data first so there is more bling first
        for mime, datum in sorted(self.data.items(), key=_calculate_bling):
            mime_path = PurePath(mime)

            if mime_path.match("image/svg+xml"):
                window = GraphicsWindow()
                graphic = get_app().graphics_renderer.add(
                    "", visible=~Condition(window.is_obscured), bg_color=bg_color
                )
                control = SVGControl(
                    datum,
                    graphic=graphic,
                    bg_color=bg_color,
                )
                window.content = control
                self.content = window
                break

            if mime_path.match("image/*"):

                window = GraphicsWindow()
                graphic = get_app().graphics_renderer.add(
                    datum, visible=~Condition(window.is_obscured), bg_color=bg_color
                )
                control = ImageControl(
                    datum,
                    graphic=graphic,
                    bg_color=bg_color,
                )
                window.content = control
                self.content = window
                break

            if mime_path.match("text/html"):
                control = HTMLControl(datum)
                if control.renderer:
                    self.content = Window(control)
                    break
                else:
                    continue  # Use plain text rendering instead

            if mime_path.match("text/latex"):
                control = LatexControl(datum)
                if control.renderer:
                    self.content = Window(control)
                    break
                else:
                    continue  # Use plain text rendering instead

            if (
                mime_path.match("text/x-markdown")
                or mime_path.match("text/markdown")
                or mime_path.match("text/latex")
            ):

                self.content = Window(
                    MarkdownControl(
                        datum,
                    )
                )
                break

            if mime_path.match("text/x-python-traceback"):
                self.content = Window(FormattedTextControl(ANSI(datum.rstrip())))
                break

            if mime_path.match("stream/std*"):
                # Parse ansi for text streams
                self.content = Window(
                    FormattedTextControl(ANSI(datum.rstrip())),
                    wrap_lines=False,
                    style="fg:red" if mime_path.name == "stderr" else "",
                )
                break

            if mime_path.match("text/*"):
                self.content = Window(
                    FormattedTextControl(datum.rstrip()), wrap_lines=True
                )
                break

        else:
            datum = sorted(self.data.items(), key=_calculate_bling)[-1][1]
            self.content = Window(FormattedTextControl(str(datum).rstrip()))

    @property
    def data(self) -> "dict[str, str]":
        """Return dictionary of mime types and data for this output.

        This generates similarly structured data objects for markdown cells and text
        output streams.

        Returns:
            JSON dictionary mapping mimes type to representaion data.

        """
        output_type = self.json.get("output_type", "unknown")
        if output_type == "stream":
            return {f'stream/{self.json.get("name")}': self.json.get("text", "")}
        elif output_type == "error":
            return {
                "text/x-python-traceback": "\n".join(self.json.get("traceback", ""))
            }
        else:
            return self.json.get("data", {})

    def __pt_container__(self) -> "AnyContainer":
        """Return the content of this output."""
        return self.content


class GraphicsWindow(Window):
    def __init__(
        self,
        *args: "Any",
        graphic: "Optional[TerminalGraphic]" = None,
        **kwargs: "Any",
    ):
        super().__init__(*args, **kwargs)
        self.parent: "Optional[ParentContainer]" = None
        self.write_position: "Optional[WritePosition]" = None

    def write_to_screen(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        write_position: "WritePosition",
        parent_style: "str",
        erase_bg: "bool",
        z_index: "Optional[int]",
    ) -> "None":
        super().write_to_screen(
            screen,
            mouse_handlers,
            write_position,
            parent_style,
            erase_bg,
            z_index,
        )
        self.write_position = write_position
        # TODO - set cropping dimensions for graphic
        if isinstance(self.content, OutputControl):
            if self.content.graphic is not None:
                self.content.graphic.set_position(
                    write_position.xpos, write_position.ypos
                )
                self.content.graphic.set_size(
                    self.content.renderer.width,
                    self.content.renderer.height,
                )

    def is_obscured(self) -> "bool":
        if self not in get_app().layout.visible_windows:
            return True
        if self.parent is None:
            self.parent = get_parent(self)
        if (
            self.parent is not None
            and self.parent.last_write_position is not None
            and self.write_position is not None
        ):
            wp = self.write_position
            pwp = self.parent.last_write_position
            assert pwp is not None
            if wp.ypos < pwp.ypos or pwp.ypos + pwp.height < wp.ypos + wp.height:
                return True
        return False


def get_parent(*containers: "AnyContainer") -> "Optional[ParentContainer]":
    parent = get_app().layout.get_parent(to_container(containers[0]))
    if parent is None:
        return None
    elif hasattr(parent, "last_write_position"):
        return cast("ParentContainer", parent)
    else:
        return get_parent(parent, *containers)
