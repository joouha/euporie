"""Define controls for display of terminal graphics."""

from __future__ import annotations

import logging
import weakref
from abc import ABCMeta, abstractmethod
from math import ceil, floor
from typing import TYPE_CHECKING

from prompt_toolkit.cache import FastDictCache, SimpleCache
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters.base import Condition
from prompt_toolkit.filters.utils import to_filter
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.formatted_text.utils import split_lines
from prompt_toolkit.layout.containers import Float, Window
from prompt_toolkit.layout.controls import GetLinePrefixCallable, UIContent, UIControl
from prompt_toolkit.layout.mouse_handlers import MouseHandlers
from prompt_toolkit.layout.screen import Char, WritePosition
from prompt_toolkit.utils import get_cwidth

from euporie.core.app.current import get_app
from euporie.core.convert.datum import Datum
from euporie.core.convert.registry import find_route
from euporie.core.data_structures import DiInt
from euporie.core.filters import has_float, in_mplex
from euporie.core.ft.utils import _ZERO_WIDTH_FRAGMENTS
from euporie.core.io import passthrough
from euporie.core.layout.scroll import BoundedWritePosition

if TYPE_CHECKING:
    from typing import Any, Callable, ClassVar

    from prompt_toolkit.filters import FilterOrBool
    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.layout.screen import Screen


log = logging.getLogger(__name__)


class GraphicControl(UIControl, metaclass=ABCMeta):
    """A base-class for display controls which render terminal graphics."""

    def __init__(
        self,
        datum: Datum,
        scale: float = 0,
        bbox: DiInt | None = None,
    ) -> None:
        """Initialize the graphic control."""
        self.app = get_app()
        self.datum = datum
        self.scale = scale
        self.bbox = bbox or DiInt(0, 0, 0, 0)
        self.rendered_lines: list[StyleAndTextTuples] = []
        self._content_cache: SimpleCache = SimpleCache(maxsize=50)
        self._format_cache: SimpleCache = SimpleCache(maxsize=50)

    def preferred_width(self, max_available_width: int) -> int | None:
        """Return the width of the rendered content."""
        cols, _aspect = self.datum.cell_size()
        return min(cols, max_available_width) if cols else max_available_width

    def preferred_height(
        self,
        width: int,
        max_available_height: int,
        wrap_lines: bool,
        get_line_prefix: GetLinePrefixCallable | None,
    ) -> int:
        """Return the number of lines in the rendered content."""
        cols, aspect = self.datum.cell_size()
        if aspect:
            return ceil(min(width, cols) * aspect)
        self.rendered_lines = self.get_rendered_lines(width, max_available_height)
        return len(self.rendered_lines)

    @abstractmethod
    def convert_data(self, wp: WritePosition) -> str:
        """Convert datum to required format."""
        return ""

    @abstractmethod
    def get_rendered_lines(
        self, visible_width: int, visible_height: int, wrap_lines: bool = False
    ) -> list[StyleAndTextTuples]:
        """Render the output data."""
        return []

    def create_content(self, width: int, height: int) -> UIContent:
        """Generate rendered output at a given size.

        Args:
            width: The desired output width
            height: The desired output height

        Returns:
            `UIContent` for the given output size.

        """

        def get_content() -> dict[str, Any]:
            rendered_lines = self.get_rendered_lines(width, height)
            self.rendered_lines = rendered_lines[:]
            line_count = len(rendered_lines)

            def get_line(i: int) -> StyleAndTextTuples:
                # Return blank lines if the renderer expects more content than we have
                line = []
                if i < line_count:
                    line += rendered_lines[i]
                # Add a space at the end, because that is a possible cursor position.
                # This is what PTK does, and fixes a nasty bug which took me ages to
                # track down the source of, where scrolling would stop working when the
                # cursor was on an empty line.
                line += [("", " ")]
                return line

            return {
                "get_line": get_line,
                "line_count": line_count,
                "menu_position": Point(0, 0),
            }

        # Re-render if the image width changes, or the terminal character size changes
        key = (
            width,
            height,
            self.app.color_palette,
            self.app.cell_size_px,
            self.bbox,
        )
        return UIContent(
            **self._content_cache.get(key, get_content),
        )

    def hide(self) -> None:
        """Hide the graphic from show."""

    def close(self) -> None:
        """Remove the displayed object entirely."""
        if not self.app.leave_graphics():
            self.hide()


