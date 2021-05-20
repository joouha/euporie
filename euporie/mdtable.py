# -*- coding: utf-8 -*-
"""Adds markdown table support to rich.markdown.

Currently every table cell is treated as a paragraph, which makes the table take the
full width of the display.

TODO - fix this.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import rich.markdown
from rich.console import Console, ConsoleOptions, JustifyMethod, RenderResult
from rich.table import Table as RichTable

from euporie.config import config
from euporie.libs.commonmark_extensions.tables import ParserWithTables  # type: ignore
from euporie.libs.commonmark_extensions.tables import Table as CETable  # type: ignore

if TYPE_CHECKING:
    from commonmark.node import Node  # type: ignore


rich.markdown.Parser = ParserWithTables


class Table(rich.markdown.MarkdownElement):
    """A table."""

    style_name = "markdown.table"
    new_line = False

    @classmethod
    def create(cls, markdown: "rich.markdown.Markdown", table: "CETable") -> "Table":
        """Instantiates and returns a rich markdown table."""
        return cls(table)

    def __init__(self, contents: "CETable") -> None:
        """Sets the contents for this markdown table.

        Args:
            contents: A `commonmark_extensions.tables.Table` instance.

        """
        self.contents = contents.table
        self.column_properties = contents.column_properties

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> RenderResult:
        """Render the table instance.

        Args:
            console: The `rich.console.Console` instance to use to render this table.
            options: The console options to use.

        Yields:
            A rich table renderable.

        """
        table = RichTable()

        def node_to_text(
            node: "Node",
            justify: "JustifyMethod" = None,
        ) -> "rich.markdown.Markdown":
            """Create a rich markdown object, then add the parsed node to it."""
            node_md = rich.markdown.Markdown(
                "",
                code_theme=str(config.pygments_style),
                justify=justify,
            )
            node_md.parsed = node
            return node_md

        for i, col in enumerate(self.contents[0][0]):
            justify = self.column_properties.get(i, {}).get("align")
            table.add_column(node_to_text(col, justify=justify), justify=justify)

        for row in self.contents[1]:
            table.add_row(*[node_to_text(cell, justify=justify) for cell in row])

        yield table


rich.markdown.Markdown.elements["table"] = Table
