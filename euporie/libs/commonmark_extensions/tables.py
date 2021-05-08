# -*- coding: utf-8 -*-
# Mokey-patch the reMaybeSpecial regex to add our table symbol |.
# This regex is apparently just an optimization so this should not
# affect CommonMark parser instances that do not recognize tables.
import re
from collections import defaultdict

import commonmark
import commonmark.blocks
import commonmark.node

commonmark.blocks.reMaybeSpecial = re.compile(r"^[#`~*+_=<>0-9-|]")


# Define a new BlockStarts class that implements a table method
# to detect and parse table starts, modeled after the blockquote.
class BlockStarts(commonmark.blocks.BlockStarts):
    def __init__(self):
        self.METHODS = ["table"] + self.METHODS

    @staticmethod
    def table(parser, container):
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


# Define a new Table class that handles incoming table lines, modeled
# a bit after the Blockquote, which allows continuation lines so long as
# they start with the symbol. Also has accepts_lines to suck in everything
# within it as raw data. Accept : as a continuation symbol for
# Github-flavored Markdown table column alignment.
class Table(commonmark.blocks.Block):
    accepts_lines = True

    @staticmethod
    def continue_(parser=None, container=None):
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
    def finalize(parser=None, block=None):
        # Split the table content into rows and columns,
        # with each line a new row.
        #
        # Note that the | in the first column is not a
        # part of string_content because it was removed
        # when we slurped in the table.
        table = [[""]]
        escape = False
        newrowbars = False  # noqa F841
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
        column_properties = defaultdict(lambda: {})
        table_parts = [[]]  # [thead, tbody] or just [tbody]
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
            def inner_parser(cell):
                node = commonmark.node.Node("document", 0)
                para = commonmark.node.Node("paragraph", 0)
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


# Create a new parser sub-class that adds the new block-start
# for tables.
class ParserWithTables(commonmark.Parser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.block_starts = BlockStarts()
        if hasattr(self, "blocks"):
            self.blocks["table"] = commonmark.blocks.Table


# Define a new renderer that extends the HtmlRenderer and
# adds table rendering.
class RendererWithTables(commonmark.HtmlRenderer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def make_table_node(self, node):
        return "<table>"

    def table(self, node, entering):
        if entering:
            self.lit(self.make_table_node(node) + "\n")
            for i, part in enumerate(node.table):
                if i == 0:
                    part_tag = "thead"
                else:
                    part_tag = "tbody"
                self.lit("<" + part_tag + ">\n")
                for row in part:
                    self.lit("<tr>\n")
                    for colidx, cell in enumerate(row):
                        if part_tag == "thead":
                            col_tag = "th"
                            if self.options.get("table_th_scope"):
                                col_attrs = '  scope="col"'
                            else:
                                col_attrs = ""
                        else:
                            col_tag = "td"
                            col_attrs = ""

                        if (
                            colidx in node.column_properties
                            and "align" in node.column_properties[colidx]
                        ):
                            col_attrs += (
                                ' align="'
                                + node.column_properties[colidx]["align"]
                                + '"'
                            )

                        self.lit("<" + col_tag + col_attrs + ">")

                        import copy

                        inner_renderer = copy.copy(self)
                        cell = inner_renderer.render(cell)

                        # If the cell is just one <p>, unwrap it.
                        m = re.match("<p>(.*)</p>$", cell)
                        if m:
                            cell = m.group(1)

                        self.lit(cell)
                        self.lit("</" + col_tag + ">\n")
                    self.lit("</tr>\n")
                self.lit("</" + part_tag + ">\n")
            self.lit("</table>\n")


# Define a new helper method that would be an in-place replacement
# for commonmark.commonmark.
def commonmark_to_html(markup):
    parser = ParserWithTables()
    ast = parser.parse(markup)
    return RendererWithTables().render(ast)


if __name__ == "__main__":
    # Run the parser on STDIN and write to STDOUT.
    import sys

    parser = ParserWithTables()
    ast = parser.parse(sys.stdin.read())
    print(RendererWithTables().render(ast))
