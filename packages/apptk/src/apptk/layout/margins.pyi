import asyncio
import logging
from abc import abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING

from apptk.filters import FilterOrBool
from apptk.formatted_text import (
    StyleAndTextTuples,
)
from apptk.layout.screen import WritePosition
from apptk.mouse_events import MouseEvent

from .controls import UIContent

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Protocol

    from apptk.key_binding.key_bindings import NotImplementedOrNone
    from apptk.layout.containers import Window, WindowRenderInfo
    from apptk.layout.controls import UIContent

    from euporie.core.diagnostics import Report

    from .containers import WindowRenderInfo

log = logging.getLogger(__name__)

__all__ = [
    "ConditionalMargin",
    "Margin",
    "NumberedMargin",
    "PromptMargin",
    "ScrollbarMargin",
]

class Margin:
    @abstractmethod
    def get_width(self, get_ui_content: Callable[[], UIContent]) -> int: ...
    @abstractmethod
    def create_margin(
        self,
        window_render_info: WindowRenderInfo,
        width: int,
        height: int,
    ) -> StyleAndTextTuples: ...

class NumberedMargin(Margin):
    relative: FilterOrBool
    display_tildes: FilterOrBool
    style = "class:line-number"
    diagnostics: Report | Callable[[], Report] | None
    show_diagnostics: FilterOrBool
    def __init__(
        self,
        relative: FilterOrBool = False,
        diagnostics: Report | Callable[[], Report] | None = None,
        show_diagnostics: FilterOrBool = False,
    ) -> None: ...
    def get_width(self, get_ui_content: Callable[[], UIContent]) -> int: ...
    def create_margin(
        self,
        window_render_info: WindowRenderInfo,
        width: int,
        height: int,
    ) -> StyleAndTextTuples: ...

class ConditionalMargin(Margin):
    margin: Margin
    filter: FilterOrBool
    def __init__(self, margin: Margin, filter: FilterOrBool) -> None: ...
    def get_width(self, get_ui_content: Callable[[], UIContent]) -> int: ...
    def create_margin(
        self,
        window_render_info: WindowRenderInfo,
        width: int,
        height: int,
    ) -> StyleAndTextTuples: ...

class ClickableMargin(Margin):
    write_position: WritePosition | None
    margin_window: Window
    def set_margin_window(self, margin_window: Window) -> None: ...

class ScrollbarMargin(ClickableMargin):
    display_arrows: FilterOrBool
    up_arrow_symbol: str
    down_arrow_symbol: str
    eighths = "█▇▆▅▄▃▂▁ "
    smooth: bool
    style: str
    repeat_task: asyncio.Task[None] | None
    dragging = False
    drag_start_scroll = 0
    drag_start_offset = 0.0
    thumb_top = 0.0
    thumb_size = 0.0
    target_render_info: WindowRenderInfo | None
    track_height: int
    def __init__(
        self,
        display_arrows: FilterOrBool = True,
        up_arrow_symbol: str = "▴",
        down_arrow_symbol: str = "▾",
        autohide: FilterOrBool = False,
        smooth: bool = True,
        style: str = "",
    ) -> None: ...
    def get_width(self, get_ui_content: Callable[[], UIContent]) -> int: ...
    def create_margin(
        self,
        window_render_info: WindowRenderInfo | None,
        width: int,
        height: int,
    ) -> StyleAndTextTuples: ...
    def _mouse_handler(
        self,
        mouse_event: MouseEvent,
        repeated: bool = False,
    ) -> NotImplementedOrNone: ...
    def mouse_handler(self, mouse_event: MouseEvent) -> NotImplementedOrNone: ...
    async def repeat(self, mouse_event: MouseEvent, timeout: float = 0.1) -> None: ...

class PromptMargin(Margin):
    get_prompt: Callable[[], StyleAndTextTuples]
    get_continuation: None | Callable[[int, int, bool], StyleAndTextTuples]
    def __init__(
        self,
        get_prompt: Callable[[], StyleAndTextTuples],
        get_continuation: None | Callable[[int, int, bool], StyleAndTextTuples] = None,
    ) -> None: ...
    def get_width(self, get_ui_content: Callable[[], UIContent]) -> int: ...
    def create_margin(
        self,
        window_render_info: WindowRenderInfo,
        width: int,
        height: int,
    ) -> StyleAndTextTuples: ...

class ScrollableContainer(Protocol):
    render_info: WindowRenderInfo | None
    vertical_scroll: int

class BorderMargin(Margin):
    char: str
    style: str
    def __init__(self, char: str = "│", style: str = "") -> None: ...
    def get_width(self, get_ui_content: Callable[[], UIContent]) -> int: ...
    def create_margin(
        self,
        window_render_info: WindowRenderInfo,
        width: int,
        height: int,
    ) -> StyleAndTextTuples: ...

class OverflowMargin(Margin):
    def get_width(self, get_ui_content: Callable[[], UIContent]) -> int: ...
    def create_margin(
        self,
        window_render_info: WindowRenderInfo,
        width: int,
        height: int,
    ) -> StyleAndTextTuples: ...
