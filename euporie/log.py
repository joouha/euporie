# -*- coding: utf-8 -*-
"""Initiate logging for euporie."""
from __future__ import annotations

import logging
import logging.config
from tempfile import TemporaryFile
from typing import IO, cast

from prompt_toolkit.patch_stdout import StdoutProxy
from rich.console import Console

log_stdout = cast("IO[str]", StdoutProxy(raw=True))
log_memory = TemporaryFile(mode="w+")

LOGGING_CONFIG = {
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
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "file": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "plain_format",
        },
        "memory": {
            "level": "INFO",
            "class": "rich.logging.RichHandler",
            "console": Console(file=log_memory, force_terminal=True, width=120),
            "markup": True,
            "rich_tracebacks": True,
            "formatter": "rich_format",
        },
        "screen": {
            "level": "ERROR",
            "class": "rich.logging.RichHandler",
            "console": Console(file=log_stdout, force_terminal=True),
            "markup": True,
            "rich_tracebacks": True,
            "formatter": "rich_format",
        },
    },
    "loggers": {
        "euporie": {
            "handlers": ["memory"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
    "root": {"handlers": ["memory"]},
}

logging.config.dictConfig(LOGGING_CONFIG)
