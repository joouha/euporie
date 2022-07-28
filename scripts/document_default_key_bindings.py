"""Prints the application's key bindings as a RST table."""

from __future__ import annotations

import importlib
from textwrap import dedent

from prompt_toolkit.shortcuts.utils import print_formatted_text

from euporie.core.border import Ascii, AsciiThick, BorderLineStyle
from euporie.core.commands import get_cmd
from euporie.core.formatted_text.table import Table
from euporie.core.key_binding.registry import BINDINGS
from euporie.core.key_binding.utils import format_keys, parse_keys

groups = [
    "euporie.core.app.BaseApp",
    "euporie.notebook.app.NotebookApp",
    "euporie.notebook.tabs.notebook.Notebook",
    "euporie.console.app.ConsoleApp",
    "euporie.console.tabs.console.Console",
    "euporie.preview.app.PreviewApp",
    "euporie.core.widgets.pager.Pager",
    "euporie.core.widgets.inputs.KernelInput",
    "euporie.core.key_binding.bindings.micro.EditMode",
]

sections = {}

for group in groups:
    mod_name, cls_name = group.rsplit(".", maxsplit=1)
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, cls_name)
    section_title = dedent(cls.__doc__).strip().split("\n")[0].rstrip(".")

    table = Table(border=Ascii)
    head = table.new_row(style="bold", border=BorderLineStyle(bottom=AsciiThick))
    head.new_cell("Command")
    head.new_cell("Keys")
    for cmd_name, raw_keys in BINDINGS.get(group, {}).items():
        cmd = get_cmd(cmd_name)
        row = table.new_row()

        formatted_keys = [
            key.replace("`", r"\`").replace("\\", "\\\\")
            for key in format_keys(parse_keys(raw_keys))
        ]
        row.new_cell("\n\n".join(f":kbd:`{key}`" for key in formatted_keys))

        cmd_title = cmd.title.replace("`", r"\`")
        cmd_desc = cmd.description.replace("`", r"\`")
        # row.new_cell(f":abbr:`{cmd_title}\n({cmd_desc})`")
        row.new_cell(cmd_desc)

    sections[section_title] = table

# Find maximum column widths across all tables
table_col_widths = [table.calculate_col_widths(99999) for table in sections.values()]
col_widths = [
    max(w[i] for w in table_col_widths) for i in range(len(table_col_widths[0]))
]

for title, table in sections.items():
    # Set column widths
    for i, val in enumerate(col_widths):
        table.rows[0].cells[i].width = val

    print_formatted_text(
        f"""
{title}
{"=" * len(title)}
"""
    )
    print_formatted_text(table)