class SixelGraphicControl(GraphicControl):
    """A graphic control which displays images as sixels."""

    def convert_data(self, wp: WritePosition) -> str:
        """Convert datum to required format."""
        bbox = wp.bbox if isinstance(wp, BoundedWritePosition) else DiInt(0, 0, 0, 0)
        cmd = str(self.datum.convert(to="sixel", cols=wp.width, rows=wp.height)).strip()
        if any(bbox):
            from sixelcrop import sixelcrop

            cell_size_x, cell_size_y = self.app.cell_size_px

            cmd = sixelcrop(
                data=cmd,
                # Horizontal pixel offset of the displayed image region
                x=bbox.left * cell_size_x,
                # Vertical pixel offset of the displayed image region
                y=bbox.top * cell_size_y,
                # Pixel width of the displayed image region
                w=(wp.width - bbox.left - bbox.right) * cell_size_x,
                # Pixel height of the displayed image region
                h=(wp.height - bbox.top - bbox.bottom) * cell_size_y,
            )

        return cmd

    def get_rendered_lines(
        self, visible_width: int, visible_height: int, wrap_lines: bool = False
    ) -> list[StyleAndTextTuples]:
        """Get rendered lines from the cache, or generate them."""
        bbox = self.bbox

        d_cols, d_aspect = self.datum.cell_size()
        d_rows = d_cols * d_aspect

        total_available_width = visible_width + bbox.left + bbox.right
        total_available_height = visible_height + bbox.top + bbox.bottom

        # Scale down the graphic to fit in the available space
        if d_rows > total_available_height or d_cols > total_available_width:
            if d_rows / total_available_height > d_cols / total_available_width:
                ratio = min(1, total_available_height / d_rows)
            else:
                ratio = min(1, total_available_width / d_cols)
        else:
            ratio = 1

        # Calculate the size and cropping bbox at which we want to display the graphic
        cols = floor(d_cols * ratio)
        rows = ceil(cols * d_aspect)
        d_bbox = DiInt(
            top=self.bbox.top,
            right=max(0, cols - (total_available_width - self.bbox.right)),
            bottom=max(0, rows - (total_available_height - self.bbox.bottom)),
            left=self.bbox.left,
        )

        def render_lines() -> list[StyleAndTextTuples]:
            """Render the lines to display in the control."""
            ft: list[StyleAndTextTuples] = []
            if visible_height >= 0:
                cmd = self.convert_data(BoundedWritePosition(0, 0, cols, rows, d_bbox))
                ft.extend(
                    split_lines(
                        to_formatted_text(
                            [
                                # Move cursor down and across by image height and width
                                (
                                    "",
                                    "\n".join(
                                        (visible_height) * [" " * (visible_width)]
                                    ),
                                ),
                                # Save position, then move back
                                ("[ZeroWidthEscape]", "\x1b[s"),
                                # Move cursor up if there is more than one line to display
                                *(
                                    [
                                        (
                                            "[ZeroWidthEscape]",
                                            f"\x1b[{visible_height - 1}A",
                                        )
                                    ]
                                    if visible_height > 1
                                    else []
                                ),
                                ("[ZeroWidthEscape]", f"\x1b[{visible_width}D"),
                                # Place the image without moving cursor
                                (
                                    "[ZeroWidthEscape]",
                                    passthrough(cmd, self.app.config),
                                ),
                                # ("[ZeroWidthEscape]", "XXXXX"),
                                # Restore the last known cursor position (at the bottom)
                                ("[ZeroWidthEscape]", "\x1b[u"),
                            ]
                        )
                    )
                )
            return ft

        key = (
            visible_width,
            self.app.color_palette,
            self.app.cell_size_px,
            self.bbox,
        )
        return self._format_cache.get(key, render_lines)


