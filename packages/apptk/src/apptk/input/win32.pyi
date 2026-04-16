from abc import abstractmethod
from collections.abc import Callable, Iterable, Iterator
from contextlib import AbstractContextManager
from ctypes import Array
from ctypes.wintypes import DWORD, HANDLE
from typing import ContextManager, TextIO

from apptk.key_binding.key_processor import KeyPress
from apptk.keys import Keys
from apptk.win32_types import (
    INPUT_RECORD,
    KEY_EVENT_RECORD,
    MOUSE_EVENT_RECORD,
)

from .base import Input
from .vt100_parser import Vt100Parser

FROM_LEFT_1ST_BUTTON_PRESSED = 0x1
RIGHTMOST_BUTTON_PRESSED = 0x2
MOUSE_MOVED = 0x0001
MOUSE_WHEELED = 0x0004
ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200

__all__ = [
    "ConsoleInputReader",
    "Win32Input",
    "attach_win32_input",
    "cooked_mode",
    "detach_win32_input",
    "raw_mode",
]

def attach_win32_input(
    input: _Win32InputBase,
    callback: Callable[[], None],
) -> AbstractContextManager[None]: ...
def detach_win32_input(input: _Win32InputBase) -> AbstractContextManager[None]: ...

class _Win32InputBase(Input):
    win32_handles = _Win32Handles()
    def __init__(self) -> None: ...
    @property
    @abstractmethod
    def handle(self) -> HANDLE: ...

class Win32Input(_Win32InputBase):
    _use_virtual_terminal_input = _is_win_vt100_input_enabled()
    console_input_reader: Vt100ConsoleInputReader | ConsoleInputReader
    def __init__(self, stdin: TextIO | None = None) -> None: ...
    def attach(
        self, input_ready_callback: Callable[[], None]
    ) -> ContextManager[None]: ...
    def detach(self) -> ContextManager[None]: ...
    def read_keys(self) -> list[KeyPress]: ...
    def flush_keys(self) -> list[KeyPress]: ...
    @property
    def closed(self) -> bool: ...
    def raw_mode(self) -> ContextManager[None]: ...
    def cooked_mode(self) -> ContextManager[None]: ...
    def fileno(self) -> int: ...
    def typeahead_hash(self) -> str: ...
    def close(self) -> None: ...
    @property
    def handle(self) -> HANDLE: ...

