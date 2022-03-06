"""Contains dpdated ANSI parsing and Formatted Text processing."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import ANSI as PTANSI
from prompt_toolkit.formatted_text import (
    fragment_list_to_text,
    split_lines,
    to_formatted_text,
)
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.layout.processors import DynamicProcessor, Processor, Transformation
from prompt_toolkit.widgets import TextArea

from euporie.config import config

if TYPE_CHECKING:
    from typing import Any, Generator

    from prompt_toolkit.formatted_text import AnyFormattedText, StyleAndTextTuples
    from prompt_toolkit.layout.processors import TransformationInput

__all__ = ["FormatTextProcessor", "FormattedTextArea", "ANSI"]

log = logging.getLogger(__name__)


class FormatTextProcessor(Processor):
    """Applies formatted text to a TextArea."""

    def __init__(self, formatted_text: "StyleAndTextTuples"):
        """Initiate the processor.

        Args:
            formatted_text: The text in a buffer but with formatting applied.

        """
        self.formatted_lines: "list[StyleAndTextTuples]" = []
        self.formatted_text = formatted_text
        super().__init__()

    def apply_transformation(
        self, transformation_input: "TransformationInput"
    ) -> "Transformation":
        """Apply text formatting to a line in a buffer."""
        if not self.formatted_lines:
            self.formatted_lines = list(split_lines(self.formatted_text))
        lineno = transformation_input.lineno
        max_lineno = len(self.formatted_lines) - 1
        if lineno > max_lineno:
            lineno = max_lineno
        line = self.formatted_lines[lineno]
        return Transformation(line)


class FormattedTextArea(TextArea):
    """Applies formatted text to a TextArea."""

    _formatted_text: "AnyFormattedText"

    def _set_formatted_text(self, value: "AnyFormattedText") -> None:
        self._formatted_text = value
        self.text = fragment_list_to_text(self.formatted_text)

    def __init__(
        self, formatted_text: "AnyFormattedText", *args: "Any", **kwargs: "Any"
    ):
        """Initialise a `FormattedTextArea` instance.

        Args:
            formatted_text: A list of `(style, text)` tuples to display.
            *args: Arguments to pass to `prompt_toolkit.widgets.TextArea`.
            **kwargs: Key-word arguments to pass to `prompt_toolkit.widgets.TextArea`.

        """
        self._formatted_text = formatted_text
        input_processors = kwargs.pop("input_processors", [])
        input_processors.append(DynamicProcessor(self.get_processor))
        # The following is not type checked due to a currently open mypy bug
        # https://github.com/python/mypy/issues/6799
        super().__init__(
            *args,
            input_processors=input_processors,
            **kwargs,
        )  # type: ignore
        # Set the formatted text to display
        for margin in self.window.right_margins:
            if isinstance(margin, ScrollbarMargin):
                margin.up_arrow_symbol = "▲"
                margin.down_arrow_symbol = "▼"

        self._set_formatted_text(formatted_text)

    @property
    def formatted_text(self) -> "StyleAndTextTuples":
        """The formatted text."""
        ft = to_formatted_text(self._formatted_text)
        text = fragment_list_to_text(ft)
        if self.text != text:
            self.text = text
        return ft

    @formatted_text.setter
    def formatted_text(self, value: "AnyFormattedText") -> None:
        """Sets the formatted text."""
        self._set_formatted_text(value)

    def get_processor(self) -> "FormatTextProcessor":
        """Generate a processor for the formatted text."""
        return FormatTextProcessor(self.formatted_text)


class ANSI(PTANSI):
    """Converts ANSI text into formatted text, preserving all control sequences."""

    def __init__(self, value: "str") -> None:
        """Initiate the ANSI processor instance.

        This replaces carriage returns to emulate terminal output.

        Args:
            value: The ANSI string to process.

        """
        # Replace windows style newlines
        value = value.replace("\r\n", "\n")
        # Remove anything before a carriage return if there is something after it to
        # emulate a carriage return in the output
        value = re.sub(r"^.*\r(?!\n)", "", value, 0, re.MULTILINE)
        # Clear line by deleting previous characters
        value = re.sub(r".*\x1b\[2K", "", value, 0)
        # Ignore cursor hide / show request
        value = re.sub(r"\x1b\[\?25[hl]", "", value, 0)

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
                formatted_text.pop()
                continue

            # Check for tabs
            elif char == "\t":
                formatted_text.append(("", " " * config.tab_size))
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
