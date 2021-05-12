# -*- coding: utf-8 -*-
from typing import Generator

from prompt_toolkit.formatted_text import ANSI as PTANSI
from prompt_toolkit.formatted_text import to_formatted_text
from prompt_toolkit.layout.processors import Processor, Transformation


class FormatTextProcessor(Processor):
    def apply_transformation(self, transformation_input):
        if not hasattr(self, "formatted_lines"):
            self.formatted_lines = to_formatted_lines(
                transformation_input.buffer_control.formatted_text
            )
        lineno = transformation_input.lineno
        max_lineno = len(self.formatted_lines) - 1
        if lineno > max_lineno:
            lineno = max_lineno
        line = self.formatted_lines[lineno]
        return Transformation(to_formatted_text(line))


def to_formatted_lines(fragments):
    lines = [[]]
    for fragment in fragments:
        style, text, *extra = fragment
        while text:
            start, line, text = text.partition("\n")
            lines[-1].append((style, start, *extra))
            if line == "\n":
                lines.append([])
    return lines


class ANSI(PTANSI):
    """
    Converts ANSI text into formatted text, preserving all control sequences.
    """

    def _parse_corot(self) -> Generator[None, str, None]:
        """
        Coroutine that parses the ANSI escape sequences.

        This is modified version of the ANSI parser from prompt_toolkit retains
        all CSI escape sequences.
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


# ===========================
#  Original Copyright Notice
# ===========================
#
# Copyright (c) 2014, Jonathan Slenders
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.
#
# * Neither the name of the {organization} nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
