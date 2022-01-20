"""An extension for python commonmark to include markdown tables.

Based on https://github.com/GovReady/CommonMark-py-Extensions
"""

import re
from collections import defaultdict
from typing import TYPE_CHECKING

import commonmark  # type: ignore
import commonmark.blocks  # type: ignore
from commonmark.blocks import Block  # type: ignore
from commonmark.node import Node  # type: ignore

if TYPE_CHECKING:
    from typing import List

    from commonmark.blocks import Parser  # type: ignore

__all__ = ["Table"]


class Table(Block):
    """Define a new markdown Table block.

    Define a new Table class that handles incoming table lines, modeled
    a bit after the Blockquote, which allows continuation lines so long as
    they start with the symbol. Also has accepts_lines to suck in everything
    within it as raw data. Accept : as a continuation symbol for
    Github-flavored Markdown table column alignment.

    """

    accepts_lines = True

    @staticmethod
    def continue_(parser: "Parser", container: "Node") -> "int":
        """Checks for the end of the table block."""
        ln = parser.current_line
        if (
            not parser.indented
            and commonmark.blocks.peek(ln, parser.next_nonspace) == "|"
        ):
            parser.advance_next_nonspace()
            parser.advance_offset(1, False)
            container.string_content += "|"
        elif not parser.indented and commonmark.blocks.peek(
            ln, parser.next_nonspace
        ) not in ("", ">", "`", None):
            pass
        else:
            return 1
        return 0

    @staticmethod
    def finalize(parser: "Parser", block: "Node") -> "None":
        """Split the table content into rows and columns, with each line a new row."""
        # Note that the '|' in the first column is not a part of string_content because
        # it was removed when we slurped in the table.

        table = [[""]]
        escape = False
        # newrowbars = False  # noqa F841
        ignore_pipe = True
        for c in block.string_content.rstrip():
            # \-escaping
            if escape:
                table[-1][-1] += c
                escape = False
            elif c == "\\":
                escape = True

            # New cell is begun by a bar. Right-strip the cell we're
            # ending.
            elif c == "|":
                if ignore_pipe:
                    ignore_pipe = False
                    continue
                table[-1][-1] = table[-1][-1].rstrip()
                table[-1].append("")

            # New row is begun by a newline.
            # Since there's always a pipe at the end of a line,
            # pop last cell if empty.
            elif c == "\n":
                if table[-1][-1].strip() == "":
                    table[-1].pop(-1)
                table.append([""])
                ignore_pipe = True
                continue

            # Ignore space at start of cell. An escaped space
            # can force a space.
            elif c in (" ", "\t") and table[-1][-1] == "":
                pass

            # Content.
            else:
                table[-1][-1] += c

            ignore_pipe = False

        # Remove the last cell if it's empty since it's caused
        # by the final pipe at the end of the last line.
        if table[-1][-1].strip() == "":
            table[-1].pop(-1)

        # Re-flow the table into a <thead> part and a <tbody> part,
        # and if the separator row uses ='s instead of -'s then
        # treat subsequent rows as multiline rows that must be
        # separated by ='s.
        column_properties: "dict" = defaultdict(lambda: {})
        table_parts: "List[List[Node]]" = [[]]  # [thead, tbody] or just [tbody]
        multiline = False
        newrow = False
        for row in table:
            if len(list(filter(lambda cell: not re.match(r"[-=:]+$", cell), row))) == 0:
                # This row has cells of just dahses.
                if len(table_parts) == 1:
                    if len(row) != len(table_parts[0][0]):
                        block.t = "paragraph"
                        return
                    # The first time, we shift to the tbody.
                    table_parts.append([])

                    # We also pick out column properties from the
                    # placement of a colon.
                    for i, cell in enumerate(row):
                        if cell.startswith(":") and cell.endswith(":"):
                            column_properties[i]["align"] = "center"
                        elif cell.startswith(":"):
                            column_properties[i]["align"] = "left"
                        elif cell.endswith(":"):
                            column_properties[i]["align"] = "right"

                    # If ='s were used, then the table is parsed in
                    # multiline mode.
                    if "=" in "".join(row):
                        multiline = True

                elif multiline:
                    # Subsequent times we just note that we're starting a new row
                    # in multiline mode.
                    newrow = True

            elif not multiline or newrow or len(table_parts[-1]) == 0:
                # Append a new row.
                table_parts[-1].append(row)
                newrow = False

                # Fill in empty rows if fewer than the header.
                if len(table_parts) > 1 and len(table_parts[0][0]) > len(
                    table_parts[-1][-1]
                ):
                    table_parts[-1][-1].extend(
                        [
                            ""
                            for _ in range(
                                len(table_parts[0][0]) - len(table_parts[-1][-1])
                            )
                        ]
                    )

                # Remove excess cells if more than number of columns
                if len(table_parts) > 1 and len(table_parts[0][0]) < len(
                    table_parts[-1][-1]
                ):
                    table_parts[-1][-1] = table_parts[-1][-1][: len(table_parts[0][0])]

            else:
                # Multline mode. Merge this row with the previous one.
                for i in range(len(row)):
                    if i < len(table_parts[-1][-1]):
                        table_parts[-1][-1][i] += "\n" + row[i]
                    else:
                        table_parts[-1][-1].append(row[i])

        # Remove the last table part (probably tbody) if there is no content.
        if table_parts[-1] == []:
            table_parts.pop(-1)

        # Parse the Markdown in each cell using a new parser
        # instance for each cell.
        if not multiline:
            # Just parse the inlines in each cell using the parser's
            # inline_parser function. Wrap each cell string content
            # in a Node first.
            def inner_parser(cell: "str") -> "Node":
                node = Node("document", 0)
                para = Node("paragraph", 0)
                para.string_content = cell
                node.append_child(para)
                parser.inline_parser.parse(para)
                return node

        else:
            # Parse each cell using the full Markdown parser,
            # by instantiating a new instance of the same
            # parser class first, using the same options.
            inner_parser = type(parser)(options=parser.options).parse

        for part in table_parts:
            for row in part:
                for i, cell in enumerate(row):
                    row[i] = inner_parser(cell)

        # Store the parsed table on the node.
        block.column_properties = column_properties
        block.table = table_parts


commonmark.blocks.Table = Table


"""
Original copyright notice:

Copyright (c) 2017 GovReady PBC

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.

    * Redistributions in binary form must reproduce the above
      copyright notice, this list of conditions and the following
      disclaimer in the documentation and/or other materials provided
      with the distribution.

    * Neither the names of Bibek Kafle, Roland Shoemaker nor the names of other
      contributors may be used to endorse or promote products derived
      from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
