__all__ = [
    "PosixStdinReader",
]

class PosixStdinReader:
    stdin_fd: int
    errors: str
    _stdin_decoder_cls: str
    _stdin_decoder = self._stdin_decoder_cls(errors=errors)
    closed = False
    def __init__(
        self,
        stdin_fd: int,
        errors: str = "surrogateescape",
        encoding: str = "utf-8",
    ) -> None: ...
    def read(self, count: int = 1024) -> str: ...
