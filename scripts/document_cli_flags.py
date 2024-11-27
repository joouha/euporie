#!/usr/bin/env python
"""Fill in the CLI reference in euporie's documentation."""

from __future__ import annotations

import subprocess
import sys
from textwrap import dedent, indent
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    import argparse
    from typing import Callable

if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points


def format_action(action: argparse.Action) -> str:
    """Format an action as RST."""
    s = ""
    type_ = ""
    if action.type and action.type is not bool:
        action.type = cast("Callable", action.type)
        type_ = f"<{action.type.__name__}>"  # typing: ignore
    if action.choices:
        type_ = f"{{{','.join(map(str, action.choices))}}}"

    flags = [f"{flag} {type_}".strip() for flag in action.option_strings] or [type_]
    nargs = " ..." if action.nargs == "*" else ""

    s += f""".. option:: {", ".join(flags)}{nargs}

   {action.help}

"""
    return s


def format_parser(
    title: str, parser: argparse.ArgumentParser, description: str = ""
) -> str:
    """Format a parser's arguments as RST."""
    s = ""

    # s = "\n"
    # s += ("*" * len(title)) + "\n" + title + "\n" + ("*" * len(title)) + "\n\n"
    # s += description or dedent(parser.description or "").strip()
    # s += "\n\n"

    s += "\nUsage\n=====\n\n"
    s += ".. code-block:: console\n\n"
    usage = parser.format_usage()
    usage = usage[usage.startswith("usage: ") and len("usage: ") :]
    s += indent(f"$ {usage}", "   ")
    s += "\n"

    positionals = [action for action in parser._actions if not action.option_strings]
    if positionals:
        s += "Positional Arguments\n====================\n\n"
        for action in positionals:
            s += format_action(action)

    optionals = [action for action in parser._actions if action.option_strings]
    if optionals:
        s += "Optional Arguments\n==================\n\n"
        for action in optionals:
            s += format_action(action)

    subcommands = [action for action in parser._actions if action.dest == "subcommand"]
    for action in subcommands:
        if isinstance(action.choices, dict):
            for name, subcommand in action.choices.items():
                s += format_parser(f":option:`{name}` subcommand", subcommand)

    return s


if __name__ == "__main__":
    for script in entry_points(group="console_scripts"):
        if script.module.split(".")[0] == "euporie":
            if sys.argv[-1].startswith("euporie"):
                if sys.argv[-1] == script.name:
                    for app in entry_points(group="euporie.apps"):
                        if app.value.split(".")[:2] == script.value.split(".")[:2]:
                            App = app.load()
                            parser = App.config._load_parser()
                            parser.prog = script.name
                            print(f".. _cli-{script.name}-start:")
                            print(
                                format_parser(
                                    f":command:`{script.name}`",
                                    parser,
                                    description=dedent("    " + App.__doc__),
                                )
                            )
                            print(f".. _cli-{script.name}-end:")
                            break
                    break
            else:
                subprocess.call([sys.executable, __file__, script.name])  # S603
