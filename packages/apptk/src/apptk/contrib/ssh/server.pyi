import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, TextIO, cast

import asyncssh
from apptk.application.current import AppSession
from apptk.data_structures import Size
from apptk.input import PipeInput
from apptk.output.vt100 import Vt100_Output

__all__ = [
    "PromptToolkitSSHServer",
    "PromptToolkitSSHSession",
]

class PromptToolkitSSHSession(asyncssh.SSHServerSession):
    interact: Callable[[PromptToolkitSSHSession], Coroutine[Any, Any, None]]
    enable_cpr: bool
    interact_task: asyncio.Task[None] | None
    _chan: Any | None
    app_session: AppSession | None
    _input: PipeInput | None
    _output: Vt100_Output | None
    stdout = cast(TextIO, Stdout())
    def __init__(
        self,
        interact: Callable[[PromptToolkitSSHSession], Coroutine[Any, Any, None]],
        *,
        enable_cpr: bool,
    ) -> None: ...
    def _get_size(self) -> Size: ...
    def connection_made(self, chan: Any) -> None: ...
    def shell_requested(self) -> bool: ...
    def session_started(self) -> None: ...
    async def _interact(self) -> None: ...
    def terminal_size_changed(
        self,
        width: int,
        height: int,
        pixwidth: object,
        pixheight: object,
    ) -> None: ...
    def data_received(self, data: str, datatype: object) -> None: ...

class PromptToolkitSSHServer(asyncssh.SSHServer):
    interact: Callable[[PromptToolkitSSHSession], Coroutine[Any, Any, None]]
    enable_cpr: bool
    def __init__(
        self,
        interact: Callable[[PromptToolkitSSHSession], Coroutine[Any, Any, None]],
        *,
        enable_cpr: bool = True,
    ) -> None: ...
    def begin_auth(self, username: str) -> bool: ...
    def session_requested(self) -> PromptToolkitSSHSession: ...
