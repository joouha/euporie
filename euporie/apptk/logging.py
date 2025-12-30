"""Logging related utilities."""

from __future__ import annotations

import logging
import sys
from io import StringIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Literal, TextIO


class stdout_to_log:
    """A context manager which captures standard output and logs it."""

    def __init__(
        self,
        log: logging.Logger,
        output: Literal["stdout", "stderr"] = "stdout",
        level: int = logging.DEBUG,
    ) -> None:
        """Create a new instance of the capturing context manager.

        Args:
            log: The logger to send the output to
            output: Whether to capture the standard output or the standard error
            level: level at which to log output
        """
        self.log = log
        self.level = level
        self.out = StringIO()
        self.output = output
        self._original: TextIO | None = None

    def __enter__(self) -> None:
        """Intercept the standard output when entering the context manager."""
        if self.output == "stderr":
            self._original = sys.stderr
            sys.stderr = self.out
        else:
            self._original = sys.stdout
            sys.stdout = self.out

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        """Replace the standard output, and logs the captured output."""
        assert self._original is not None
        if self.output == "stderr":
            sys.stderr = self._original
        else:
            sys.stdout = self._original
        if exc_type is not None:
            self.out.seek(0)
            for line in self.out.readlines():
                self.log.log(self.level, str(line).strip())
        self.out.close()
