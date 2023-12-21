#!/usr/bin/env python
"""Fill in the command reference in euporie's documentation."""

from __future__ import annotations

import subprocess
import sys
from textwrap import dedent, indent

from euporie.core.commands import commands

if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points


def format_commands() -> None:
    """Format commands as RST."""
    for name, command in commands.items():
        print(f".. option:: {name}\n")
        print(f":title: {command.title}")
        print(":description:")
        print(indent(dedent(command.description), "   "))
        print()


if __name__ == "__main__":
    for script in entry_points(group="console_scripts"):
        if script.module.split(".")[0] == "euporie":
            if sys.argv[-1].startswith("euporie"):
                if sys.argv[-1] == script.name:
                    for app in entry_points(group="euporie.apps"):
                        if app.value.split(".")[:2] == script.value.split(".")[:2]:
                            App = app.load()
                            print(f".. _commands-{script.name}-start:")
                            format_commands()
                            print(f".. _commands-{script.name}-end:")
                            break
                    break
            else:
                subprocess.call([sys.executable, __file__, script.name])  # S603
