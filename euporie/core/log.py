"""Initiate logging for euporie.core."""

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
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.renderer import (
    print_formatted_text as renderer_print_formatted_text,
)
from prompt_toolkit.shortcuts.utils import print_formatted_text
from prompt_toolkit.styles.pygments import style_from_pygments_cls
from prompt_toolkit.styles.style import Style, merge_styles
from pygments.styles import get_style_by_name

from euporie.core.formatted_text.utils import indent, lex, wrap
from euporie.core.style import LOG_STYLE

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Any, Callable, Optional, TextIO, Type

    from prompt_toolkit.formatted_text.base import StyleAndTextTuples
    from prompt_toolkit.styles.base import BaseStyle

    from euporie.core.config import Config

log = logging.getLogger(__name__)

LOG_QUEUE: "deque" = deque(maxlen=1000)


def dict_merge(target_dict: "dict", input_dict: "dict") -> "None":
    """Merge the second dictionary onto the first."""
    for k in input_dict:
        if k in target_dict:
            if isinstance(target_dict[k], dict) and isinstance(input_dict[k], dict):
                dict_merge(target_dict[k], input_dict[k])
            elif isinstance(target_dict[k], list) and isinstance(input_dict[k], list):
                target_dict[k] = [*target_dict[k], *input_dict[k]]
            else:
                target_dict[k] = input_dict[k]
        else:
            target_dict[k] = input_dict[k]


class FormattedTextHandler(logging.StreamHandler):
    """Format log records for display on the standard output."""

    formatter: "FtFormatter"

    def __init__(
        self,
        *args: "Any",
        share_stream: "bool" = True,
        style: "Optional[BaseStyle]" = None,
        pygments_theme: "str" = "euporie",
        **kwargs: "Any",
    ) -> "None":
        """Creates a new log handler instance."""
        super().__init__(*args, **kwargs)
        self.output = create_output(stdout=self.stream)
        self.style = style or merge_styles(
            [
                style_from_pygments_cls(get_style_by_name(pygments_theme)),
                style or Style(LOG_STYLE),
            ]
        )
        self.share_stream = share_stream

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
            if self.share_stream:
                print_formatted_text(
                    msg,
                    end="",
                    style=self.style,
                    output=self.output,
                    include_default_pygments_style=False,
                )
            else:
                renderer_print_formatted_text(
                    output=self.output,
                    formatted_text=msg,
                    style=self.style,
                )

        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


class QueueHandler(logging.Handler):
    """This handler store logs events into a queue."""

    formatter: "FtFormatter"
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
        message = self.formatter.ft_format(record)
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

    def __init__(self, *args: "Any", **kwargs: "Any") -> "None":
        """Creates a new formatter instance."""
        super().__init__(*args, **kwargs)
        self.datefmt = self.datefmt or "%Y-%m-%d %H:%M:%S"

    def prepare(
        self, record: "logging.LogRecord", width: "Optional[int]" = None
    ) -> "logging.LogRecord":
        """Format certain attributes on the log record."""
        record.asctime = self.formatTime(record, self.datefmt)
        record.message = record.getMessage()
        record.exc_text = ""
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        return record

    def format_traceback(self, tb: "str") -> "StyleAndTextTuples":
        """Formats a traceback string using pygments."""
        return lex([("", tb)], "pytb")

    def ft_format(
        self, record: "logging.LogRecord", width: "Optional[int]" = None
    ) -> "FormattedText":
        """Formats a log record as :py:class:`FormattedText`."""
        return FormattedText([])


class LogTabFormatter(FtFormatter):
    """Formats log messages for display in the log view tab."""

    def ft_format(
        self, record: "logging.LogRecord", width: "Optional[int]" = None
    ) -> "FormattedText":
        """Formats a log record as formatted text."""
        record = self.prepare(record)
        output: "StyleAndTextTuples" = [
            ("class:pygments.literal.date", f"{record.asctime}"),
            ("", " "),
            (f"class:log.level.{record.levelname}", f"{record.levelname}"),
            ("", " " * (10 - len(record.levelname))),
            ("class:log,msg", record.message),
            ("", " "),
            (
                "class:pygments.comment",
                f"{record.name}.{record.funcName}:{record.lineno}",
            ),
            ("", "\n"),
        ]
        if record.exc_text:
            output += self.format_traceback(record.exc_text) + [("", "\n")]
        return FormattedText(output)


