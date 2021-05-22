# -*- coding: utf-8 -*-
"""Container class for cell output."""
from __future__ import annotations

from pathlib import PurePath
from typing import TYPE_CHECKING, Any

from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import FormattedTextControl, UIControl
from prompt_toolkit.widgets import Label
from rich.markdown import Markdown

from euporie import mdtable  # noqa E401
from euporie.config import config
from euporie.control import HTMLControl, ImageControl, RichControl, SVGControl
from euporie.text import ANSI

if TYPE_CHECKING:
    from prompt_toolkit.layout.containers import AnyContainer

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
        self.content: AnyContainer

        control: UIControl

        # Sort data first so there is more bling first
        for mime, datum in sorted(self.data.items(), key=calculate_bling):

            mime_path = PurePath(mime)

            if mime_path.match("image/svg+xml"):
                control = SVGControl(
                    datum,
                    render_args=dict(
                        cell=self.parent,
                        cell_index=self.parent.index,
                        output_index=index,
                    ),
                )
                if control.renderer:
                    self.content = Window(control)
                    break

            if mime_path.match("image/*"):
                control = ImageControl(
                    datum,
                    render_args=dict(
                        cell=self.parent,
                        cell_index=self.parent.index,
                        output_index=index,
                    ),
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
                self.content = Window(
                    RichControl(
                        Markdown(
                            datum,
                            code_theme=str(config.pygments_style),
                            inline_code_theme=str(config.pygments_style),
                        )
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
                    wrap_lines=True,
                    style="fg:red" if mime_path.name == "stderr" else "",
                )
                break

            if mime_path.match("text/*"):
                self.content = Window(
                    FormattedTextControl(datum.rstrip()), wrap_lines=True
                )
                break

        else:
            datum = sorted(self.data.items(), key=calculate_bling)[-1][1]
            self.content = Label(str(datum).rstrip())

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
