import logging
from abc import abstractmethod
from collections.abc import Callable, Sequence
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING, NamedTuple, Union
from weakref import WeakKeyDictionary

from apptk.cache import SimpleCache
from apptk.data_structures import Point
from apptk.enums import HorizontalAlign, VerticalAlign
from apptk.filters import FilterOrBool, emacs_insert_mode, to_filter, vi_insert_mode
from apptk.formatted_text import AnyFormattedText, StyleAndTextTuples
from apptk.key_binding import KeyBindingsBase
from apptk.layout.controls import (
    DummyControl,
    FormattedTextControl,
    UIContent,
)
from apptk.layout.dimension import Dimension
from apptk.layout.margins import Margin
from apptk.layout.screen import WritePosition
from apptk.mouse_events import MouseEvent

from .controls import (
    DummyControl,
    FormattedTextControl,
    GetLinePrefixCallable,
    UIContent,
)
from .dimension import (
    AnyDimension,
    Dimension,
)
from .margins import Margin
from .mouse_handlers import MouseHandlers
from .screen import Screen, WritePosition

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any, Protocol, TypeGuard

    from apptk.data_structures import Size
    from apptk.key_binding.key_bindings import KeyBindingsBase, NotImplementedOrNone
    from apptk.layout.graphics import GraphicControl
    from apptk.layout.mouse_handlers import MouseHandlers
    from apptk.layout.screen import Screen
    from typing_extensions import Protocol

AnyContainer = Union[Container, "MagicContainer"]
_in_insert_mode = vi_insert_mode | emacs_insert_mode
StatusBarFields = tuple[Sequence[AnyFormattedText], Sequence[AnyFormattedText]]
log = logging.getLogger(__name__)
WindowAlign = HorizontalAlign
_CONTAINER_STATUSES: WeakKeyDictionary[
    Container, Callable[[], StatusBarFields | None]
] = WeakKeyDictionary()

__all__ = [
    "AnyContainer",
    "ColorColumn",
    "ConditionalContainer",
    "Container",
    "DynamicContainer",
    "Float",
    "FloatContainer",
    "HSplit",
    "HorizontalAlign",
    "ScrollOffsets",
    "VSplit",
    "VerticalAlign",
    "Window",
    "WindowAlign",
    "WindowRenderInfo",
    "is_container",
    "to_container",
    "to_window",
]

def to_container(container: AnyContainer) -> Container: ...
def to_window(container: AnyContainer) -> Window: ...
def is_container(value: object) -> TypeGuard[AnyContainer]: ...
def distribute_dimensions(
    size: int,
    dimensions: tuple[DimensionTuple, ...],
    expand: bool = False,
) -> list[int] | None: ...

class Container:
    @abstractmethod
    def reset(self) -> None: ...
    @abstractmethod
    def preferred_width(self, max_available_width: int) -> Dimension: ...
    @abstractmethod
    def preferred_height(self, width: int, max_available_height: int) -> Dimension: ...
    @abstractmethod
    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None: ...
    def is_modal(self) -> bool: ...
    def get_key_bindings(self) -> KeyBindingsBase | None: ...
    @abstractmethod
    def get_children(self) -> list[Container]: ...

class MagicContainer(Protocol):
    def __pt_container__(self) -> AnyContainer: ...

class VerticalAlign(Enum):
    TOP = "TOP"
    CENTER = "CENTER"
    BOTTOM = "BOTTOM"
    JUSTIFY = "JUSTIFY"

class HorizontalAlign(Enum):
    LEFT = "LEFT"
    CENTER = "CENTER"
    RIGHT = "RIGHT"
    JUSTIFY = "JUSTIFY"

class _Split(Container):
    children = [to_container(c) for c in children]
    window_too_small: Container | None
    padding: AnyDimension
    padding_char: str | None
    padding_style: str
    width: AnyDimension
    height: AnyDimension
    z_index: int | None
    modal: bool
    key_bindings: KeyBindingsBase | None
    style: str | Callable[[], str]
    def __init__(
        self,
        children: Sequence[AnyContainer],
        window_too_small: Container | None = None,
        padding: AnyDimension = Dimension.exact(0),
        padding_char: str | None = None,
        padding_style: str = "",
        width: AnyDimension = None,
        height: AnyDimension = None,
        z_index: int | None = None,
        modal: bool = False,
        key_bindings: KeyBindingsBase | None = None,
        style: str | Callable[[], str] = "",
    ) -> None: ...
    def is_modal(self) -> bool: ...
    def get_key_bindings(self) -> KeyBindingsBase | None: ...
    def get_children(self) -> list[Container]: ...

