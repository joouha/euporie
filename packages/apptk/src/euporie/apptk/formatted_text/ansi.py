"""Contain ANSI formatted text parser."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text.ansi import (
    ANSI as PtkANSI,
)
from prompt_toolkit.formatted_text.ansi import (
    _256_colors,
    _bg_colors,
    _fg_colors,
)

if TYPE_CHECKING:
    from collections.abc import Generator


class ANSI(PtkANSI):
    """Convert ANSI text into formatted text, preserving all control sequences.

    Extended to support additional SGR attributes like dim, underline colors,
    various underline styles, fast blink, and overline.
    """

    """Convert ANSI text into formatted text, preserving all control sequences."""

    def __init__(self, value: str, tab_size: int = 8) -> None:
        """Initiate the ANSI processor instance.

        This replaces carriage returns to emulate terminal output.

        Args:
            value: The ANSI string to process.
            tab_size: The number of spaces to use to represent a tab

        """
        # Initialize extended attributes before calling super().__init__
        self._ul_color: str | None = None  # Underline color
        self._blinkfast = False
        self._overline = False
        self._double_underline = False
        self._curvy_underline = False
        self._dotted_underline = False
        self._dashed_underline = False

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

    def _select_graphic_rendition(self, attrs: list[int]) -> None:
        """Process SGR (Select Graphic Rendition) parameters.

        Extended to support additional attributes like dim, underline color,
        various underline styles, fast blink, and overline.

        Args:
            attrs: List of SGR parameter values.

        """
        if not attrs:
            attrs = [0]
        else:
            attrs = list(attrs[::-1])

        while attrs:
            attr = attrs.pop()

            if attr in _fg_colors:
                self._color = _fg_colors[attr]
            elif attr in _bg_colors:
                self._bgcolor = _bg_colors[attr]
            elif attr == 1:
                self._bold = True
            elif attr == 2:
                self._dim = True
            elif attr == 3:
                self._italic = True
            elif attr == 4:
                self._underline = True
            elif attr == 5:
                self._blink = True  # Slow blink
            elif attr == 6:
                self._blinkfast = True  # Fast blink
            elif attr == 7:
                self._reverse = True
            elif attr == 8:
                self._hidden = True
            elif attr == 9:
                self._strike = True
            elif attr == 21:
                # Double underline (alternative code)
                self._double_underline = True
                self._underline = False
            elif attr == 22:
                self._bold = False  # Normal intensity
                self._dim = False
            elif attr == 23:
                self._italic = False
            elif attr == 24:
                self._underline = False
                self._double_underline = False
                self._curvy_underline = False
                self._dotted_underline = False
                self._dashed_underline = False
            elif attr == 25:
                self._blink = False
                self._blinkfast = False
            elif attr == 27:
                self._reverse = False
            elif attr == 28:
                self._hidden = False
            elif attr == 29:
                self._strike = False
            elif attr == 53:
                self._overline = True
            elif attr == 55:
                self._overline = False
            elif attr == 59:
                # Reset underline color
                self._ul_color = None
            elif not attr:
                # Reset all style attributes
                self._color = None
                self._bgcolor = None
                self._bold = False
                self._dim = False
                self._underline = False
                self._double_underline = False
                self._curvy_underline = False
                self._dotted_underline = False
                self._dashed_underline = False
                self._strike = False
                self._italic = False
                self._blink = False
                self._blinkfast = False
                self._reverse = False
                self._hidden = False
                self._overline = False
                self._ul_color = None

            elif attr in (38, 48, 58) and len(attrs) > 1:
                n = attrs.pop()

                # 256 colors.
                if n == 5 and len(attrs) >= 1:
                    if attr == 38:
                        m = attrs.pop()
                        self._color = _256_colors.get(m)
                    elif attr == 48:
                        m = attrs.pop()
                        self._bgcolor = _256_colors.get(m)
                    elif attr == 58:
                        m = attrs.pop()
                        self._ul_color = _256_colors.get(m)

                # True colors.
                if n == 2 and len(attrs) >= 3:
                    try:
                        color_str = (
                            f"#{attrs.pop():02x}{attrs.pop():02x}{attrs.pop():02x}"
                        )
                    except IndexError:
                        pass
                    else:
                        if attr == 38:
                            self._color = color_str
                        elif attr == 48:
                            self._bgcolor = color_str
                        elif attr == 58:
                            self._ul_color = color_str

    def _parse_sgr_sequence(self, sequence: str) -> None:
        """Parse an SGR sequence, handling colon-separated sub-parameters.

        This handles sequences like ESC[4:2m for double underline.

        Args:
            sequence: The full escape sequence string.

        """
        # Extract parameters from sequence (remove ESC[ prefix and m suffix)
        if sequence.startswith("\x1b["):
            param_str = sequence[2:-1]  # Remove \x1b[ and m
        elif sequence.startswith("\x9b"):
            param_str = sequence[1:-1]  # Remove \x9b and m
        else:
            return

        if not param_str:
            self._select_graphic_rendition([0])
            return

        # Split by semicolon first
        parts = param_str.split(";")
        params: list[int] = []

        for part in parts:
            if ":" in part:
                # Handle colon-separated sub-parameters
                sub_parts = part.split(":")
                main_param = int(sub_parts[0]) if sub_parts[0] else 0

                if main_param == 4 and len(sub_parts) > 1:
                    # Underline style: 4:0=off, 4:1=single, 4:2=double, 4:3=curvy, 4:4=dotted, 4:5=dashed
                    sub_param = int(sub_parts[1]) if sub_parts[1] else 0
                    if sub_param == 0:
                        self._underline = False
                        self._double_underline = False
                        self._curvy_underline = False
                        self._dotted_underline = False
                        self._dashed_underline = False
                    elif sub_param == 1:
                        self._underline = True
                    elif sub_param == 2:
                        self._double_underline = True
                    elif sub_param == 3:
                        self._curvy_underline = True
                    elif sub_param == 4:
                        self._dotted_underline = True
                    elif sub_param == 5:
                        self._dashed_underline = True
                elif main_param in (38, 48, 58) and len(sub_parts) > 1:
                    # Extended color with colon syntax: 38:2:r:g:b or 38:5:n
                    color_type = int(sub_parts[1]) if sub_parts[1] else 0
                    color = None
                    if color_type == 5 and len(sub_parts) > 2:
                        color_index = int(sub_parts[2]) if sub_parts[2] else 0
                        color = f"ansicolor{color_index}"
                    elif color_type == 2 and len(sub_parts) > 4:
                        r = int(sub_parts[2]) if sub_parts[2] else 0
                        g = int(sub_parts[3]) if sub_parts[3] else 0
                        b = int(sub_parts[4]) if sub_parts[4] else 0
                        color = f"#{r:02x}{g:02x}{b:02x}"

                    if color:
                        if main_param == 38:
                            self._color = color
                        elif main_param == 48:
                            self._bgcolor = color
                        elif main_param == 58:
                            self._ul_color = color
                else:
                    params.append(main_param)
            else:
                if part:
                    params.append(min(int(part), 9999))

        if params:
            self._select_graphic_rendition(params)

    def _create_style_string(self) -> str:
        """Create a style string from the current attributes.

        Extended to include additional attributes like dim, underline color,
        various underline styles, fast blink, and overline.

        Returns:
            A style string for prompt_toolkit.

        """
        result: list[str] = []

        if self._color:
            result.append(self._color)
        if self._bgcolor:
            result.append(f"bg:{self._bgcolor}")
        if self._bold:
            result.append("bold")
        if self._dim:
            result.append("dim")
        if self._italic:
            result.append("italic")
        if self._underline:
            result.append("underline")
        if self._double_underline:
            result.append("doubleunderline")
        if self._curvy_underline:
            result.append("curvyunderline")
        if self._dotted_underline:
            result.append("dottedunderline")
        if self._dashed_underline:
            result.append("dashedunderline")
        if self._strike:
            result.append("strike")
        if self._blink:
            result.append("blink")
        if self._blinkfast:
            result.append("blinkfast")
        if self._reverse:
            result.append("reverse")
        if self._hidden:
            result.append("hidden")
        if self._overline:
            result.append("overline")
        if self._ul_color:
            result.append(f"ul:{self._ul_color}")

        return " ".join(result)

    def _parse_corot(self) -> Generator[None, str, None]:
        """Coroutine that parses the ANSI escape sequences.

        This is modified version of the ANSI parser from euporie.apptk retains
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
                        # Parse colon-separated sub-parameters from the sequence
                        self._parse_sgr_sequence(sequence)
                        style = self._create_style_string()
                    # Otherwise print a zero-width control sequence
                    else:
                        formatted_text.append(("[ZeroWidthEscape]", sequence))
                    continue

            formatted_text.append((style, sequence))
