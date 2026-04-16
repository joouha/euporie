import logging
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING

from apptk.cache import FastDictCache
from apptk.data_structures import DiInt, Point

if TYPE_CHECKING:
    from .containers import Window

_CHAR_CACHE: FastDictCache[tuple[str, str], Char] = FastDictCache(
    Char, size=1000 * 1000
)
Transparent = "[transparent]"
log = logging.getLogger(__name__)

__all__ = [
    "Char",
    "Screen",
]

class Char:
    __slots__ = ("char", "style", "width")
    display_mappings: dict[str, str] = {
        "\x00": "^@",  # Control space
        "\x01": "^A",
        "\x02": "^B",
        "\x03": "^C",
        "\x04": "^D",
        "\x05": "^E",
        "\x06": "^F",
        "\x07": "^G",
        "\x08": "^H",
        "\x09": "^I",
        "\x0a": "^J",
        "\x0b": "^K",
        "\x0c": "^L",
        "\x0d": "^M",
        "\x0e": "^N",
        "\x0f": "^O",
        "\x10": "^P",
        "\x11": "^Q",
        "\x12": "^R",
        "\x13": "^S",
        "\x14": "^T",
        "\x15": "^U",
        "\x16": "^V",
        "\x17": "^W",
        "\x18": "^X",
        "\x19": "^Y",
        "\x1a": "^Z",
        "\x1b": "^[",  # Escape
        "\x1c": "^\\",
        "\x1d": "^]",
        "\x1e": "^^",
        "\x1f": "^_",
        "\x7f": "^?",  # ASCII Delete (backspace).
        # Special characters. All visualized like Vim does.
        "\x80": "<80>",
        "\x81": "<81>",
        "\x82": "<82>",
        "\x83": "<83>",
        "\x84": "<84>",
        "\x85": "<85>",
        "\x86": "<86>",
        "\x87": "<87>",
        "\x88": "<88>",
        "\x89": "<89>",
        "\x8a": "<8a>",
        "\x8b": "<8b>",
        "\x8c": "<8c>",
        "\x8d": "<8d>",
        "\x8e": "<8e>",
        "\x8f": "<8f>",
        "\x90": "<90>",
        "\x91": "<91>",
        "\x92": "<92>",
        "\x93": "<93>",
        "\x94": "<94>",
        "\x95": "<95>",
        "\x96": "<96>",
        "\x97": "<97>",
        "\x98": "<98>",
        "\x99": "<99>",
        "\x9a": "<9a>",
        "\x9b": "<9b>",
        "\x9c": "<9c>",
        "\x9d": "<9d>",
        "\x9e": "<9e>",
        "\x9f": "<9f>",
        # For the non-breaking space: visualize like Emacs does by default.
        # (Print a space, but attach the 'nbsp' class that applies the
        # underline style.)
        "\xa0": " ",
    }
    char: str
    style: str
    width: str
    def __init__(self, char: str = " ", style: str = "") -> None: ...
    def _equal(self, other: Char) -> bool: ...
    def _not_equal(self, other: Char) -> bool: ...
    def __repr__(self) -> str: ...

class Screen:
    data_buffer: ChainBuffer
    zero_width_escapes: defaultdict[int, defaultdict[int, str]]
    cursor_positions: dict[Window, Point]
    show_cursor = True
    menu_positions: dict[Window, Point]
    width: int
    height: int
    visible_windows_to_write_positions: dict[Window, WritePosition]
    _draw_float_functions = functions[1:]
    def __init__(
        self,
        default_char: Char | None = None,
        initial_width: int = 0,
        initial_height: int = 0,
    ) -> None: ...
    @property
    def visible_windows(self) -> list[Window]: ...
    def set_cursor_position(self, window: Window, position: Point) -> None: ...
    def set_menu_position(self, window: Window, position: Point) -> None: ...
    def get_cursor_position(self, window: Window) -> Point: ...
    def get_menu_position(self, window: Window) -> Point: ...
    def draw_with_z_index(
        self, z_index: int, draw_func: Callable[[], None]
    ) -> None: ...
    def draw_all_floats(self) -> None: ...
    def append_style_to_content(self, style_str: str) -> None: ...
    def fill_area(
        self,
        write_position: WritePosition,
        style: str = "",
        after: bool = False,
    ) -> None: ...

class WritePosition:
    xpos: int
    ypos: int
    width: int
    height: int
    bbox: DiInt | None
    def __init__(
        self,
        xpos: int,
        ypos: int,
        width: int,
        height: int,
        bbox: DiInt | None = None,
    ) -> None: ...
    def __repr__(self) -> str: ...

class ChainBuffer(dict):
    layers = {0: base}
    def __init__(self, base: defaultdict[int, defaultdict[int, str]]) -> None: ...
    def add_layer(self, z_index: int) -> None: ...
    def __missing__(self, key: int) -> str: ...
    def flatten(self) -> defaultdict[int, defaultdict[int, str]]: ...
