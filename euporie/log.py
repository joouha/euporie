"""Initiate logging for euporie."""

from __future__ import annotations

import logging
import logging.config
import sys
import textwrap
from collections import deque
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.formatted_text.base import FormattedText
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.shortcuts.utils import print_formatted_text
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import SearchToolbar

from euporie.config import config
from euporie.style import LOG_STYLE
from euporie.tab import Tab
from euporie.widgets.formatted_text_area import FormattedTextArea

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Any, Callable, Optional, TextIO

__all__ = ["setup_logs", "QueueHandler", "LogView"]

log = logging.getLogger(__name__)

LOG_QUEUE: "deque" = deque(maxlen=1000)


class FormattedTextHandler(logging.StreamHandler):
    """Format log records for display on the standard output."""

    formatter: "FtFormatter"

    def __init__(self, *args: "Any", style: "Optional[Style]" = None, **kwargs: "Any"):
        super().__init__(*args, **kwargs)
        self.output = create_output(stdout=self.stream)
        self.style = style or Style(LOG_STYLE)

    def ft_format(self, record: "logging.LogRecord") -> "FormattedText":
        """Format the specified record."""
        if self.formatter is not None:
            return self.formatter.ft_format(record, width=self.output.get_size()[1])
        else:
            return FormattedText([])

    def emit(self, record: "logging.LogRecord") -> "None":
        """Emit a formatted record."""
        try:
            msg = self.ft_format(record)
            print_formatted_text(msg, style=self.style, output=self.output)
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


class QueueHandler(logging.Handler):
    """This handler store logs events into a queue."""

    hook_id = 0
    hooks: "dict[int, Callable]" = {}

    def __init__(
        self,
        *args: "Any",
        queue: "deque",
        style: "Optional[Style]" = None,
        **kwargs: "Any",
    ) -> "None":
        """Initialize an instance, using the passed queue."""
        logging.Handler.__init__(self, *args, **kwargs)
        self.queue = queue
        self.style = style or Style(LOG_STYLE)

    def emit(self, record: "logging.LogRecord") -> "None":
        """Queue unformatted records, as they will be formatted when accessed."""
        message = self.format(record)
        self.queue.append(message)
        for hook in self.hooks.values():
            if callable(hook):
                hook(message)

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


class FtFormatter(logging.Formatter):
    """Base class for formatted text logging formatter."""

    def ft_format(
        self, record: "logging.LogRecord", width: "Optional[int]" = None
    ) -> "FormattedText":
        return FormattedText([])


class LogTabFormatter(FtFormatter):
    """Formats log messages for display in the log view tab."""

    def ft_format(
        self, record: "logging.LogRecord", width: "Optional[int]" = None
    ) -> "FormattedText":
        """Formats a log record as formatted text."""
        record.message = record.getMessage()
        record.asctime = self.formatTime(record, self.datefmt)
        message = self.formatMessage(record)

        return FormattedText(
            [
                ("class:log.date", f"{record.asctime} "),
                (f"class:log.level.{record.levelname}", f"{record.levelname:<7} "),
                ("class:log.msg", message),
                ("class:log.ref", f" {record.name}.{record.funcName}:{record.lineno}"),
                ("", "\n"),
            ]
        )


class StdoutFormatter(FtFormatter):
    datefmt = "%Y-%m-%d %H:%M:%S"

    def __init__(self, *args: "Any", **kwargs: "Any") -> "None":
        super().__init__(*args, **kwargs)
        self.last_date: "Optional[str]" = None

    def ft_format(
        self, record: "logging.LogRecord", width: "Optional[int]" = None
    ) -> "FormattedText":

        if width is None:
            width = get_app_session().output.get_size()[1]

        record.message = record.getMessage()
        record.asctime = self.formatTime(record, self.datefmt)
        message = self.formatMessage(record)
        path_name = Path(record.pathname).name

        date = f"{record.asctime} "
        if date == self.last_date:
            date = " " * len(date)
        else:
            self.last_date = date
        level = f"{record.levelname:>7} "
        ref = f" {path_name}:{record.lineno}"

        msg_lines = textwrap.wrap(
            message,
            width=width,
            initial_indent=" " * (len(date) + len(level) + len(ref)),
            subsequent_indent=" " * (len(date) + len(level)),
        )

        output = [
            ("class:log.date", date),
            (f"class:log.level.{record.levelname}", level),
            (
                "class:log.msg",
                msg_lines[0].strip().ljust(width - (len(date) + len(level) + len(ref))),
            ),
            ("class:log.ref", ref),
        ]
        for line in msg_lines[1:]:
            output += [
                ("", "\n"),
                ("class:log.msg", line),
            ]
        return FormattedText(output)


def setup_logs() -> "None":
    """Configures the logger for euporie."""
    # Pytype used TypedDicts to validate the dictionary structure, but I cannot get
    # this to work for some reason...

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "file_format": {
                "format": "{asctime} {levelname:<7} [{name}.{funcName}:{lineno}] {message}",
                "style": "{",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "stdout_format": {
                "()": "euporie.log.StdoutFormatter",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "log_tab_format": {
                "()": "euporie.log.LogTabFormatter",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            **(
                {
                    "file": {
                        "level": "DEBUG" if config.debug else "ERROR",
                        "class": "logging.FileHandler",
                        "filename": "/dev/stdout"
                        if config.log_file == "-"
                        else config.log_file,
                        "formatter": "file_format",
                    }
                }
                if config.log_file
                else {}
            ),
            "stdout": {
                "level": "DEBUG" if config.debug else "CRITICAL",
                "class": "euporie.log.FormattedTextHandler",
                "formatter": "stdout_format",
                "stream": sys.stdout,
            },
            "log_tab": {
                "level": "DEBUG" if config.debug else "INFO",
                "class": "euporie.log.QueueHandler",
                "formatter": "log_tab_format",
                "queue": LOG_QUEUE,
            },
        },
        "loggers": {
            "euporie": {
                "level": "DEBUG" if config.debug else "INFO",
                "handlers": ["log_tab"]
                + (
                    ["stdout"]
                    if config.log_file in ("-", "/dev/stdout")
                    else (["file"] if config.log_file else [])
                ),
                "propagate": False,
            },
        },
        # Log everything to the internal logger
        "root": {"handlers": ["log_tab"]},
    }
    # Update log_config based on config file
    # log_config.update(config.log_config)
    # Configure the logger
    logging.config.dictConfig(log_config)  # type: ignore


class LogView(Tab):
    """A tab which allows you to view log entries."""

    def __init__(self) -> "None":
        """Builds the tab's contents.

        Also hooks into the queue handler to update the log.
        """
        super().__init__()
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
            wrap_lines=False,
            dont_extend_width=False,
        )
        self.container = HSplit([self.text_area, self.search_field])
        # Add text to the textarea
        for record in LOG_QUEUE:
            self.add_record(record)
        # Hook the queue handler
        self.hook_id = QueueHandler.hook(self.add_record)

    def add_record(self, message: "FormattedText") -> "None":
        """Adds a single new record to the textarea.

        Args:
            message: The formatted log record to add

        """
        cp = self.text_area.buffer.cursor_position
        self.text_area.formatted_text += message
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
        self._original: "Optional[TextIO]" = None

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
        assert self._original is not None
        if self.output == "stderr":
            sys.stderr = self._original
        else:
            sys.stdout = self._original
        if exc_type is not None:
            self.out.seek(0)
            for line in self.out.readlines():
                self.log.debug(str(line).strip())
        self.out.close()
