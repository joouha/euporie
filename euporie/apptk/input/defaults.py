"""Relating to creation of inputs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.input.defaults import create_input as ptk_create_input

if TYPE_CHECKING:
    from typing import TextIO

    from euporie.apptk.input.base import Input


def create_input(stdin: TextIO | None = None, always_prefer_tty: bool = False) -> Input:
    """Use :py:class:`IgnoredInput` if stdin is not a tty."""
    input_ = ptk_create_input(stdin, always_prefer_tty)

    if (stdin := getattr(input_, "stdin", None)) and not stdin.isatty():
        from euporie.apptk.input.base import IgnoredInput

        input_ = IgnoredInput()

    return input_
