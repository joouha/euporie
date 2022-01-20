"""Defines the start of blocks for extensions to commonmark."""

import re
from typing import TYPE_CHECKING

import commonmark  # type: ignore
import commonmark.blocks  # type: ignore

from euporie.markdown.blocks.math import MathBlock
from euporie.markdown.blocks.tables import Table

if TYPE_CHECKING:
    from typing import Any, List, Optional

__all__ = ["MathBlock", "Table", "BlockStarts"]

commonmark.blocks.reMaybeSpecial = re.compile(r"^[#`~*+_=<>0-9-|$]")


class BlockStarts(commonmark.blocks.BlockStarts):
    """Subclasses the BlockStarts class, implementing extension methods."""

    def __init__(self) -> "None":
        """Creates a new instance of the block starting class."""
        super().__init__()
        self.METHODS: "List[str]" = ["math_block", "table"] + self.METHODS

    @staticmethod
    def math_block(parser: "Any", container: "Optional[Any]" = None) -> "int":
        """Defines the start of a block of maths."""
        m = re.search(r"^\${2}\s?$", parser.current_line[parser.next_nonspace :])
        if m:
            math_length = len(m.group())
            parser.close_unmatched_blocks()
            container = parser.add_child("math_block", parser.next_nonspace)
            container.math_length = math_length
            parser.advance_next_nonspace()
            parser.advance_offset(math_length, False)
            return 2
        return 0

    @staticmethod
    def table(parser: "Any", container: "Optional[Any]") -> "int":
        """Defines the start of a table."""
        if (
            not parser.indented
            and commonmark.blocks.peek(parser.current_line, parser.next_nonspace) == "|"
        ):
            parser.advance_next_nonspace()
            parser.advance_offset(1, False)
            parser.close_unmatched_blocks()
            parser.add_child("table", parser.next_nonspace)
            parser.tip.string_content = "|"
            return 2
        return 0
