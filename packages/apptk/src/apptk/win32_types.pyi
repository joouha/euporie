from ctypes import Structure, Union, c_char, c_long, c_short, c_ulong
from ctypes.wintypes import BOOL, DWORD, LPVOID, WCHAR, WORD

STD_INPUT_HANDLE = c_ulong(-10)
STD_OUTPUT_HANDLE = c_ulong(-11)
STD_ERROR_HANDLE = c_ulong(-12)
EventTypes = {
    1: "KeyEvent",
    2: "MouseEvent",
    4: "WindowBufferSizeEvent",
    8: "MenuEvent",
    16: "FocusEvent",
}

class COORD(Structure):
    _fields_ = [
        ("X", c_short),  # Short
        ("Y", c_short),  # Short
    ]
    def __repr__(self) -> str: ...

class UNICODE_OR_ASCII(Union):
    _fields_ = [
        ("AsciiChar", c_char),
        ("UnicodeChar", WCHAR),
    ]

class KEY_EVENT_RECORD(Structure):
    _fields_ = [
        ("KeyDown", c_long),  # bool
        ("RepeatCount", c_short),  # word
        ("VirtualKeyCode", c_short),  # word
        ("VirtualScanCode", c_short),  # word
        ("uChar", UNICODE_OR_ASCII),  # Unicode or ASCII.
        ("ControlKeyState", c_long),  # double word
    ]

class MOUSE_EVENT_RECORD(Structure):
    _fields_ = [
        ("MousePosition", COORD),
        ("ButtonState", c_long),  # dword
        ("ControlKeyState", c_long),  # dword
        ("EventFlags", c_long),  # dword
    ]

class WINDOW_BUFFER_SIZE_RECORD(Structure):
    _fields_ = [("Size", COORD)]

class MENU_EVENT_RECORD(Structure):
    _fields_ = [("CommandId", c_long)]  # uint

class FOCUS_EVENT_RECORD(Structure):
    _fields_ = [("SetFocus", c_long)]  # bool

class EVENT_RECORD(Union):
    _fields_ = [
        ("KeyEvent", KEY_EVENT_RECORD),
        ("MouseEvent", MOUSE_EVENT_RECORD),
        ("WindowBufferSizeEvent", WINDOW_BUFFER_SIZE_RECORD),
        ("MenuEvent", MENU_EVENT_RECORD),
        ("FocusEvent", FOCUS_EVENT_RECORD),
    ]

class INPUT_RECORD(Structure):
    _fields_ = [("EventType", c_short), ("Event", EVENT_RECORD)]  # word  # Union.

class SMALL_RECT(Structure):
    _fields_ = [
        ("Left", c_short),
        ("Top", c_short),
        ("Right", c_short),
        ("Bottom", c_short),
    ]

class CONSOLE_SCREEN_BUFFER_INFO(Structure):
    _fields_ = [
        ("dwSize", COORD),
        ("dwCursorPosition", COORD),
        ("wAttributes", WORD),
        ("srWindow", SMALL_RECT),
        ("dwMaximumWindowSize", COORD),
    ]
    def __repr__(self) -> str: ...

class SECURITY_ATTRIBUTES(Structure):
    _fields_ = [
        ("nLength", DWORD),
        ("lpSecurityDescriptor", LPVOID),
        ("bInheritHandle", BOOL),
    ]
