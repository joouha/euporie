"""Contain functions to automatically format code cell input."""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

from euporie.core.filters import have_black, have_isort, have_ruff, have_ssort
from euporie.core.log import stdout_to_log

if TYPE_CHECKING:
    from euporie.core.config import Config

log = logging.getLogger(__name__)


def format_ruff(text: str) -> str:
    """Format a code string using :py:mod:`ruff`."""
    from ruff.__main__ import find_ruff_bin

    try:
        ruff_path = find_ruff_bin()
    except FileNotFoundError:
        pass
    else:
        import subprocess

        with contextlib.suppress(subprocess.CalledProcessError):
            text = subprocess.check_output(
                [ruff_path, "format", "-"],
                input=text,
                text=True,
                stderr=subprocess.DEVNULL,
            )
    return text


def format_black(text: str) -> str:
    """Format a code string using :py:mod:`black`."""
    try:
        import black
    except ModuleNotFoundError:
        pass
    else:
        try:
            text = black.format_str(text, mode=black.Mode()).rstrip()
        except (black.parsing.InvalidInput, KeyError):
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
    formatters = set(config.formatters)
    if have_ssort() and "ssort" in formatters:
        text = format_ssort(text)
    if have_isort() and "isort" in formatters:
        text = format_isort(text)
    if have_black() and "black" in formatters:
        text = format_black(text)
    if have_ruff() and "ruff" in formatters:
        text = format_ruff(text)
    return text.strip()