class ItermGraphicControl(GraphicControl):
    """A graphic control which displays images using iTerm's graphics protocol."""

    def convert_data(self, wp: WritePosition) -> str:
        """Convert the graphic's data to base64 data."""
        datum = self.datum
        bbox = wp.bbox if isinstance(wp, BoundedWritePosition) else DiInt(0, 0, 0, 0)
        # Crop image if necessary
        if any(bbox):
            import io

            image = datum.convert(to="pil", cols=wp.width, rows=wp.height)
            if image is not None:
                cell_size_x, cell_size_y = self.app.cell_size_px
                # Downscale image to fit target region for precise cropping
                image.thumbnail((wp.width * cell_size_x, wp.height * cell_size_y))
                left = bbox.left * cell_size_x
                top = bbox.top * cell_size_y
                right = (wp.width - bbox.right) * cell_size_x
                bottom = (wp.height - bbox.bottom) * cell_size_y
                upper, lower = sorted((top, bottom))
                image = image.crop((left, upper, right, lower))
                with io.BytesIO() as output:
                    image.save(output, format="PNG")
                    datum = Datum(data=output.getvalue(), format="png")

        if datum.format.startswith("base64-"):
            b64data = datum.data
        else:
            b64data = datum.convert(to="base64-png", cols=wp.width, rows=wp.height)
        return b64data.replace("\n", "").strip()

    def get_rendered_lines(
        self, visible_width: int, visible_height: int, wrap_lines: bool = False
    ) -> list[StyleAndTextTuples]:
        """Get rendered lines from the cache, or generate them."""
        bbox = self.bbox

        d_cols, d_aspect = self.datum.cell_size()
        d_rows = d_cols * d_aspect

        total_available_width = visible_width + bbox.left + bbox.right
        total_available_height = visible_height + bbox.top + bbox.bottom

        # Scale down the graphic to fit in the available space
        if d_rows > total_available_height or d_cols > total_available_width:
            if d_rows / total_available_height > d_cols / total_available_width:
                ratio = min(1, total_available_height / d_rows)
            else:
                ratio = min(1, total_available_width / d_cols)
        else:
            ratio = 1

        # Calculate the size and cropping bbox at which we want to display the graphic
        cols = floor(d_cols * ratio)
        rows = ceil(cols * d_aspect)
        d_bbox = DiInt(
            top=self.bbox.top,
            right=max(0, cols - (total_available_width - self.bbox.right)),
            bottom=max(0, rows - (total_available_height - self.bbox.bottom)),
            left=self.bbox.left,
        )

        def render_lines() -> list[StyleAndTextTuples]:
            """Render the lines to display in the control."""
            ft: list[StyleAndTextTuples] = []
            if (
                rows - d_bbox.top - d_bbox.bottom > 0
                and cols - d_bbox.left - d_bbox.right > 0
            ):
                b64data = self.convert_data(
                    BoundedWritePosition(0, 0, cols, rows, d_bbox)
                )
                cmd = f"\x1b]1337;File=inline=1;width={cols}:{b64data}\a"
                ft.extend(
                    split_lines(
                        to_formatted_text(
                            [
                                # Move cursor down and across by image height and width
                                (
                                    "",
                                    "\n".join(
                                        (visible_height) * [" " * (visible_width)]
                                    ),
                                ),
                                # Save position, then move back
                                ("[ZeroWidthEscape]", "\x1b[s"),
                                # Move cursor up if there is more than one line to display
                                *(
                                    [
                                        (
                                            "[ZeroWidthEscape]",
                                            f"\x1b[{visible_height - 1}A",
                                        )
                                    ]
                                    if visible_height > 1
                                    else []
                                ),
                                ("[ZeroWidthEscape]", f"\x1b[{visible_width}D"),
                                # Place the image without moving cursor
                                (
                                    "[ZeroWidthEscape]",
                                    passthrough(cmd, self.app.config),
                                ),
                                # Restore the last known cursor position (at the bottom)
                                ("[ZeroWidthEscape]", "\x1b[u"),
                            ]
                        )
                    )
                )
            return ft

        key = (
            visible_width,
            self.app.color_palette,
            self.app.cell_size_px,
            self.bbox,
        )
        return self._format_cache.get(key, render_lines)


