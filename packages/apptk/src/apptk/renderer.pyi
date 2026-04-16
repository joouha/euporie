import logging
from asyncio import Future
from collections import deque
from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING, Any

from apptk.data_structures import Point
from apptk.filters import FilterOrBool
from apptk.formatted_text import AnyFormattedText
from apptk.layout.screen import Screen
from apptk.output import ColorDepth, Output
from apptk.styles import Attrs, BaseStyle, StyleTransformation

if TYPE_CHECKING:
    from collections.abc import Callable

    from apptk.application import Application
    from apptk.layout.graphics import GraphicControl
    from apptk.layout.layout import Layout

log = logging.getLogger(__name__)

__all__ = [
    "Renderer",
    "print_formatted_text",
]

def print_formatted_text(
    output: Output,
    formatted_text: AnyFormattedText,
    style: BaseStyle,
    style_transformation: StyleTransformation | None = None,
    color_depth: ColorDepth | None = None,
) -> None: ...

class HeightIsUnknownError(Exception): ...

class _StyleStringToAttrsCache(dict[str, Attrs]):
    get_attrs_for_style_str: Callable[[str], Attrs]
    style_transformation: StyleTransformation
    def __init__(
        self,
        get_attrs_for_style_str: Callable[[str], Attrs],
        style_transformation: StyleTransformation,
    ) -> None: ...
    def __missing__(self, style_str: str) -> Attrs: ...

class _StyleStringHasStyleCache(dict[str, bool]):
    style_string_to_attrs: dict[str, Attrs]
    def __init__(self, style_string_to_attrs: dict[str, Attrs]) -> None: ...
    def __missing__(self, style_str: str) -> bool: ...

class CPR_Support(Enum):
    SUPPORTED = "SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    UNKNOWN = "UNKNOWN"

class Renderer:
    CPR_TIMEOUT = 2  # Time to wait until we consider CPR to be not supported.
    style: BaseStyle
    output: Output
    full_screen: bool
    mouse_support: FilterOrBool
    cpr_not_supported_callback: Callable[[], None] | None
    _in_alternate_screen = True
    _mouse_support_enabled = True
    _bracketed_paste_enabled = True
    _cursor_key_mode_reset = True
    _waiting_for_cpr_futures: deque[Future[None]]
    cpr_support = CPR_Support.UNKNOWN
    _attrs_for_style = None
    _style_string_has_style = None
    _last_style_hash = self.style.invalidation_hash()
    _last_transformation_hash = app.style_transformation.invalidation_hash()
    _last_color_depth = app.color_depth
    _cursor_pos: Point
    _last_screen = screen
    _last_size = size
    _last_style: str | None
    _last_cursor_shape = new_cursor_shape
    mouse_handlers = mouse_handlers
    _min_available_height = 0
    extend_height: FilterOrBool
    extend_width: FilterOrBool
    leave_graphics: FilterOrBool
    _extended_keys_enabled = False
    _palette_dsr_enabled = False
    _sgr_pixel_enabled = False
    preferred_graphics: Callable[[], type[GraphicControl]] | GraphicControl | None
    graphics_sixel = False
    graphics_iterm = False
    graphics_kitty = False
    sgr_pixel = False
    osc52_clipboard = False
    size_px: tuple[int, int]
    _last_link: str | None
    def __init__(
        self,
        style: BaseStyle,
        output: Output,
        full_screen: bool = False,
        mouse_support: FilterOrBool = False,
        cpr_not_supported_callback: Callable[[], None] | None = None,
        extend_height: FilterOrBool = False,
        extend_width: FilterOrBool = False,
        preferred_graphics: Callable[[], type[GraphicControl]]
        | GraphicControl
        | None = None,
        leave_graphics: FilterOrBool = False,
    ) -> None: ...
    def reset(
        self, _scroll: bool = False, leave_alternate_screen: bool = True
    ) -> None: ...
    @property
    def last_rendered_screen(self) -> Screen | None: ...
    @property
    def height_is_known(self) -> bool: ...
    @property
    def rows_above_layout(self) -> int: ...
    def request_absolute_cursor_position(self) -> None: ...
    def report_absolute_cursor_row(self, row: int) -> None: ...
    @property
    def waiting_for_cpr(self) -> bool: ...
    async def wait_for_cpr_responses(self, timeout: int = 1) -> None: ...
    def render(
        self,
        app: Application[Any],
        layout: Layout,
        is_done: bool = False,
    ) -> None: ...
    def erase(self, leave_alternate_screen: bool = True) -> None: ...
    def clear(self) -> None: ...
