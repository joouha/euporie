#!/usr/bin/env python
"""Fill in the command reference in euporie's documentation."""

from __future__ import annotations

import subprocess
import sys
from inspect import Parameter, signature
from textwrap import dedent, indent

from apptk.commands import COMMANDS, Command

if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points


def command_args(command: Command) -> list[Parameter]:
    """Return the user-facing parameters a command's handler accepts."""
    params = list(signature(command.handler).parameters.values())
    # Drop a leading `event` parameter (handled internally, not user-supplied)
    if params and params[0].name == "event":
        params = params[1:]
    # Ignore keyword-only/var-keyword params (arguments are passed positionally)
    return [p for p in params if p.kind is not Parameter.VAR_KEYWORD]


def format_commands() -> None:
    """Format commands as RST."""
    # Group command names by their command object to deduplicate aliases
    command_names: dict[int, tuple[Command, list[str]]] = {}
    for name, command in COMMANDS.items():
        if not name:
            continue
        key = id(command)
        if key not in command_names:
            command_names[key] = (command, [])
        command_names[key][1].append(name)

    for command, names in command_names.values():
        # Use the command's canonical name as the primary entry
        primary = command.name if command.name in names else names[0]
        aliases = [n for n in names if n != primary]
        print(f".. option:: {primary}\n")
        print(f"   :title: {command.title}")
        print("   :description:")
        print(indent(dedent(command.description), "      "))
        if aliases:
            print()
            print(f"   :aliases: ``{'``, ``'.join(sorted(aliases))}``")
        args = command_args(command)
        if args:
            print()
            print(f"   :arguments: ``{'``, ``'.join(p.name for p in args)}``")
        print()


if __name__ == "__main__":
    print("############")
    print("All Commands")
    print("############")
    print()
    for script in entry_points(group="console_scripts"):
        if script.name.startswith("euporie"):
            if sys.argv[-1].startswith("euporie"):
                if sys.argv[-1] == script.name:
                    # Load the app module to register commands
                    script.load()
                    print(f".. _commands-{script.name}-start:")
                    format_commands()
                    print(f".. _commands-{script.name}-end:")
                    break
            else:
                subprocess.call([sys.executable, __file__, script.name])  # S603
