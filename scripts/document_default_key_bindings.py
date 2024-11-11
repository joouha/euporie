#!/usr/bin/env python
"""Prints the application's key bindings as a RST table."""

from __future__ import annotations

import importlib
import json
from textwrap import dedent

from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.shortcuts.utils import print_formatted_text

from euporie.core.border import (
    AsciiLine,
    AsciiThickLine,
    DiLineStyle,
)
from euporie.core.commands import get_cmd
from euporie.core.ft.table import Table
from euporie.core.ft.utils import indent
from euporie.core.key_binding.registry import BINDINGS
from euporie.core.key_binding.utils import format_keys, parse_keys

groups = [
    "euporie.core.app.app:BaseApp",
    "euporie.core.tabs.base.Tab",
    "euporie.notebook.app.NotebookApp",
    "euporie.notebook.tabs.notebook.Notebook",
    "euporie.console.app.ConsoleApp",
    "euporie.console.tabs.console.Console",
    "euporie.preview.app.PreviewApp",
    "euporie.core.key_binding.bindings.micro.EditMode",
    "euporie.core.widgets.pager.Pager",
    "euporie.core.widgets.inputs.KernelInput",
    "euporie.core.widgets.display.Display",
    "euporie.web.widgets.webview.WebViewControl",
]

sections = {}

available_width = Dimension(max=9999)

# Pre-import everything
for group in groups:
    mod_name, cls_name = group.rsplit(".", maxsplit=1)
    importlib.import_module(mod_name)

for group in groups:
    mod_name, cls_name = group.rsplit(".", maxsplit=1)
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, cls_name)
    section_title = dedent(cls.__doc__).strip().split("\n")[0].rstrip(".")

    table = Table(border_line=AsciiLine)
    head = table.new_row(style="bold")
    head_line = DiLineStyle(
        top=AsciiLine, right=AsciiLine, bottom=AsciiThickLine, left=AsciiLine
    )
    head.new_cell("Keys", border_line=head_line)
    head.new_cell("Description", border_line=head_line)
    head.new_cell("Command", border_line=head_line)
    for cmd_name, raw_keys in BINDINGS.get(group, {}).items():
        cmd = get_cmd(cmd_name)
        row = table.new_row(border_line=AsciiLine)

        formatted_keys = [
            key.replace("\\", "\\\\").replace("`", r"\`")
            for key in format_keys(parse_keys(raw_keys))
        ]
        row.new_cell(
            "\n\n".join(f":kbd:`{key}`" for key in formatted_keys),
            border_line=AsciiLine,
        )

        cmd_title = cmd.title.replace("`", r"\`")
        cmd_desc = cmd.description.replace("`", r"\`")
        # row.new_cell(f":abbr:`{cmd_title}\n({cmd_desc})`")
        row.new_cell(cmd_desc, border_line=AsciiLine)

        row.new_cell(f":command:`{cmd_name}`", border_line=AsciiLine)

    sections[section_title] = table

# Find maximum column widths across all tables
table_col_widths = [
    table.calculate_col_widths(available_width) for table in sections.values()
]
col_widths = [
    max(w[i] for w in table_col_widths) for i in range(len(table_col_widths[0]))
]

for title, table in sections.items():
    if len(table.rows) == 1:
        continue

    # Set column widths
    for i, val in enumerate(col_widths):
        table.rows[0].cells[i].width = val

    print_formatted_text(
        f"""
{title}
{"=" * len(title)}

.. table::
   :width: 133%
   :widths: 25,75,33

"""
    )
    ft = table.render(width=available_width)
    print_formatted_text(to_formatted_text(indent(ft, "   ")))

print()
print("----")
print()

print(
    """
Default Key-binding configuration
=================================

The following lists all of the default key-bindings used in euporie in the format required for custom key-bindings in the configuration file.

.. code-block:: javascript
"""
)

lines = json.dumps(
    {group: BINDINGS.get(group, {}) for group in groups}, indent=2
).split("\n")
for line in lines:
    print(f"   {line}")
print()
