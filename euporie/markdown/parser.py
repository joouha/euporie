"""Adds extensions to the python commonmark parser."""

from typing import TYPE_CHECKING

import commonmark  # type: ignore
import commonmark.blocks  # type: ignore

from euporie.markdown.blocks import BlockStarts, MathBlock, Table
from euporie.markdown.inlines import InlineParser

if TYPE_CHECKING:
    from typing import Optional


class Parser(commonmark.Parser):
    """Subclasses the commonmark parser to include tables and math blocks."""

    def __init__(self, options: "Optional[dict]" = None) -> "None":
        """Create a new instance of the parser."""
        if options is None:
            options = {}
        super().__init__(options)
        self.inline_parser = InlineParser(options)
        self.block_starts = BlockStarts()
        if hasattr(self, "blocks"):
            self.blocks["table"] = Table
            self.blocks["math_block"] = MathBlock
