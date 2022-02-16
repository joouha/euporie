"""A math block extensions for python commonmark."""

from typing import TYPE_CHECKING

import commonmark.blocks  # type: ignore
from commonmark.blocks import Block  # type: ignore
from commonmark.node import Node  # type: ignore

if TYPE_CHECKING:
    from commonmark.blocks import Parser  # type: ignore


class MathBlock(Block):
    """Defines a markdown math block, enclosed in a pair of dollar symbols."""

    accepts_lines = True

    @staticmethod
    def finalize(parser: "Parser", block: "Node") -> "None":
        """Ends the math block."""
        block.literal = block.string_content
        block.string_content = None

    @staticmethod
    def continue_(parser: "Parser", container: "Node") -> "int":
        """Checks for the end of the math block."""
        ln = parser.current_line
        if ln.strip().endswith("$$"):
            parser.finalize(container, parser.line_number)
            return 2
        elif parser.blank:
            parser.advance_next_nonspace()
            return 1
        else:
            return 0

    @staticmethod
    def can_contain(t: "str") -> "bool":
        """Ensures the math block does not contain other nodes."""
        return False


commonmark.blocks.Math = MathBlock
