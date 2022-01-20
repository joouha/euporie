"""Defines additional inline nodes for the python commonmark parser."""

import re
from typing import TYPE_CHECKING

import commonmark.inlines  # type: ignore
from commonmark.inlines import text  # type: ignore
from commonmark.node import Node  # type: ignore

if TYPE_CHECKING:
    from typing import Any

reDollars = re.compile(r"\$+")
reDollarsHere = re.compile(r"^\$+")

# Add dollar sign to the non-special string matching regex
reMain = re.compile(r'^[^\n`\[\]\\!<&*_\'"$]+', re.MULTILINE)
commonmark.inlines.reMain = reMain


class InlineParser(commonmark.inlines.InlineParser):
    """An extension of the commonmark inline parser.

    Includes support for:
    - Inline maths deliminated with dollar signs (``$``)

    """

    pos: "int"

    def parseMath(self, block: "Any") -> "bool":
        """Attempt to parse inline math code between pairs of '$'."""
        dollars = self.match(reDollarsHere)
        if dollars is None:
            return False
        after_open_dollars = self.pos
        matched = self.match(reDollars)
        while matched is not None:
            if matched == dollars:
                node = Node("math", None)
                contents = self.subject[
                    after_open_dollars : self.pos - len(dollars)
                ].replace("\n", " ")
                if contents.lstrip(" ") and contents[0] == contents[-1] == " ":
                    node.literal = contents[1:-1]
                else:
                    node.literal = contents
                block.append_child(node)
                return True
            matched = self.match(reDollars)
        # If we got here, we didn't match a closing dollar sequence.
        self.pos = after_open_dollars
        block.append_child(text(dollars))
        return True

    def parseInline(self, block: "Any") -> "bool":
        """Override the inline parsing function to include parsing inline math."""
        c = self.peek()
        if c == "$":
            self.parseMath(block)
            return True
        else:
            return super().parseInline(block)
