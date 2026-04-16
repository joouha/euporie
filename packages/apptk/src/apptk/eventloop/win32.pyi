from ctypes.wintypes import HANDLE

WAIT_TIMEOUT = 0x00000102
INFINITE = -1

__all__ = [
    "create_win32_event",
    "wait_for_handles",
]

def wait_for_handles(
    handles: list[HANDLE], timeout: int = INFINITE
) -> HANDLE | None: ...
def create_win32_event() -> HANDLE: ...