class StdoutFormatter(FtFormatter):
    """A log formatter for formatting log entries for display on the standard output."""

    def __init__(self, *args: "Any", **kwargs: "Any") -> "None":
        """Creates a new formatter instance."""
        super().__init__(*args, **kwargs)
        self.last_date: "Optional[str]" = None

    def ft_format(
        self, record: "logging.LogRecord", width: "Optional[int]" = None
    ) -> "FormattedText":
        """Formats log records for display on the standard output."""
        if width is None:
            width = get_app_session().output.get_size()[1]

        record = self.prepare(record)
        # path_name = Path(record.pathname).name

        date = f"{record.asctime}"
        if date == self.last_date:
            date = " " * len(date)
        else:
            self.last_date = date
        # ref = f"{path_name}:{record.lineno}"
        ref = f"{record.name}.{record.funcName}:{record.lineno}"

        msg_pad = len(date) + 10
        msg_pad_1st_line = msg_pad + 1 + len(ref)

        msg_lines = textwrap.wrap(
            record.message,
            width=width,
            initial_indent=" " * msg_pad_1st_line,
            subsequent_indent=" " * msg_pad,
        )

        output: "StyleAndTextTuples" = [
            ("class:pygments.literal.date", date),
            ("", " " * (9 - len(record.levelname))),
            (f"class:log.level.{record.levelname}", record.levelname),
            ("", " "),
            (
                "class:pygments.text",
                msg_lines[0].strip().ljust(width - msg_pad_1st_line),
            ),
            ("", " "),
            ("class:pygments.comment", ref),
        ]
        for line in msg_lines[1:]:
            output += [
                ("", "\n"),
                ("class:log,msg", line),
            ]
        if record.exc_text:
            output += indent(
                wrap(
                    self.format_traceback(record.exc_text),
                    width=width - msg_pad,
                ),
                margin=" " * msg_pad,
            )
        output += [("", "\n")]
        return FormattedText(output)


def setup_logs(config: "Config") -> "None":
    """Configures the logger for euporie."""
    log_file_is_stdout = config.log_file in ("-", "/dev/stdout")

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
                "()": "euporie.core.log.StdoutFormatter",
            },
            "log_tab_format": {
                "()": "euporie.core.log.LogTabFormatter",
            },
        },
        "handlers": {
            **(
                {
                    "file": {
                        "level": config.log_level.upper() or "ERROR",
                        "class": "logging.FileHandler",
                        "filename": Path(config.log_file).expanduser(),
                        "formatter": "file_format",
                    }
                }
                if config.log_file and not log_file_is_stdout
                else {}
            ),
            "stdout": {
                "level": config.log_level.upper()
                if config.log_level and log_file_is_stdout
                else "CRITICAL",
                "class": "euporie.core.log.FormattedTextHandler",
                "pygments_theme": config.syntax_theme,
                "formatter": "stdout_format",
                "stream": sys.stdout,
            },
            "log_tab": {
                "level": config.log_level.upper() or "INFO",
                "class": "euporie.core.log.QueueHandler",
                "formatter": "log_tab_format",
                "queue": LOG_QUEUE,
            },
        },
        "loggers": {
            "euporie": {
                "level": config.log_level.upper() or "INFO",
                "handlers": ["log_tab", "stdout"]
                + (["file"] if not log_file_is_stdout and config.log_file else []),
                "propagate": False,
            },
        },
        # Log everything to the internal logger
        "root": {"handlers": ["log_tab"]},
    }
    # Update log_config based additional config provided
    if config.log_config:
        import json

        extra_config = json.loads(config.log_config)
        dict_merge(log_config, extra_config)
    # Configure the logger
    # Pytype used TypedDicts to validate the dictionary structure, but I cannot get
    # this to work for some reason...
    logging.config.dictConfig(log_config)  # type: ignore


class stdout_to_log:
    """A decorator which captures standard output and logs it."""

    def __init__(
        self, log: "logging.Logger", output: "str" = "Literal['stdout','stderr']"
    ) -> "None":
        """Creates a new instance of the capturing context manager.

        Args:
            log: The logger to send the output to
            output: Whether to capture the standard output or the standard error

        """
        self.log = log
        self.out = StringIO()
        self.output = output
        self._original: "Optional[TextIO]" = None

    def __enter__(self) -> "None":
        """Hooks the standard output when entering the context manager."""
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
        """Replaces the standard output, and logs the captured output."""
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


def handle_exception(
    exc_type: "Type[BaseException]",
    exc_value: "BaseException",
    exc_traceback: "Optional[TracebackType]",
) -> "Any":
    """Log unhandled exceptions and their tracebacks in the log.

    Args:
        exc_type: The type of the exception
        exc_value: The exception instance
        exc_traceback: The associated traceback
    """
    # Check the exception is not a keyboard interrupt (Ctrl+C) - if so, so not log it
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    # Log the exception
    log.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


def default_logs() -> "None":
    """Default logging configuration to be used before euporie's config is loaded."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "file_format": {
                    "format": "{asctime} {levelname:<7} [{name}.{funcName}:{lineno}] {message}",
                    "style": "{",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "stdout_format": {
                    "()": StdoutFormatter,
                },
                "log_tab_format": {
                    "()": LogTabFormatter,
                },
            },
            "handlers": {
                "stdout": {
                    "level": "INFO",
                    "()": FormattedTextHandler,
                    "formatter": "stdout_format",
                    "stream": sys.stdout,
                },
                "log_tab": {
                    "level": "INFO",
                    "()": QueueHandler,
                    "formatter": "log_tab_format",
                    "queue": LOG_QUEUE,
                },
            },
            "loggers": {
                "euporie": {
                    "level": "INFO",
                    "handlers": ["log_tab", "stdout"],
                    "propagate": False,
                },
            },
            # Log everything to the internal logger
            "root": {"handlers": ["log_tab"]},
        }
    )  # type: ignore

    # Capture warnings so they show up in the logs
    logging.captureWarnings(True)

    # Log uncaught exceptions
    sys.excepthook = handle_exception
