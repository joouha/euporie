from collections.abc import Callable

from apptk.eventloop import InputHook
from apptk.formatted_text import AnyFormattedText

from .application import Application

__all__ = [
    "DummyApplication",
]

class DummyApplication(Application[None]):
    def __init__(self) -> None: ...
    def run(
        self,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
        in_thread: bool = False,
        inputhook: InputHook | None = None,
    ) -> None: ...
    async def run_async(
        self,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
        slow_callback_duration: float = 0.5,
    ) -> None: ...
    async def run_system_command(
        self,
        command: str,
        wait_for_enter: bool = True,
        display_before_text: AnyFormattedText = "",
        wait_text: str = "",
    ) -> None: ...
    def suspend_to_background(self, suspend_group: bool = True) -> None: ...
