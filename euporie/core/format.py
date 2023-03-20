"""Contain functions to automatically format code cell input."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from euporie.core.log import stdout_to_log

if TYPE_CHECKING:
    from euporie.core.config import Config

log = logging.getLogger(__name__)


def format_black(text: str) -> str:
    """Format a code string using :py:mod:`black`."""
    try:
        import black
    except ModuleNotFoundError:
        pass
    else:
        try:
            text = black.format_str(text, mode=black.Mode()).rstrip()
        except black.parsing.InvalidInput:
            log.warning("Error formatting code with black: invalid input")
    return text


def format_isort(text: str) -> str:
    """Format a code string using :py:mod:`isort`."""
    try:
        import isort
    except ModuleNotFoundError:
        pass
    else:
        text = isort.code(text, profile="black")
    return text


def format_ssort(text: str) -> str:
    """Format a code string using :py:mod:`ssort`."""
    try:
        import ssort
    except ModuleNotFoundError:
        pass
    else:
        with stdout_to_log(log, output="stderr"):
            output = ""
            try:
                output = ssort.ssort(text)
            except Exception:  # noqa S110
                # log.debug("Error formatting code with ssort")
                pass
            finally:
                if output:
                    text = output
    return text


def format_code(text: str, config: Config) -> str:
    """Format a code string using :py:mod:``."""
    if config.format_ssort:
        text = format_ssort(text)
    if config.format_isort:
        text = format_isort(text)
    if config.format_black:
        text = format_black(text)
    return text.strip()