class ConsoleInputReader:
    mappings = {
        b"\x1b": Keys.Escape,
        b"\x00": Keys.ControlSpace,  # Control-Space (Also for Ctrl-@)
        b"\x01": Keys.ControlA,  # Control-A (home)
        b"\x02": Keys.ControlB,  # Control-B (emacs cursor left)
        b"\x03": Keys.ControlC,  # Control-C (interrupt)
        b"\x04": Keys.ControlD,  # Control-D (exit)
        b"\x05": Keys.ControlE,  # Control-E (end)
        b"\x06": Keys.ControlF,  # Control-F (cursor forward)
        b"\x07": Keys.ControlG,  # Control-G
        b"\x08": Keys.ControlH,  # Control-H (8) (Identical to '\b')
        b"\x09": Keys.ControlI,  # Control-I (9) (Identical to '\t')
        b"\x0a": Keys.ControlJ,  # Control-J (10) (Identical to '\n')
        b"\x0b": Keys.ControlK,  # Control-K (delete until end of line; vertical tab)
        b"\x0c": Keys.ControlL,  # Control-L (clear; form feed)
        b"\x0d": Keys.ControlM,  # Control-M (enter)
        b"\x0e": Keys.ControlN,  # Control-N (14) (history forward)
        b"\x0f": Keys.ControlO,  # Control-O (15)
        b"\x10": Keys.ControlP,  # Control-P (16) (history back)
        b"\x11": Keys.ControlQ,  # Control-Q
        b"\x12": Keys.ControlR,  # Control-R (18) (reverse search)
        b"\x13": Keys.ControlS,  # Control-S (19) (forward search)
        b"\x14": Keys.ControlT,  # Control-T
        b"\x15": Keys.ControlU,  # Control-U
        b"\x16": Keys.ControlV,  # Control-V
        b"\x17": Keys.ControlW,  # Control-W
        b"\x18": Keys.ControlX,  # Control-X
        b"\x19": Keys.ControlY,  # Control-Y (25)
        b"\x1a": Keys.ControlZ,  # Control-Z
        b"\x1c": Keys.ControlBackslash,  # Both Control-\ and Ctrl-|
        b"\x1d": Keys.ControlSquareClose,  # Control-]
        b"\x1e": Keys.ControlCircumflex,  # Control-^
        b"\x1f": Keys.ControlUnderscore,  # Control-underscore (Also for Ctrl-hyphen.)
        b"\x7f": Keys.Backspace,  # (127) Backspace   (ASCII Delete.)
    }
    keycodes = {
        # Home/End
        33: Keys.PageUp,
        34: Keys.PageDown,
        35: Keys.End,
        36: Keys.Home,
        # Arrows
        37: Keys.Left,
        38: Keys.Up,
        39: Keys.Right,
        40: Keys.Down,
        45: Keys.Insert,
        46: Keys.Delete,
        # F-keys.
        112: Keys.F1,
        113: Keys.F2,
        114: Keys.F3,
        115: Keys.F4,
        116: Keys.F5,
        117: Keys.F6,
        118: Keys.F7,
        119: Keys.F8,
        120: Keys.F9,
        121: Keys.F10,
        122: Keys.F11,
        123: Keys.F12,
    }
    LEFT_ALT_PRESSED = 0x0002
    RIGHT_ALT_PRESSED = 0x0001
    SHIFT_PRESSED = 0x0010
    LEFT_CTRL_PRESSED = 0x0008
    RIGHT_CTRL_PRESSED = 0x0004
    _fdcon = None
    recognize_paste: bool
    handle: HANDLE
    def __init__(self, recognize_paste: bool = True) -> None: ...
    def close(self) -> None: ...
    def read(self) -> Iterable[KeyPress]: ...
    def flush_keys(self) -> list[KeyPress]: ...
    def _insert_key_data(self, key_press: KeyPress) -> KeyPress: ...
    def _get_keys(
        self,
        read: DWORD,
        input_records: Array[INPUT_RECORD],
    ) -> Iterator[KeyPress]: ...
    @staticmethod
    def _merge_paired_surrogates(key_presses: list[KeyPress]) -> Iterator[KeyPress]: ...
    @staticmethod
    def _is_paste(keys: list[KeyPress]) -> bool: ...
    def _event_to_key_presses(self, ev: KEY_EVENT_RECORD) -> list[KeyPress]: ...
    def _handle_mouse(self, ev: MOUSE_EVENT_RECORD) -> list[KeyPress]: ...

class Vt100ConsoleInputReader:
    _fdcon = None
    _buffer: list[KeyPress]
    _vt100_parser: Vt100Parser
    handle: HANDLE
    def __init__(self) -> None: ...
    def close(self) -> None: ...
    def read(self) -> Iterable[KeyPress]: ...
    def flush_keys(self) -> list[KeyPress]: ...
    def _get_keys(
        self,
        read: DWORD,
        input_records: Array[INPUT_RECORD],
    ) -> Iterator[str]: ...

class _Win32Handles:
    _handle_callbacks: dict[int, Callable[[], None]]
    _remove_events: dict[int, HANDLE]
    def __init__(self) -> None: ...
    def add_win32_handle(
        self, handle: HANDLE, callback: Callable[[], None]
    ) -> None: ...
    def remove_win32_handle(self, handle: HANDLE) -> Callable[[], None] | None: ...

class raw_mode:
    handle: HANDLE
    use_win10_virtual_terminal_input: bool
    original_mode = original_mode
    def __init__(
        self,
        fileno: int | None = None,
        use_win10_virtual_terminal_input: bool = False,
    ) -> None: ...
    def __enter__(self) -> None: ...
    def _patch(self) -> None: ...
    def __exit__(self, *a: object) -> None: ...

class cooked_mode(raw_mode):
    def _patch(self) -> None: ...
