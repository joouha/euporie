"""Adds extends :py:class`rich.markdown.Markdown` with tables and LaTeX."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import rich.markdown
from rich.align import Align
from rich.console import Console, ConsoleOptions, JustifyMethod, RenderResult
from rich.markdown import Markdown as RichMarkdown
from rich.markdown import MarkdownContext, MarkdownElement, Paragraph, TextElement
from rich.table import Table as RichTable
from rich.text import Text

from euporie.config import config
from euporie.markdown.parser import Parser

# from euporie.render.latex import LatexRenderer

if TYPE_CHECKING:
    from typing import List

    from commonmark.node import Node  # type: ignore
    from rich.text import TextType

    from euporie.markdown.blocks.tables import Table as TableNode

__all__ = ["Table", "LatexElement", "LatexBlock", "LatexInline", "Markdown"]

log = logging.getLogger(__name__)

rich.markdown.Parser = Parser


class Table(MarkdownElement):
    """A table."""

    style_name = "markdown.table"
    new_line = True
    dumb_console = Console(force_terminal=False, record=True)

    def __init__(self, table_node: "TableNode") -> None:
        """Sets the contents for this markdown table.

        Args:
            table_node: A `commonmark_extensions.tables.Table` instance.

        """
        self.contents = table_node.table
        self.column_properties = table_node.column_properties

    @classmethod
    def create(cls, markdown: "RichMarkdown", table_node: "TableNode") -> "Table":
        """Instantiates and returns a rich markdown table."""
        return cls(table_node)

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
        node_md = Markdown(
            markup="",
            code_theme=str(config.syntax_theme),
            justify=justify,
        )
        node_md.parsed = node
        return node_md

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

        rows: "List[List[Markdown]]" = []

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


class LatexElement(TextElement):
    """A latex element which renders text as LaTeX."""

    def on_text(self, context: "MarkdownContext", text: "TextType") -> None:
        """Converts LaTeX source text to rendered LaTeX text."""
        from euporie.convert.base import convert

        text = str(text)
        text = convert(text, "latex", "ansi")
        text = str(text).ljust(max(map(len, text.split("\n"))))
        super().on_text(context, text)


class LatexBlock(Paragraph, LatexElement):
    """Render a block of LaTeX centered as a paragraph."""

    new_line = True

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        """Centers the LaTeX block."""
        yield Align.center(self.text)


class LatexInline(LatexElement):
    """Render a LaTeX in a paragraph."""

    new_line = False

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        """Ensures the output does not end in a newline."""
        yield Text.assemble(self.text, end=" ")


class Markdown(RichMarkdown):
    """Rich's markdown with additional elements."""

    elements = {
        **RichMarkdown.elements,
        "math_block": LatexBlock,
        "math": LatexInline,
        "table": Table,
    }
