import asyncio
import contextvars
import socket
from collections.abc import Callable, Coroutine
from typing import Any, TextIO, cast

from apptk.data_structures import Size
from apptk.formatted_text import AnyFormattedText
from apptk.input import PipeInput
from apptk.output.vt100 import Vt100_Output
from apptk.styles import BaseStyle

from .protocol import (
    TelnetProtocolParser,
)

__all__ = [
    "TelnetServer",
]

def int2byte(number: int) -> bytes: ...

class _ConnectionStdout:
    _encoding: str
    _connection: socket.socket
    _errors = "strict"
    _buffer: list[bytes]
    _closed = False
    def __init__(self, connection: socket.socket, encoding: str) -> None: ...
    def write(self, data: str) -> None: ...
    def isatty(self) -> bool: ...
    def flush(self) -> None: ...
    def close(self) -> None: ...
    @property
    def encoding(self) -> str: ...
    @property
    def errors(self) -> str: ...

class TelnetConnection:
    conn: socket.socket
    addr: tuple[str, int]
    interact: Callable[[TelnetConnection], Coroutine[Any, Any, None]]
    server: TelnetServer
    encoding: str
    style: BaseStyle | None
    _closed = False
    _ready: asyncio.Event
    vt100_input: PipeInput
    enable_cpr: bool
    vt100_output: Vt100_Output | None
    size: Size
    stdout = cast(TextIO, _ConnectionStdout(conn, encoding=encoding))
    parser: TelnetProtocolParser
    context: contextvars.Context | None
    def __init__(
        self,
        conn: socket.socket,
        addr: tuple[str, int],
        interact: Callable[[TelnetConnection], Coroutine[Any, Any, None]],
        server: TelnetServer,
        encoding: str,
        style: BaseStyle | None,
        vt100_input: PipeInput,
        enable_cpr: bool = True,
    ) -> None: ...
    async def run_application(self) -> None: ...
    def feed(self, data: bytes) -> None: ...
    def close(self) -> None: ...
    def send(self, formatted_text: AnyFormattedText) -> None: ...
    def send_above_prompt(self, formatted_text: AnyFormattedText) -> None: ...
    def _run_in_terminal(self, func: Callable[[], None]) -> None: ...
    def erase_screen(self) -> None: ...

class TelnetServer:
    host: str
    port: int
    interact: Callable[[TelnetConnection], Coroutine[Any, Any, None]]
    encoding: str
    style: BaseStyle | None
    enable_cpr: bool
    _run_task: asyncio.Task[None] | None
    _application_tasks: list[asyncio.Task[None]]
    connections: set[TelnetConnection]
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 23,
        interact: Callable[
            [TelnetConnection], Coroutine[Any, Any, None]
        ] = _dummy_interact,
        encoding: str = "utf-8",
        style: BaseStyle | None = None,
        enable_cpr: bool = True,
    ) -> None: ...
    @classmethod
    def _create_socket(cls, host: str, port: int) -> socket.socket: ...
    async def run(self, ready_cb: Callable[[], None] | None = None) -> None: ...
    def start(self) -> None: ...
    async def stop(self) -> None: ...
    def _accept(self, listen_socket: socket.socket) -> None: ...
