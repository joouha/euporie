"""Contain ANSI formatted text parser."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import ANSI as PTANSI

if TYPE_CHECKING:
    from collections.abc import Generator

log = logging.getLogger(__name__)


class ANSI(PTANSI):
    """Convert ANSI text into formatted text, preserving all control sequences."""

    def __init__(self, value: str, tab_size: int = 8) -> None:
        """Initiate the ANSI processor instance.

        This replaces carriage returns to emulate terminal output.

        Args:
            value: The ANSI string to process.
            tab_size: The number of spaces to use to represent a tab

        """
        # Replace tabs with spaces
        value = value.expandtabs(tabsize=tab_size)
        # Replace windows style newlines
        value = value.replace("\r\n", "\n")
        # Remove anything before a carriage return if there is something after it to
        # emulate a carriage return in the output
        value = re.sub(r"^.*\r(?!\n)", "", value, count=0, flags=re.MULTILINE)
        # Clear line by deleting previous characters
        value = re.sub(r".*\x1b\[2K", "", value, count=0)
        # Remove hide & show cursor commands
        value = re.sub(r"\x1b\[\?25[hl]", "", value, count=0)
        # Collapse cursor up movements
        while (match := re.search(r"\x1b\[(?P<count>\d+)A", value)) is not None:
            lines = int(match["count"])
            before = value[: match.start()]
            after = value[match.end() :]
            before = "".join(before.splitlines(keepends=True)[:-lines])
            value = before + after

        super().__init__(value)

    def _parse_corot(self) -> Generator[None, str, None]:
        """Coroutine that parses the ANSI escape sequences.

        This is modified version of the ANSI parser from prompt_toolkit retains
        all CSI escape sequences.

        Yields:
            Accepts characters from a string.

        """
        style = ""
        formatted_text = self._formatted_text

        while True:
            char = yield
            sequence = char

            # Everything between \001 and \002 should become a ZeroWidthEscape.
            if char == "\001":
                sequence = ""
                while char != "\002":
                    char = yield
                    if char == "\002":
                        formatted_text.append(("[ZeroWidthEscape]", sequence))
                        break
                    else:
                        sequence += char
                continue

            # Check for backspace
            elif char == "\x08":
                # TODO - remove last character from last non-ZeroWidthEscape fragment
                if formatted_text:
                    formatted_text.pop()
                continue

            elif char in ("\x1b", "\x9b"):
                # Got a CSI sequence, try to compile a control sequence
                char = yield

                # Check for sixels
                if char == "P":
                    # Got as DEC code
                    sequence += char
                    # We expect "p1;p2;p3;q" + sixel data + "\x1b\"
                    char = yield
                    while char != "\x1b":
                        sequence += char
                        char = yield
                    sequence += char
                    char = yield
                    if ord(char) == 0x5C:
                        sequence += char
                        formatted_text.append(("[ZeroWidthEscape]", sequence))
                        # char = yield
                        continue

                # Check for hyperlinks
                elif char == "]":
                    sequence += char
                    char = yield
                    if char == "8":
                        sequence += char
                        char = yield
                        if char == ";":
                            sequence += char
                            char = yield
                            while True:
                                sequence += char
                                if sequence[-2:] == "\x1b\\":
                                    break
                                char = yield
                            formatted_text.append(("[ZeroWidthEscape]", sequence))
                            continue

                elif (char == "[" and sequence == "\x1b") or sequence == "\x9b":
                    if sequence == "\x1b":
                        sequence += char
                        char = yield

                    # Next are any number (including none) of "parameter bytes"
                    params = []
                    current = ""
                    while 0x30 <= ord(char) <= 0x3F:
                        # Parse list of integer parameters
                        sequence += char
                        if char.isdigit():
                            current += char
                        else:
                            params.append(min(int(current or 0), 9999))
                            if char == ";":
                                current = ""
                        char = yield
                    if current:
                        params.append(min(int(current or 0), 9999))
                    # then any number of "intermediate bytes"
                    while 0x20 <= ord(char) <= 0x2F:
                        sequence += char
                        char = yield
                    # finally by a single "final byte"
                    if 0x40 <= ord(char) <= 0x7E:
                        sequence += char
                    # Check if that escape sequence was a style:
                    if char == "m":
                        self._select_graphic_rendition(params)
                        style = self._create_style_string()
                    # Otherwise print a zero-width control sequence
                    else:
                        formatted_text.append(("[ZeroWidthEscape]", sequence))
                    continue

            formatted_text.append((style, sequence))
            # log.debug(repr(sequence))
