from contextlib import AbstractContextManager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apptk.input.base import Input
    from apptk.output.base import Output

    from .application import Application

class AppSession:
    _input: Input | None
    _output: Output | None
    app: Application[Any] | None
    def __init__(
        self, input: Input | None = None, output: Output | None = None
    ) -> None: ...
    @property
    def input(self) -> Input: ...
    @property
    def output(self) -> Output: ...
    def __repr__(self) -> str: ...

_current_app_session: ContextVar[AppSession] = ContextVar(
    "_current_app_session", default=AppSession()
)

__all__ = [
    "AppSession",
    "create_app_session",
    "create_app_session_from_tty",
    "get_app",
    "get_app_or_none",
    "get_app_session",
    "set_app",
]

def get_app_session() -> AppSession: ...
def get_app() -> Application[Any]: ...
def get_app_or_none() -> Application[Any] | None: ...
def set_app(app: Application[Any]) -> AbstractContextManager[None]: ...
def create_app_session(
    input: Input | None = None,
    output: Output | None = None,
) -> AbstractContextManager[AppSession]: ...
def create_app_session_from_tty() -> AbstractContextManager[AppSession]: ...
