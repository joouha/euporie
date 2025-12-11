#!/usr/bin/env python
"""Parse vt100 input and print keys."""

from __future__ import annotations  # noqa: I001

import sys
from typing import TYPE_CHECKING

from euporie.core.key_binding import key_processor  # noqa: F401

from euporie.apptk.input.vt100 import raw_mode
from euporie.apptk.keys import Keys

from euporie.core.io import Vt100Parser

if TYPE_CHECKING:
    from euporie.apptk.key_binding import KeyPress


def callback(key_press: KeyPress) -> None:
    """Run when a key press event is received."""
    print(key_press)
    if key_press.key == Keys.ControlC:
        print("\x1b[>4;0m")
        print("\x1b[<1u")
        sys.exit(0)


def main() -> None:
    """Run the main event loop."""
    print("\x1b[>4;1m")
    print("\x1b[>1u")
    stream = Vt100Parser(callback)
    with raw_mode(sys.stdin.fileno()):
        while True:
            c = sys.stdin.read(1)
            stream.feed(c)


if __name__ == "__main__":
    main()
