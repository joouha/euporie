#!/usr/bin/env python
"""Prints the application's key bindings as a RST table."""

from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
from textwrap import dedent

from apptk.border import (
    AsciiLine,
    AsciiThickLine,
    DiLineStyle,
)
from apptk.commands import get_cmd
from apptk.formatted_text.base import to_formatted_text
from apptk.formatted_text.table import Table
from apptk.formatted_text.utils import indent
from apptk.layout.dimension import Dimension
from apptk.shortcuts.utils import print_formatted_text


def import_all_modules() -> None:
    """Import all euporie modules to register their commands."""
    package_name = "euporie"
    package = importlib.import_module(package_name)
    for _importer, modname, _ispkg in pkgutil.walk_packages(
        path=package.__path__,
        prefix=package_name + ".",
    ):
        try:
            importlib.import_module(modname)
        except Exception:  # noqa: S110
            pass


def get_classes_with_commands() -> list[type]:
    """Find all classes that have a 'commands' attribute."""
    classes = []
    package_name = "euporie"
    package = importlib.import_module(package_name)
    for _importer, modname, _ispkg in pkgutil.walk_packages(
        path=package.__path__,
        prefix=package_name + ".",
    ):
        try:
            module = importlib.import_module(modname)
        except Exception:  # noqa: S112
            continue
        for _name, cls in inspect.getmembers(module, lambda x: hasattr(x, "commands")):
            if cls.__module__ == modname and cls not in classes:
                classes.append(cls)
    return classes


def get_bindings_for_class(cls: type) -> dict[str, list[str]]:
    """Get command bindings for a class, excluding inherited commands."""
    commands = dict.fromkeys(cls.commands).keys()
    for base in cls.__bases__:
        commands = commands - dict.fromkeys(getattr(base, "commands", [])).keys()

    bindings = {}
    for name in commands:
        try:
            cmd = get_cmd(name)
        except KeyError:
            continue
        if not cmd.hidden() and cmd.bindings:
            # Get key strings for this command
            key_strs = list(cmd.key_strs())
            if key_strs:
                bindings[name] = key_strs
    return bindings


# Import all modules to register commands
import_all_modules()

# Get all classes with commands
classes_with_commands = get_classes_with_commands()

sections = {}
bindings_by_group = {}

available_width = Dimension(max=9999)

for cls in classes_with_commands:
    section_title = dedent(cls.__doc__).strip().split("\n")[0].rstrip(".")
    class_bindings = get_bindings_for_class(cls)

    if not class_bindings:
        continue

    group_name = f"{cls.__module__}:{cls.__name__}"
    bindings_by_group[group_name] = class_bindings

    table = Table(border_line=AsciiLine)
    head = table.new_row(style="bold")
    head_line = DiLineStyle(
        top=AsciiLine, right=AsciiLine, bottom=AsciiThickLine, left=AsciiLine
    )
    head.new_cell("Keys", border_line=head_line)
    head.new_cell("Description", border_line=head_line)
    head.new_cell("Command", border_line=head_line)

    for cmd_name in class_bindings:
        cmd = get_cmd(cmd_name)
        row = table.new_row(border_line=AsciiLine)

        formatted_keys = [
            key.replace("\\", "\\\\").replace("`", r"\`") for key in cmd.key_strs()
        ]
        row.new_cell(
            "\n\n".join(f":kbd:`{key}`" for key in formatted_keys),
            border_line=AsciiLine,
        )

        cmd_desc = cmd.description.replace("`", r"\`")
        row.new_cell(cmd_desc, border_line=AsciiLine)

        row.new_cell(f":command:`{cmd_name}`", border_line=AsciiLine)

    sections[section_title] = table

# Find maximum column widths across all tables
if sections:
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

lines = json.dumps(bindings_by_group, indent=2).split("\n")
for line in lines:
    print(f"   {line}")
print()
