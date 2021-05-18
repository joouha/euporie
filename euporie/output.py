# -*- coding: utf-8 -*-
"""Container class for cell output."""
from __future__ import annotations

from pathlib import PurePath
from typing import TYPE_CHECKING, Any, Optional, Union

from prompt_toolkit.layout import Container, Window, to_container
from prompt_toolkit.layout.controls import (
    FormattedTextControl,
    GetLinePrefixCallable,
    UIControl,
)
from prompt_toolkit.widgets import Label
from rich.markdown import Markdown

from euporie import mdtable  # noqa E401
from euporie.config import config
from euporie.control import HTMLControl, ImageControl, RichControl, SVGControl
from euporie.text import ANSI

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_bindings import KeyBindingsBase
    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.dimension import Dimension
    from prompt_toolkit.layout.mouse_handlers import MouseHandlers
    from prompt_toolkit.layout.screen import Screen, WritePosition

    from euporie.cell import Cell

BLING_SCORES = {
    "image/*": 0,
    "text/html": 1,
    "text/x-markdown": 2,
    "text/x-python-traceback": 3,
    "text/stderr": 4,
    "text/*": 5,
    "*": 6,
}


def calculate_bling(item: tuple[str, str]) -> int:
    """Scores the richness of mime output types."""
    mime, _ = item
    for bling_path, score in BLING_SCORES.items():
        if PurePath(mime).match(bling_path):
            return score
    else:
        return 999


class Output:
    """A prompt-toolkit compatible container for rendered cell outputs.

    This is a Container / Control hyrid, as `Output.content` can be either.
    """

    def __init__(
        self, index: "int", json: "dict[str, Any]", parent: "Optional[Cell]" = None
    ):
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
        self.content: AnyContainer

        control: UIControl

        # Sort data first so there is more bling first
        for mime, datum in sorted(self.data.items(), key=calculate_bling):

            mime_path = PurePath(mime)

            if mime_path.match("image/svg+xml"):
                control = SVGControl(
                    datum,
                    render_args=dict(cell=self.parent, output_index=index),
                )
                if control.renderer:
                    self.content = Window(control)
                    break

            if mime_path.match("image/*"):
                control = ImageControl(
                    datum,
                    render_args=dict(cell=self.parent, output_index=index),
                )
                if control.renderer:
                    self.content = Window(control)
                    break

            if mime_path.match("text/html"):
                control = HTMLControl(datum)
                if control.renderer:
                    self.content = Window(control)
                    break
                else:
                    continue  # Use plain text rendering instead

            if mime_path.match("text/x-markdown"):
                control = RichControl(
                    Markdown(
                        datum,
                        code_theme=str(config.pygments_style),
                        inline_code_theme=str(config.pygments_style),
                    )
                )
                self.content = Window(control)
                break

            if mime_path.match("text/x-python-traceback"):
                control = FormattedTextControl(ANSI(datum.rstrip()))
                self.content = Window(control)
                break

            if mime_path.match("text/stderr"):
                control = FormattedTextControl(ANSI(datum.rstrip()))
                self.content = Window(control, wrap_lines=True, style="fg:red")
                break

            if mime_path.match("text/*"):
                # Use formatted text so ansi colour codes are displayed as colours
                control = FormattedTextControl(ANSI(datum.rstrip()))
                self.content = Window(control, wrap_lines=True)
                break

        else:
            datum = sorted(self.data.items(), key=calculate_bling)[-1][1]
            self.content = Label(str(datum).rstrip())

    @property
    def data(self) -> "dict[str, str]":
        """Return dictionary of mime types and data for this output.

        This generates similarly structured data objects for markdown cells and text
        output streams.
        """
        output_type = self.json.get("output_type", "unknown")
        if output_type == "stream":
            return {f'text/{self.json.get("name")}': self.json.get("text", "")}
        elif output_type == "error":
            return {
                "text/x-python-traceback": "\n".join(self.json.get("traceback", ""))
            }
        else:
            return self.json.get("data", {})

    def get_key_bindings(self) -> "Optional[KeyBindingsBase]":
        """Wrap `get_key_bindings` method of `self.content`."""
        return to_container(self.content).get_key_bindings()

    def get_children(self) -> "list[Container]":
        """Wrap `get_children` method of `self.content`."""
        return to_container(self.content).get_children()

    def preferred_width(
        self, max_available_width: "Union[int]"
    ) -> "Optional[Union[int, Dimension]]":
        """Wrap `preferred_width` method of `self.content`."""
        return to_container(self.content).preferred_width(max_available_width)

    def preferred_height(
        self,
        width: "int",
        max_available_height: "int",
        wrap_lines: "Optional[bool]" = None,
        get_line_prefix: "Optional[GetLinePrefixCallable]" = None,
    ) -> "Union[int, Dimension]":
        """Wrap `preferred_height` method of `self.content`.

        Some argument processing is needed here to work with Controls and Containers.
        """
        args: "list[Any]" = [width, max_available_height]
        if wrap_lines:
            args.append(wrap_lines)
        if get_line_prefix:
            args.append(get_line_prefix)
        return to_container(self.content).preferred_height(*args)

    def write_to_screen(
        self,
        screen: "Screen",
        mouse_handlers: "MouseHandlers",
        write_position: "WritePosition",
        parent_style: "str",
        erase_bg: "bool",
        z_index: "Optional[int]",
    ) -> None:
        """Wrap `write_to_screen` method of `self.content`."""
        return to_container(self.content).write_to_screen(
            screen, mouse_handlers, write_position, parent_style, erase_bg, z_index
        )

    def reset(self) -> None:
        """Wrap `reset` method of `self.content`."""
        return to_container(self.content).reset()

    def __pt_container__(self) -> Container:
        """Wrap `__pt_container__` method of `self.content`."""
        return to_container(self.content)
