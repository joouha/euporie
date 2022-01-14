# -*- coding: utf-8 -*-
"""Adds markdown table support to rich.markdown.

Currently every table cell is treated as a paragraph, which makes the table take the
full width of the display.

TODO - fix this.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import flatlatex  # type: ignore
import rich.markdown
from rich.console import Console, ConsoleOptions, JustifyMethod, RenderResult
from rich.markdown import MarkdownContext
from rich.table import Table as RichTable
from rich.text import Text

from euporie.components.markdown.parser import Parser
from euporie.config import config

if TYPE_CHECKING:
    from commonmark.node import Node  # type: ignore
    from rich.markdown import Markdown
    from rich.text import TextType

    from euporie.components.markdown.blocks.tables import Table as TableNode

__all__ = ["Table"]

log = logging.getLogger(__name__)


class Table(rich.markdown.MarkdownElement):
    """A table."""

    style_name = "markdown.table"
    new_line = True
    dumb_console = Console(force_terminal=False, record=True)

    @classmethod
    def create(
        cls, markdown: "rich.markdown.Markdown", table_node: "TableNode"
    ) -> "Table":
        """Instantiates and returns a rich markdown table."""
        return cls(table_node)

    def __init__(self, table_node: "TableNode") -> None:
        """Sets the contents for this markdown table.

        Args:
            table_node: A `commonmark_extensions.tables.Table` instance.

        """
        self.contents = table_node.table
        self.column_properties = table_node.column_properties

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        """Render the table instance.

        Args:
            console: The `rich.console.Console` instance to use to render this table.
            options: The console options to use.

        Yields:
            A rich table renderable.

        """
        table = RichTable(expand=False)

        aligns = [
            self.column_properties.get(i, {}).get("align")
            for i in range(len(self.contents[0][0]))
        ]

        rows: "list[list[Markdown]]" = []

        # Generate header row
        rows.append(
            [
                self.node_to_md(col, justify=aligns[i])
                for i, col in enumerate(self.contents[0][0])
            ]
        )
        # Generate content rows
        if len(self.contents) > 1:
            for row in self.contents[1]:
                rows.append(
                    [
                        self.node_to_md(cell, justify=aligns[i])
                        for i, cell in enumerate(row)
                    ]
                )

        # Get maximum column widths
        max_col_widths = []
        for i in range(len(rows[0])):
            max_col_widths.append(
                max([self.get_markdown_width(row[i]) for row in rows])
            )

        # Add column headers to the table, setting column width
        for i, col in enumerate(rows[0]):
            table.add_column(
                col,
                justify=aligns[i],
                min_width=max_col_widths[i] // 2,
                max_width=max_col_widths[i],
            )
        # Add rows to the table
        for row in rows[1:]:
            table.add_row(*row)

        yield table

    def get_markdown_width(self, md: "Markdown") -> "int":
        """Get the width of markdown text."""
        buffer = self.dumb_console.render(md)
        self.dumb_console._render_buffer(buffer)
        rendered_lines = self.dumb_console.export_text(clear=True)
        return max(map(lambda x: len(x.strip()), rendered_lines.strip().split("\n")))

    @staticmethod
    def node_to_md(
        node: "Node",
        justify: "JustifyMethod" = None,
    ) -> "Markdown":
        """Create a rich markdown object, then add the parsed node to it."""
        node_md = rich.markdown.Markdown(
            markup="",
            code_theme=str(config.syntax_theme),
            justify=justify,
        )
        node_md.parsed = node
        return node_md


class LatexElement(rich.markdown.TextElement):
    """A latex element which renders text as LaTeX."""

    c = flatlatex.converter()

    def on_text(self, context: "MarkdownContext", text: "TextType") -> None:
        text = self.c.convert(text)
        super().on_text(context, text)


class LatexBlock(rich.markdown.Paragraph, LatexElement):
    """Render a block of LaTeX centered as a paragraph."""

    new_line = True

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        self.text.justify = "center"
        yield self.text


class LatexInline(LatexElement):
    """Render a LaTeX in a paragraph."""

    new_line = False

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        yield Text.assemble(self.text, end=" ")


rich.markdown.Parser = Parser
rich.markdown.Markdown.elements["math_block"] = LatexBlock
rich.markdown.Markdown.elements["math"] = LatexInline
rich.markdown.Markdown.elements["table"] = Table
# rich.markdown.Markdown.inlines.add("math")