class HSplit:
    align: VerticalAlign
    _children_cache: SimpleCache[tuple[Container, ...], list[Container]]
    _remaining_space_window: Window
    _pad_window: Window
    def __init__(
        self,
        children: Sequence[AnyContainer],
        window_too_small: Container | None = None,
        align: VerticalAlign = VerticalAlign.JUSTIFY,
        padding: AnyDimension = 0,
        padding_char: str | None = None,
        padding_style: str = "",
        width: AnyDimension = None,
        height: AnyDimension = None,
        z_index: int | None = None,
        modal: bool = False,
        key_bindings: KeyBindingsBase | None = None,
        style: str | Callable[[], str] = "",
    ) -> None: ...
    def preferred_width(self, max_available_width: int) -> Dimension: ...
    def preferred_height(self, width: int, max_available_height: int) -> Dimension: ...
    def reset(self) -> None: ...
    @property
    def _all_children(self) -> list[Container]: ...
    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None: ...
    def _divide_heights(self, write_position: WritePosition) -> list[int] | None: ...
    @property
    def pad_window(self) -> Window: ...

class VSplit:
    align: HorizontalAlign
    _children_cache: SimpleCache[tuple[Container, ...], list[Container]]
    _remaining_space_window: Window
    _pad_window: Window
    def __init__(
        self,
        children: Sequence[AnyContainer],
        window_too_small: Container | None = None,
        align: HorizontalAlign = HorizontalAlign.JUSTIFY,
        padding: AnyDimension = 0,
        padding_char: str | None = None,
        padding_style: str = "",
        width: AnyDimension = None,
        height: AnyDimension = None,
        z_index: int | None = None,
        modal: bool = False,
        key_bindings: KeyBindingsBase | None = None,
        style: str | Callable[[], str] = "",
    ) -> None: ...
    def preferred_width(self, max_available_width: int) -> Dimension: ...
    def preferred_height(self, width: int, max_available_height: int) -> Dimension: ...
    def reset(self) -> None: ...
    @property
    def _all_children(self) -> list[Container]: ...
    def _divide_widths(self, width: int) -> list[int] | None: ...
    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None: ...
    @property
    def pad_window(self) -> Window: ...

