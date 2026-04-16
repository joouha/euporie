from apptk.data_structures import Point
from apptk.filters import FilterOrBool
from apptk.key_binding import KeyBindingsBase

from .containers import Container, ScrollOffsets
from .dimension import AnyDimension, Dimension
from .mouse_handlers import MouseHandlers
from .screen import Screen, WritePosition

MAX_AVAILABLE_HEIGHT = 10_000

__all__ = [
    "ScrollablePane",
]

class ScrollablePane(Container):
    content: Container
    scroll_offsets: ScrollOffsets | None
    keep_cursor_visible: FilterOrBool
    keep_focused_window_visible: FilterOrBool
    max_available_height: int
    width: AnyDimension
    height: AnyDimension
    show_scrollbar: FilterOrBool
    display_arrows: FilterOrBool
    up_arrow_symbol: str
    down_arrow_symbol: str
    vertical_scroll = 0
    def __init__(
        self,
        content: Container,
        scroll_offsets: ScrollOffsets | None = None,
        keep_cursor_visible: FilterOrBool = True,
        keep_focused_window_visible: FilterOrBool = True,
        max_available_height: int = MAX_AVAILABLE_HEIGHT,
        width: AnyDimension = None,
        height: AnyDimension = None,
        show_scrollbar: FilterOrBool = True,
        display_arrows: FilterOrBool = True,
        up_arrow_symbol: str = "^",
        down_arrow_symbol: str = "v",
    ) -> None: ...
    def reset(self) -> None: ...
    def preferred_width(self, max_available_width: int) -> Dimension: ...
    def preferred_height(self, width: int, max_available_height: int) -> Dimension: ...
    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None: ...
    def _clip_point_to_visible_area(
        self,
        point: Point,
        write_position: WritePosition,
    ) -> Point: ...
    def _copy_over_screen(
        self,
        screen: Screen,
        temp_screen: Screen,
        write_position: WritePosition,
        virtual_width: int,
    ) -> None: ...
    def _copy_over_mouse_handlers(
        self,
        mouse_handlers: MouseHandlers,
        temp_mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        virtual_width: int,
    ) -> None: ...
    def _copy_over_write_positions(
        self,
        screen: Screen,
        temp_screen: Screen,
        write_position: WritePosition,
    ) -> None: ...
    def is_modal(self) -> bool: ...
    def get_key_bindings(self) -> KeyBindingsBase | None: ...
    def get_children(self) -> list[Container]: ...
    def _make_window_visible(
        self,
        visible_height: int,
        virtual_height: int,
        visible_win_write_pos: WritePosition,
        cursor_position: Point | None,
    ) -> None: ...
    def _draw_scrollbar(
        self,
        write_position: WritePosition,
        content_height: int,
        screen: Screen,
    ) -> None: ...
    def __repr__(self) -> str: ...