class KittyGraphicControl(GraphicControl):
    """A graphic control which displays images using Kitty's graphics protocol."""

    _kitty_image_count: ClassVar[int] = 1

    def __init__(
        self,
        datum: Datum,
        scale: float = 0,
        bbox: DiInt | None = None,
    ) -> None:
        """Create a new kitty graphic instance."""
        super().__init__(datum=datum, scale=scale, bbox=bbox)
        self.kitty_image_id = 0
        self.loaded = False
        self._datum_pad_cache: FastDictCache[tuple[Datum, int, int], Datum] = (
            FastDictCache(get_value=self._pad_datum, size=1)
        )

    def _pad_datum(self, datum: Datum, cell_size_x: int, cell_size_y: int) -> Datum:
        from PIL import ImageOps

        px, py = datum.pixel_size()

        if px and py:
            target_width = int((px + cell_size_x - 1) // cell_size_x * cell_size_x)
            target_height = int((py + cell_size_y - 1) // cell_size_y * cell_size_y)

            image = ImageOps.pad(
                datum.convert("pil").convert("RGBA"),
                (target_width, target_height),
                centering=(0, 0),
            )
            datum = Datum(
                image,
                format="pil",
                px=target_width,
                py=target_height,
                path=datum.path,
                align=datum.align,
            )
        return datum

    def convert_data(self, wp: WritePosition) -> str:
        """Convert the graphic's data to base64 data for kitty graphics protocol."""
        bbox = wp.bbox if isinstance(wp, BoundedWritePosition) else DiInt(0, 0, 0, 0)
        full_width = wp.width + bbox.left + bbox.right
        full_height = wp.height + bbox.top + bbox.bottom

        datum = self._datum_pad_cache[(self.datum, *self.app.cell_size_px)]
        return str(
            datum.convert(
                to="base64-png",
                cols=full_width,
                rows=full_height,
            )
        ).replace("\n", "")

    @staticmethod
    def _kitty_cmd(chunk: str = "", **params: Any) -> str:
        param_str = ",".join(
            [f"{key}={value}" for key, value in params.items() if value is not None]
        )
        cmd = f"\x1b_G{param_str}"
        if chunk:
            cmd += f";{chunk}"
        cmd += "\x1b\\"
        return cmd

    def load(self, rows: int, cols: int, bbox: DiInt) -> None:
        """Send the graphic to the terminal without displaying it."""
        data = self.convert_data(
            BoundedWritePosition(0, 0, width=cols, height=rows, bbox=bbox)
        )
        self.kitty_image_id = self._kitty_image_count
        KittyGraphicControl._kitty_image_count += 1

        while data:
            chunk, data = data[:4096], data[4096:]
            cmd = self._kitty_cmd(
                chunk=chunk,
                a="t",  # We are sending an image without displaying it
                t="d",  # Transferring the image directly
                i=self.kitty_image_id,  # Send a unique image number, wait for an image id
                # I=self.kitty_image_number,  # Send a unique image number, wait for an image id
                p=1,  # Placement ID
                q=2,  # No chatback
                f=100,  # Sending a PNG image
                C=1,  # Do not move the cursor
                m=1 if data else 0,  # Data will be chunked
            )
            self.app.output.write_raw(passthrough(cmd, self.app.config))
        self.app.output.flush()
        self.loaded = True

    def hide_cmd(self) -> str:
        """Generate a command to hide the graphic."""
        return passthrough(
            self._kitty_cmd(
                a="d",
                d="i",
                i=self.kitty_image_id,
                q=1,
            ),
            self.app.config,
        )

    def hide(self) -> None:
        """Hide the graphic from show without deleting it."""
        if self.kitty_image_id > 0:
            self.app.output.write_raw(self.hide_cmd())
            self.app.output.flush()

    def delete(self) -> None:
        """Delete the graphic from the terminal."""
        if self.kitty_image_id > 0:
            self.app.output.write_raw(
                passthrough(
                    self._kitty_cmd(
                        a="D",
                        d="I",
                        i=self.kitty_image_id,
                        q=2,
                    ),
                    self.app.config,
                )
            )
            self.app.output.flush()
            self.loaded = False

    def get_rendered_lines(
        self, visible_width: int, visible_height: int, wrap_lines: bool = False
    ) -> list[StyleAndTextTuples]:
        """Get rendered lines from the cache, or generate them."""
        bbox = self.bbox

        cell_size_px = self.app.cell_size_px
        datum = self._datum_pad_cache[(self.datum, *cell_size_px)]
        px, py = datum.pixel_size()
        # Fall back to a default pixel size
        px = px or 100
        py = py or 100

        d_cols, d_aspect = datum.cell_size()
        d_rows = d_cols * d_aspect

        total_available_width = visible_width + bbox.left + bbox.right
        total_available_height = visible_height + bbox.top + bbox.bottom

        # Scale down the graphic to fit in the available space
        if d_rows > total_available_height or d_cols > total_available_width:
            if d_rows / total_available_height > d_cols / total_available_width:
                ratio = min(1, total_available_height / d_rows)
            else:
                ratio = min(1, total_available_width / d_cols)
        else:
            ratio = 1

        # Calculate the size and cropping bbox at which we want to display the graphic
        cols = floor(d_cols * ratio)
        rows = ceil(cols * d_aspect)
        d_bbox = DiInt(
            top=self.bbox.top,
            right=max(0, cols - (total_available_width - self.bbox.right)),
            bottom=max(0, rows - (total_available_height - self.bbox.bottom)),
            left=self.bbox.left,
        )
        if not self.loaded:
            self.load(cols=cols, rows=rows, bbox=d_bbox)

        def render_lines() -> list[StyleAndTextTuples]:
            """Render the lines to display in the control."""
            ft: list[StyleAndTextTuples] = []
            if display_rows := rows - d_bbox.top - d_bbox.bottom:
                cmd = self._kitty_cmd(
                    a="p",  # Display a previously transmitted image
                    i=self.kitty_image_id,
                    p=1,  # Placement ID
                    m=0,  # No batches remaining
                    q=2,  # No backchat
                    c=cols - d_bbox.left - d_bbox.right,
                    r=display_rows,
                    C=1,  # 1 = Do move the cursor
                    # Horizontal pixel offset of the displayed image region
                    x=int(px * d_bbox.left / cols),
                    # Vertical pixel offset of the displayed image region
                    y=int(py * d_bbox.top / rows),
                    # Pixel width of the displayed image region
                    w=int(px * (cols - d_bbox.left - d_bbox.right) / cols),
                    # Pixel height of the displayed image region
                    h=int(py * (rows - d_bbox.top - d_bbox.bottom) / rows),
                )
                ft.extend(
                    split_lines(
                        to_formatted_text(
                            [
                                # Move cursor down and acoss by image height and width
                                (
                                    "",
                                    "\n".join(
                                        (visible_height) * [" " * (visible_width)]
                                    ),
                                ),
                                # Save position, then move back
                                ("[ZeroWidthEscape]", "\x1b[s"),
                                # Move cursor up if there is more than one line to display
                                *(
                                    [
                                        (
                                            "[ZeroWidthEscape]",
                                            f"\x1b[{visible_height - 1}A",
                                        )
                                    ]
                                    if visible_height > 1
                                    else []
                                ),
                                ("[ZeroWidthEscape]", f"\x1b[{visible_width}D"),
                                # Place the image without moving cursor
                                (
                                    "[ZeroWidthEscape]",
                                    passthrough(cmd, self.app.config),
                                ),
                                # Restore the last known cursor position (at the bottom)
                                ("[ZeroWidthEscape]", "\x1b[u"),
                            ]
                        )
                    )
                )
            else:
                ft.append([("[ZeroWidthEscape]", self.hide_cmd())])
            return ft

        key = (
            visible_width,
            self.app.color_palette,
            self.app.cell_size_px,
            self.bbox,
        )
        return self._format_cache.get(key, render_lines)

    def reset(self) -> None:
        """Hide and delete the kitty graphic from the terminal."""
        self.hide()
        self.delete()
        super().reset()

    def close(self) -> None:
        """Remove the displayed object entirely."""
        super().close()
        if not self.app.leave_graphics():
            self.delete()


class NotVisible(Exception):
    """Exception to signal that a graphic is not currently visible."""


class GraphicWindow(Window):
    """A window responsible for displaying terminal graphics content.

    The content is displayed floating on top of a target window.

    The graphic will be displayed if:
    - a completion menu is not being shown
    - a dialog is not being shown
    - a menu is not being shown
    - the output it attached to is fully in view
    """

    content: GraphicControl

    def __init__(
        self,
        content: GraphicControl,
        get_position: Callable[[Screen], BoundedWritePosition],
        filter: FilterOrBool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initiate a new :py:class:`GraphicWindow` object.

        Args:
            content: A control which generates the graphical content to display
            get_position: A function which returns the position of the graphic
            filter: A filter which determines if the graphic should be shown
            args: Positional arguments for :py:method:`Window.__init__`
            kwargs: Key-word arguments for :py:method:`Window.__init__`
        """
        super().__init__(*args, **kwargs)
        self.content = content
        self.get_position = get_position
        self.filter = ~has_float & to_filter(filter)
        self._pre_rendered = False

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """Draw the graphic window's contents to the screen if required."""
        # Pre-convert datum for this write position so result is cached
        if not self._pre_rendered:
            self.content.convert_data(write_position)
            self._pre_rendered = True
        filter_value = self.filter()
        if filter_value:
            try:
                new_write_position = self.get_position(screen)
            except NotVisible:
                pass
            else:
                # Inform the graphic control of the calculated cropping region
                self.content.bbox = new_write_position.bbox

                # Draw the graphic content to the screen
                if (
                    new_write_position
                    and new_write_position.width
                    and new_write_position.height
                ):
                    # Do not pass the bbox on to the window when writing
                    new_write_position.bbox = DiInt(0, 0, 0, 0)
                    super().write_to_screen(
                        screen,
                        MouseHandlers(),  # Do not let the float add mouse events
                        new_write_position,
                        # Force renderer refreshes by constantly changing the style
                        f"{parent_style} class:render-{get_app().render_counter}",
                        erase_bg=True,
                        z_index=z_index,
                    )
                    return

        # Otherwise hide the content (required for kitty graphics)
        if not get_app().leave_graphics():
            self.content.hide()

    def _fill_bg(
        self,
        screen: Screen,
        # mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        erase_bg: bool,
    ) -> None:
        """Erase/fill the background."""
        char: str | None = self.char() if callable(self.char) else self.char
        if erase_bg or char:
            wp = write_position
            char_obj = Char(char or " ", f"class:render-{get_app().render_counter}")

            # mouse_handlers_dict = mouse_handlers.mouse_handlers
            for y in range(wp.ypos, wp.ypos + wp.height):
                row = screen.data_buffer[y]
                # mouse_handler_row = mouse_handlers_dict[y]
                for x in range(wp.xpos, wp.xpos + wp.width):
                    row[x] = char_obj
                    # mouse_handler_row[x] = lambda e: NotImplemented


def select_graphic_control(format_: str) -> type[GraphicControl] | None:
    """Determine which graphic control to use."""
    SelectedGraphicControl: type[GraphicControl] | None = None
    app = get_app()
    preferred_graphics_protocol = app.config.graphics
    useable_graphics_controls: list[type[GraphicControl]] = []
    _in_mplex = in_mplex()
    force_graphics = app.config.force_graphics

    if preferred_graphics_protocol != "none":
        if (app.term_graphics_iterm or force_graphics) and find_route(
            format_, "base64-png"
        ):
            useable_graphics_controls.append(ItermGraphicControl)
        if (
            preferred_graphics_protocol == "iterm"
            and ItermGraphicControl in useable_graphics_controls
            # Iterm does not work in mplex without pass-through
            and (not _in_mplex or (_in_mplex and force_graphics))
        ):
            SelectedGraphicControl = ItermGraphicControl
        elif (
            (app.term_graphics_kitty or force_graphics)
            and find_route(format_, "base64-png")
            # Kitty does not work in mplex without pass-through
            and (not _in_mplex or (_in_mplex and force_graphics))
        ):
            useable_graphics_controls.append(KittyGraphicControl)
        if (
            preferred_graphics_protocol == "kitty"
            and KittyGraphicControl in useable_graphics_controls
        ):
            SelectedGraphicControl = KittyGraphicControl
        # Tmux now supports sixels (>=3.4)
        elif (app.term_graphics_sixel or force_graphics) and find_route(
            format_, "sixel"
        ):
            useable_graphics_controls.append(SixelGraphicControl)
        if (
            preferred_graphics_protocol == "sixel"
            and SixelGraphicControl in useable_graphics_controls
        ):
            SelectedGraphicControl = SixelGraphicControl

        if SelectedGraphicControl is None and useable_graphics_controls:
            SelectedGraphicControl = useable_graphics_controls[0]

    return SelectedGraphicControl


class GraphicProcessor:
    """Class which loads and positions graphics references in a :py:class:`UIContent`."""

    def __init__(self, control: UIControl) -> None:
        """Initialize a new graphic processor."""
        self.control = control

        self.positions: dict[str, Point] = {}
        self._position_cache: FastDictCache[tuple[UIContent], dict[str, Point]] = (
            FastDictCache(self._load_positions, size=1_000)
        )
        self._float_cache: FastDictCache[tuple[str], Float | None] = FastDictCache(
            self.get_graphic_float, size=1_000
        )
        self.app = get_app()

    def load(self, content: UIContent) -> None:
        """Check for graphics in lines of text."""
        self.positions = self._position_cache[content,]

    def _load_positions(self, content: UIContent) -> dict[str, Point]:
        positions = {}
        get_line = content.get_line
        for y in range(content.line_count):
            line = get_line(y)
            x = 0
            for style, text, *_ in line:
                for part in style.split():
                    if part.startswith("[Graphic_"):
                        key = part[9:-1]
                        positions[key] = Point(x, y)
                        # Get graphic float for this image and update its position
                        graphic_float = self._float_cache[key,]
                        # Register graphic with application
                        if graphic_float:
                            self.app.graphics.add(graphic_float)
                    if part in _ZERO_WIDTH_FRAGMENTS:
                        break
                else:
                    x += get_cwidth(text)
        return positions

    def _get_position(
        self, key: str, rows: int, cols: int
    ) -> Callable[[Screen], BoundedWritePosition]:
        """Return a function that returns the current bounded graphic position."""

        def get_graphic_position(screen: Screen) -> BoundedWritePosition:
            """Get the position and bbox of a graphic."""
            if key not in self.positions:
                raise NotVisible

            # Find the control's window
            window: Window | None = None
            for _window in get_app().layout.find_all_windows():
                if _window.content == self.control:
                    window = _window
                    break

            if window not in screen.visible_windows:
                raise NotVisible

            render_info = window.render_info
            if render_info is None:
                raise NotVisible

            # Hide graphic if control is not in layout
            win_wp = screen.visible_windows_to_write_positions.get(window)
            if win_wp is None:
                raise NotVisible

            if isinstance(win_wp, BoundedWritePosition):
                win_bbox = win_wp.bbox
            else:
                win_bbox = DiInt(0, 0, 0, 0)

            render_info = window.render_info
            if render_info is None:
                raise NotVisible

            x, y = self.positions[key]
            win_content_height = render_info.ui_content.line_count
            win_content_width = win_wp.width  # TODO - get the actual content width

            horizontal_scroll = getattr(render_info, "horizontal_scroll", 0)
            vertical_scroll = render_info.vertical_scroll
            if (
                horizontal_scroll >= x + win_content_width
                or vertical_scroll >= y + win_content_height
            ):
                raise NotVisible

            bbox = DiInt(
                top=max(0, win_bbox.top - y + vertical_scroll),
                right=win_bbox.right,
                bottom=max(
                    0, win_bbox.bottom - (win_wp.height - y - rows) - vertical_scroll
                ),
                left=win_bbox.left,
            )

            xpos = win_wp.xpos + x + win_bbox.left
            ypos = max(
                win_wp.ypos + win_bbox.top,
                win_wp.ypos + y + max(0, win_bbox.top - y) - min(y, vertical_scroll),
            )
            width = max(0, cols - bbox.left - bbox.right)
            height = max(0, rows - bbox.top - bbox.bottom)

            return BoundedWritePosition(
                xpos=xpos, ypos=ypos, width=width, height=height, bbox=bbox
            )

        return get_graphic_position

    def get_graphic_float(self, key: str) -> Float | None:
        """Create a graphical float for an image."""
        sized_datum = Datum.get_size(key)
        if sized_datum is None:
            log.debug("Datum not found for graphic '%s'", key)
            return None

        datum, (rows, cols) = sized_datum

        GraphicControl = select_graphic_control(format_=datum.format)
        if GraphicControl is None:
            # log.debug("Terminal graphics not supported or format not graphical")
            return None

        bg_color = datum.bg
        graphic_float = Float(
            graphic_window := GraphicWindow(
                content=(graphic_control := GraphicControl(datum)),
                get_position=self._get_position(key, rows, cols),
                style=f"bg:{bg_color}" if bg_color else "",
                align=datum.align,
            )
        )
        # Register graphic with application
        (app_graphics := self.app.graphics).add(graphic_float)
        # Hide the graphic from app if the float is deleted
        weak_float_ref = weakref.ref(graphic_float)
        graphic_window.filter &= Condition(lambda: weak_float_ref() in app_graphics)
        # Hide the graphic from terminal if the float is deleted
        weakref.finalize(graphic_float, graphic_control.close)

        return graphic_float
