"""Container class for cell output."""

from __future__ import annotations

import io
import logging
from pathlib import PurePath
from typing import TYPE_CHECKING, cast

import imagesize  # type: ignore
from prompt_toolkit.filters import Condition, to_filter
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.containers import to_container
from prompt_toolkit.layout.controls import FormattedTextControl

from euporie.app import get_app
from euporie.convert.base import convert
from euporie.output.control import FormatterControl
from euporie.text import ANSI

if TYPE_CHECKING:
    from typing import Any, Optional, Protocol

    from prompt_toolkit.layout.containers import AnyContainer
    from prompt_toolkit.layout.mouse_handlers import MouseHandlers
    from prompt_toolkit.layout.screen import Screen, WritePosition

    from euporie.graphics.base import TerminalGraphic

    class ParentContainer(Protocol):
        """A type for a parent container which remembers it's write position."""

        last_write_position: "Optional[WritePosition]"


log = logging.getLogger(__name__)

BLING_SCORES = {
    "image/*": 0,
    "text/html": 1,
    "text/latex": 1,
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


def get_dims(
    data: "Any", format_: "str", fg: "Optional[str]" = None, bg: "Optional[str]" = None
) -> "tuple[Optional[int], Optional[int]]":
    """Get the dimensions of an image.

    Foreground and background color are set at this point if they are available, as
    data conversion outputs are cached and re-used.

    Args:
        data: The data to check the dimensions of
        format_: The current format of the data
        fg: The desired foreground color of the data
        bg: The desired background color of the data

    Returns:
        A tuple of the data's width in terminal columns and its aspect ratio, when
            converted to a image.

    """
    cols, aspect = None, None
    if format_ not in {"png", "svg", "jpg", "gif", "tiff"}:
        try:
            data = convert(data, from_=format_, to="png", fg=fg, bg=bg)
        except NotImplementedError:
            pass
    if isinstance(data, str):
        data = data.encode()
    px, py = imagesize.get(io.BytesIO(data))
    if px > 0:
        cell_px, cell_py = get_app().term_info.cell_size_px
        cols = int(px // cell_px)
        aspect = (py / cell_py) / (px / cell_px)
    return cols, aspect


class CellOutput:
    """A container for rendered cell outputs."""

    def __init__(self, json: "dict[str, Any]"):
        """Instantiate an Output container object.

        Args:
            json: A reference to the notebook json branch corresponding to this output

        """
        self.json = json

        self.window: AnyContainer = OutputWindow()
        self.graphic = None

        fg_color = get_app().term_info.foreground_color.value
        bg_color = {"light": "#FFFFFF", "dark": "#000000"}.get(
            json.get("metadata", {}).get("needs_background")
        )

        # Sort data first so there is more bling first
        for mime, datum in sorted(self.data.items(), key=_calculate_bling):
            mime_path = PurePath(mime)

            # TODO - force image dimensions based on metadata, e.g.:
            # metadata": {
            #    "image/jpeg": {
            #        "height": 200,
            #        "width": 100
            #    }
            # }

            format_ = None
            if mime_path.match("image/svg+xml"):
                format_ = "svg"
            elif mime_path.match("image/*"):
                format_ = "base64"
            elif mime_path.match("text/html"):
                format_ = "html"
            elif mime_path.match("text/latex"):
                format_ = "latex"
            elif mime_path.match("text/x-markdown") or mime_path.match("text/markdown"):
                format_ = "markdown"

            if format_ is not None:

                self.graphic = get_app().graphics_renderer.add(
                    datum,
                    format_=format_,
                    visible=~Condition(self.window.is_obscured),
                    fg_color=fg_color,
                    bg_color=bg_color,
                )

                cols, aspect = get_dims(datum, format_, fg_color, bg_color)

                self.window.content = FormatterControl(
                    datum,
                    format_=format_,
                    graphic=self.graphic,
                    fg_color=fg_color,
                    bg_color=bg_color,
                    max_cols=cols,
                    aspect=aspect,
                )
                break
            elif mime_path.match("text/x-python-traceback"):
                self.window.content = FormattedTextControl(ANSI(datum.rstrip()))
                break
            elif mime_path.match("stream/std*"):
                self.window.content = FormattedTextControl(ANSI(datum.rstrip()))
                self.window.wrap_lines = to_filter(False)
                self.window.style = "fg:red" if mime_path.name == "stderr" else ""
                break
            elif mime_path.match("text/*"):
                self.window.content = FormattedTextControl(datum.rstrip())
                self.window.wrap_lines = to_filter(True)
                break
        else:
            datum = sorted(self.data.items(), key=_calculate_bling)[-1][1]
            self.window.content = FormattedTextControl(str(datum).rstrip())

    @property
    def data(self) -> "dict[str, str]":
        """Return dictionary of mime types and data for this output.

        This generates similarly structured data objects for markdown cells and text
        output streams.

        Returns:
            JSON dictionary mapping mimes type to representation data.

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
        return self.window


class OutputWindow(Window):
    """A window to contain a formatted control and a terminal graphics."""

    def __init__(
        self,
        *args: "Any",
        graphic: "Optional[TerminalGraphic]" = None,
        **kwargs: "Any",
    ):
        """Create a new output window."""
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
        """Draw the window's contents to the screen.

        This also updates the location of the control's graphic if it has one.

        Args:
            screen: The :class:`~prompt_toolkit.layout.screen.Screen` class to which
                the output has to be drawn.
            mouse_handlers: :class:`prompt_toolkit.layout.mouse_handlers.MouseHandlers`.
            write_position: A :class:`prompt_toolkit.layout.screen.WritePosition` object
                defining where this container should be drawn.
            erase_bg: If true, the background will be erased prior to drawing.
            parent_style: Style string to pass to the :class:`.Window` object. This will
                be applied to all content of the windows. :class:`.VSplit` and
                :class:`prompt_toolkit.layout.containers.HSplit` can use it to pass
                their style down to the windows that they contain.
            z_index: Used for propagating z_index from parent to child.

        """
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

        # Set graphic position
        if isinstance(self.content, FormatterControl):
            if self.content.graphic is not None:
                self.content.graphic.set_position(
                    write_position.xpos, write_position.ypos
                )

    def is_obscured(self) -> "bool":
        """Determine if the control is partially obscured."""
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
    """Find the first parent of a container with a ``last_write_position`` attribute.

    Args:
        containers: A list of nested containers to find the parent of. Pass a single
            container instance to find a parent with a known write position.

    Returns:
        A parent container with a :py:attr:`last_write_position` attribute, if one is
            found

    """
    parent = get_app().layout.get_parent(to_container(containers[0]))
    if parent is None:
        return None
    elif hasattr(parent, "last_write_position"):
        return cast("ParentContainer", parent)
    else:
        return get_parent(parent, *containers)
