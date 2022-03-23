"""Initiate logging for euporie."""

from __future__ import annotations

import logging
import logging.config
import sys
from collections import deque
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, cast

from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.patch_stdout import StdoutProxy
from prompt_toolkit.widgets import SearchToolbar
from rich.console import Console

from euporie.config import config
from euporie.tab import Tab
from euporie.widgets.formatted_text_area import FormattedTextArea

if TYPE_CHECKING:
    from types import TracebackType
    from typing import IO, Callable, Optional

    from prompt_toolkit.formatted_text import StyleAndTextTuples

__all__ = ["setup_logs", "QueueHandler", "LogView"]

LOG_QUEUE: "deque" = deque(maxlen=1000)


def setup_logs() -> "None":
    """Configures the logger for euporie."""
    # Pytype used TypedDicts to validate the dictionary structure, but I cannot get
    # this to work for some reason...
    logging.config.dictConfig(  # type: ignore
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "plain_format": {
                    "format": "{asctime} {levelname:>7} [{name}.{funcName}:{lineno}] {message}",
                    "style": "{",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "rich_format": {
                    "format": "{message}",
                    "style": "{",
                    "datefmt": "%Y%m%d.%H%M%S",
                },
            },
            "handlers": {
                "stdout": {
                    "level": "DEBUG"
                    if config.debug and config.log_file == "-"
                    else "CRITICAL",
                    "class": "rich.logging.RichHandler",
                    "formatter": "rich_format",
                    "console": Console(
                        file=cast("IO[str]", StdoutProxy(raw=True)),
                    ),
                    "markup": False,
                },
                **(
                    {
                        "file": {
                            "level": "DEBUG" if config.debug else "ERROR",
                            "class": "logging.FileHandler",
                            "filename": "/dev/stdout"
                            if config.log_file == "-"
                            else config.log_file,
                            "formatter": "plain_format",
                        }
                    }
                    if config.log_file
                    else {}
                ),
                "internal": {
                    "level": "DEBUG" if config.debug else "INFO",
                    "class": "euporie.log.QueueHandler",
                    "queue": LOG_QUEUE,
                },
            },
            "loggers": {
                "euporie": {
                    "level": "DEBUG" if config.debug else "INFO",
                    "handlers": ["internal", "stdout"]
                    + ([] if not config.log_file else ["file"]),
                    "propagate": False,
                },
            },
            "root": {"handlers": ["internal"]},
        }
    )


class QueueHandler(logging.Handler):
    """This handler store logs events into a queue."""

    hook_id = 0
    hooks: "dict[int, Callable]" = {}

    def __init__(self, queue: "deque") -> "None":
        """Initialize an instance, using the passed queue."""
        logging.Handler.__init__(self)
        self.queue = queue

    def emit(self, record: "logging.LogRecord") -> "None":
        """Queue unformatted records, as they will be formatted when accessed."""
        self.queue.append(record)
        for hook in self.hooks.values():
            if callable(hook):
                hook(record)

    @classmethod
    def hook(cls, hook: "Callable") -> "int":
        """Adds a hook to run after each log entry.

        Args:
            hook: The hook function to add

        Returns:
            The hook id
        """
        hook_id = cls.hook_id
        cls.hook_id += 1
        cls.hooks[hook_id] = hook
        return hook_id

    @classmethod
    def unhook(cls, hook_id: "int") -> "None":
        """Removes a hook function.

        Args:
            hook_id: The ID of the hook function to remove
        """
        if hook_id in cls.hooks:
            del cls.hooks[hook_id]


class LogView(Tab):
    """A tab which allows you to view log entries."""

    def __init__(self) -> "None":
        """Builds the tab's contents.

        Also hooks into the queue handler to update the log.
        """
        super().__init__()
        self.formatter = logging.Formatter()
        # Build the container
        self.search_field = SearchToolbar(
            text_if_not_searching=[("class:not-searching", "Press '/' to search.")]
        )
        self.text_area = FormattedTextArea(
            formatted_text=[],
            read_only=True,
            scrollbar=True,
            line_numbers=True,
            search_field=self.search_field,
            focus_on_click=True,
            wrap_lines=True,
            dont_extend_width=False,
        )
        self.container = HSplit([self.text_area, self.search_field])
        # Add text to the textarea
        for record in LOG_QUEUE:
            self.add_record(record)
        # Hook the queue handler
        self.hook_id = QueueHandler.hook(self.add_record)

    def render(self, record: "logging.LogRecord") -> "StyleAndTextTuples":
        """Converts a log record to formatted text.

        Args:
            record: The log record to format

        Returns:
            A list of style and text tuples describing the log record

        """
        date = self.formatter.formatTime(record, "%Y%m%d.%H%M%S")
        record.message = record.getMessage()
        msg = self.formatter.formatMessage(record)
        formatted_record: "StyleAndTextTuples" = [
            ("class:log.date", f"{date} "),
            (f"class:log.level.{record.levelname}", f"{record.levelname:>7} "),
            ("class:log.msg", f"{msg} "),
            ("class:log.ref", f"{record.name}.{record.funcName}:{record.lineno} "),
            ("", "\n"),
        ]

        return formatted_record

    def add_record(self, record: "logging.LogRecord") -> "None":
        """Adds a single new record to the textarea.

        Args:
            record: The log record to add

        """
        cp = self.text_area.buffer.cursor_position
        self.text_area.formatted_text += self.render(record)
        self.text_area.buffer.cursor_position = cp

    @property
    def title(self) -> "str":
        """Returns the title of this tab."""
        return f"Logs ({Path(config.log_file)})"


class stdout_to_log:
    """A decorator which captures standard output and logs it."""

    def __init__(
        self, log: "logging.Logger", output: "str" = "Literal['stdout','stderr']"
    ) -> "None":
        self.log = log
        self.out = StringIO()
        self.output = output

    def __enter__(self) -> "None":
        if self.output == "stderr":
            self._original = sys.stderr
            sys.stderr = self.out
        else:
            self._original = sys.stdout
            sys.stdout = self.out

    def __exit__(
        self,
        exc_type: "Optional[type[BaseException]]",
        exc_value: "Optional[BaseException]",
        exc_traceback: "Optional[TracebackType]",
    ) -> "None":
        if self.output == "stderr":
            sys.stderr = self._original
        else:
            sys.stdout = self._original
        if exc_type is not None:
            self.out.seek(0)
            for line in self.out.readlines():
                self.log.debug(str(line).strip())
        self.out.close()
