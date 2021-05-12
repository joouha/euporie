# -*- coding: utf-8 -*-
import logging

from prompt_toolkit.patch_stdout import StdoutProxy
from rich.console import Console
from rich.logging import RichHandler

log_stdout = StdoutProxy(raw=True)

handlers = [
    # logging.StreamHandler(log_stdout),
    RichHandler(
        console=Console(file=log_stdout, force_terminal=True),
        markup=True,
        rich_tracebacks=True,
    )
]

logging.basicConfig(
    level=logging.WARNING,
    handlers=handlers,
    format="%(message)s",
)
