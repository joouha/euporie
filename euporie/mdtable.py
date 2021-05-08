# -*- coding: utf-8 -*-
from typing import Any

import rich.markdown
from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table as RichTable

from euporie.config import config
from euporie.libs.commonmark_extensions.tables import ParserWithTables

rich.markdown.Parser = ParserWithTables


class Table(rich.markdown.MarkdownElement):
    """A table."""

    style_name = "markdown.table"
    new_line = False

    @classmethod
    def create(cls, markdown: rich.markdown.Markdown, table: Any) -> "Table":
        return cls(table)

    def __init__(self, contents) -> None:
        self.contents = contents.table
        self.column_properties = contents.column_properties
        self.elements = []

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:

        table = RichTable()

        def node_to_text(node, justify=None):
            """Create a rich markdown object, then add the parsed node to it."""
            node_md = rich.markdown.Markdown(
                "",
                code_theme=config.pygments_style,
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