class FloatContainer:
    content: AnyContainer
    floats: list[Float]
    modal: bool
    key_bindings: KeyBindingsBase | None
    style: str | Callable[[], str]
    z_index: int | None
    def __init__(
        self,
        content: AnyContainer,
        floats: list[Float],
        modal: bool = False,
        key_bindings: KeyBindingsBase | None = None,
        style: str | Callable[[], str] = "",
        z_index: int | None = None,
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
    def _draw_float(
        self,
        fl: Float,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None: ...
    def _area_is_empty(self, screen: Screen, write_position: WritePosition) -> bool: ...
    def is_modal(self) -> bool: ...
    def get_key_bindings(self) -> KeyBindingsBase | None: ...
    def get_children(self) -> list[Container]: ...

class Float:
    left = new_x
    right = None
    top = new_y
    bottom = None
    width: int | Callable[[], int] | None
    height: int | Callable[[], int] | None
    xcursor: bool
    ycursor: bool
    attach_to_window: AnyContainer | None
    content: AnyContainer
    hide_when_covering_content: bool
    allow_cover_cursor: bool
    z_index: int
    transparent: bool
    _drag_start: Point | None
    write_position: WritePosition | None
    allow_overflow: bool
    def __init__(
        self,
        content: AnyContainer,
        top: int | None = None,
        right: int | None = None,
        bottom: int | None = None,
        left: int | None = None,
        width: int | Callable[[], int] | None = None,
        height: int | Callable[[], int] | None = None,
        xcursor: bool = False,
        ycursor: bool = False,
        attach_to_window: AnyContainer | None = None,
        hide_when_covering_content: bool = False,
        allow_cover_cursor: bool = False,
        z_index: int = 1,
        transparent: bool = False,
        allow_overflow: bool = False,
    ) -> None: ...
    def get_width(self) -> int | None: ...
    def get_height(self) -> int | None: ...
    def __repr__(self) -> str: ...
    def drag_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone: ...

class WindowRenderInfo:
    window: Window
    ui_content: UIContent
    vertical_scroll: int
    window_width: int
    window_height: int
    configured_scroll_offsets: ScrollOffsets
    visible_line_to_row_col: dict[int, tuple[int, int]]
    wrap_lines: bool
    _rowcol_to_yx: dict[tuple[int, int], tuple[int, int]]
    _x_offset: int
    _y_offset: int
    horizontal_scroll: int
    def __init__(
        self,
        window: Window,
        ui_content: UIContent,
        horizontal_scroll: int,
        vertical_scroll: int,
        window_width: int,
        window_height: int,
        configured_scroll_offsets: ScrollOffsets,
        visible_line_to_row_col: dict[int, tuple[int, int]],
        rowcol_to_yx: dict[tuple[int, int], tuple[int, int]],
        x_offset: int,
        y_offset: int,
        wrap_lines: bool,
    ) -> None: ...
    @property
    def visible_line_to_input_line(self) -> dict[int, int]: ...
    @property
    def cursor_position(self) -> Point: ...
    @property
    def applied_scroll_offsets(self) -> ScrollOffsets: ...
    @property
    def displayed_lines(self) -> list[int]: ...
    @property
    def input_line_to_visible_line(self) -> dict[int, int]: ...
    def first_visible_line(self, after_scroll_offset: bool = False) -> int: ...
    def last_visible_line(self, before_scroll_offset: bool = False) -> int: ...
    def center_visible_line(
        self,
        before_scroll_offset: bool = False,
        after_scroll_offset: bool = False,
    ) -> int: ...
    @property
    def content_height(self) -> int: ...
    @property
    def full_height_visible(self) -> bool: ...
    @property
    def top_visible(self) -> bool: ...
    @property
    def bottom_visible(self) -> bool: ...
    @property
    def vertical_scroll_percentage(self) -> int: ...
    def get_height_for_line(self, lineno: int) -> int: ...

class ScrollOffsets:
    _top: int | Callable[[], int]
    _bottom: int | Callable[[], int]
    _left: int | Callable[[], int]
    _right: int | Callable[[], int]
    def __init__(
        self,
        top: int | Callable[[], int] = 0,
        bottom: int | Callable[[], int] = 0,
        left: int | Callable[[], int] = 0,
        right: int | Callable[[], int] = 0,
    ) -> None: ...
    @property
    def top(self) -> int: ...
    @property
    def bottom(self) -> int: ...
    @property
    def left(self) -> int: ...
    @property
    def right(self) -> int: ...
    def __repr__(self) -> str: ...

class ColorColumn:
    position: int
    style: str
    def __init__(self, position: int, style: str = "class:color-column") -> None: ...

class WindowAlign(Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    CENTER = "CENTER"

class Window:
    allow_scroll_beyond_bottom: FilterOrBool
    always_hide_cursor: FilterOrBool
    wrap_lines: FilterOrBool
    cursorline: FilterOrBool
    cursorcolumn: FilterOrBool
    content: DummyControl
    dont_extend_width: FilterOrBool
    dont_extend_height: FilterOrBool
    ignore_content_width: FilterOrBool
    ignore_content_height: FilterOrBool
    left_margins: Sequence[Margin] | None
    right_margins: Sequence[Margin] | None
    scroll_offsets: ScrollOffsets | None
    get_vertical_scroll: Callable[[Window], int] | None
    get_horizontal_scroll: Callable[[Window], int] | None
    colorcolumns: None | list[ColorColumn] | Callable[[], list[ColorColumn]]
    align: WindowAlign | Callable[[], WindowAlign]
    style: str | Callable[[], str]
    char: None | str | Callable[[], str]
    get_line_prefix: GetLinePrefixCallable | None
    width: AnyDimension
    height: AnyDimension
    z_index: int | None
    _ui_content_cache: SimpleCache[tuple[int, int, int], UIContent]
    _margin_width_cache: SimpleCache[tuple[Margin, int], int]
    vertical_scroll = 0
    horizontal_scroll = 0
    vertical_scroll_2 = 0
    render_info = render_info
    _graphic_control_cache: SimpleCache[
        tuple[str, str, str, type[GraphicControl]], GraphicControl
    ]
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def __repr__(self) -> str: ...
    def reset(self) -> None: ...
    def _get_margin_width(self, margin: Margin) -> int: ...
    def _get_total_margin_width(self) -> int: ...
    def preferred_width(self, max_available_width: int) -> Dimension: ...
    def preferred_height(self, width: int, max_available_height: int) -> Dimension: ...
    @staticmethod
    def _merge_dimensions(
        dimension: Dimension | None,
        get_preferred: Callable[[], int | None],
        dont_extend: bool = False,
    ) -> Dimension: ...
    def _get_ui_content(self, width: int, height: int) -> UIContent: ...
    def _get_digraph_char(self) -> str | None: ...
    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None: ...
    def _write_to_screen_at_index(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int,
    ) -> None: ...
    def _copy_body(
        self,
        ui_content: UIContent,
        new_screen: Screen,
        write_position: WritePosition,
        move_x: int,
        width: int,
        vertical_scroll: int = 0,
        horizontal_scroll: int = 0,
        wrap_lines: bool = False,
        highlight_lines: bool = False,
        vertical_scroll_2: int = 0,
        always_hide_cursor: bool = False,
        has_focus: bool = False,
        align: WindowAlign = WindowAlign.LEFT,
        get_line_prefix: Callable[[int, int], AnyFormattedText] | None = None,
    ) -> tuple[dict[int, tuple[int, int]], dict[tuple[int, int], tuple[int, int]]]: ...
    def _fill_bg(
        self,
        screen: Screen,
        write_position: WritePosition,
        erase_bg: bool,
    ) -> None: ...
    def _apply_style(
        self,
        new_screen: Screen,
        write_position: WritePosition,
        parent_style: str,
    ) -> None: ...
    def _highlight_digraph(self, new_screen: Screen) -> None: ...
    def _show_key_processor_key_buffer(self, new_screen: Screen) -> None: ...
    def _highlight_cursorlines(
        self,
        new_screen: Screen,
        cpos: Point,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None: ...
    def _copy_margin(
        self,
        margin_content: UIContent,
        new_screen: Screen,
        write_position: WritePosition,
        move_x: int,
        width: int,
    ) -> None: ...
    def _scroll(self, ui_content: UIContent, width: int, height: int) -> None: ...
    def _scroll_when_linewrapping(
        self,
        ui_content: UIContent,
        width: int,
        height: int,
    ) -> None: ...
    def _scroll_without_linewrapping(
        self,
        ui_content: UIContent,
        width: int,
        height: int,
    ) -> None: ...
    def _mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone: ...
    def _scroll_down(self) -> NotImplementedOrNone: ...
    def _scroll_up(self) -> NotImplementedOrNone: ...
    def get_key_bindings(self) -> KeyBindingsBase | None: ...
    def get_children(self) -> list[Container]: ...
    def _draw_graphic(
        self,
        screen: Screen,
        graphic_control: GraphicControl,
        content_pos: Point,
        size: Size,
        write_position: WritePosition,
        parent_style: str,
        ui_content: UIContent,
        vertical_scroll: int,
        horizontal_scroll: int,
        z_index: int,
    ) -> None: ...
    def _register_graphics(
        self,
        screen: Screen,
        ui_content: UIContent,
        write_position: WritePosition,
        parent_style: str,
        vertical_scroll: int,
        horizontal_scroll: int,
        z_index: int,
    ) -> None: ...
    def _scroll_right(self, max: int | None = None) -> NotImplementedOrNone: ...
    def _scroll_left(self) -> NotImplementedOrNone: ...

class ConditionalContainer(Container):
    content: AnyContainer
    alternative_content: AnyContainer | None
    filter: FilterOrBool
    def __init__(
        self,
        content: AnyContainer,
        filter: FilterOrBool,
        alternative_content: AnyContainer | None = None,
    ) -> None: ...
    def __repr__(self) -> str: ...
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
    def get_children(self) -> list[Container]: ...

class DynamicContainer(Container):
    get_container: Callable[[], AnyContainer]
    def __init__(self, get_container: Callable[[], AnyContainer]) -> None: ...
    def _get_container(self) -> Container: ...
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
    def is_modal(self) -> bool: ...
    def get_key_bindings(self) -> KeyBindingsBase | None: ...
    def get_children(self) -> list[Container]: ...

class ScrollableContainer(Protocol):
    render_info: WindowRenderInfo | None
    vertical_scroll: int

class StatusContainer:
    body: AnyContainer
    status: Callable[[], StatusBarFields | None]
    def __init__(
        self,
        body: AnyContainer,
        status: Callable[[], StatusBarFields | None],
    ) -> None: ...
    def __pt_status__(self) -> StatusBarFields | None: ...
    def __pt_container__(self) -> AnyContainer: ...

class DimensionTuple(NamedTuple):
    min: int
    max: int
    preferred: int
    weight: int = 1

@lru_cache(maxsize=None)
class DummyContainer(Container):
    width: int
    height: int
    def __init__(self, width: int = 0, height: int = 0) -> None: ...
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
    def get_children(self) -> list[Container]: ...

class MarginContainer(Window):
    margin: Margin
    target: ScrollableContainer
    render_info: WindowRenderInfo | None
    content: FormattedTextControl
    always_hide_cursor = to_filter(True)
    write_position: WritePosition | None
    def __init__(self, margin: Margin, target: ScrollableContainer) -> None: ...
    def create_fragments(self) -> StyleAndTextTuples: ...
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
    def _write_to_screen_deferred(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None: ...
    def is_modal(self) -> bool: ...
    def get_key_bindings(self) -> KeyBindingsBase | None: ...
    def get_children(self) -> list[Container]: ...
