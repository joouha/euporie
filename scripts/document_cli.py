"""Fill in the CLI reference in euporie's documentation."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, cast

from euporie.config import config

if TYPE_CHECKING:
    import argparse
    from typing import Callable


def format_action(action: "argparse.Action") -> "str":
    """Format an action as RST."""
    s = ""
    type_ = ""
    if action.type and action.type != bool:
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
    title: "str", parser: "argparse.ArgumentParser", description: "str" = ""
) -> "str":
    """Formats a parser's arguments as RST."""
    s = "\n"
    s += "----\n\n"
    s += ("*" * len(title)) + "\n" + title + "\n" + ("*" * len(title)) + "\n\n"
    s += description or dedent(parser.description or "").strip()
    s += "\n\n"

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


def update_file(content: "str", rst_file: "Path", section: "str") -> "None":
    """Inserts content into a section of a RST file."""
    with open(rst_file, "r") as f:
        lines = f.readlines()

    start = lines.index(f".. _{section}-start:\n")
    end = lines.index(f".. _{section}-end:\n")

    with open(rst_file, "w") as f:

        f.writelines(lines[: start + 1])
        f.write(content)
        f.writelines(lines[end:])


if __name__ == "__main__":
    update_file(
        format_parser(
            "Global Options",
            config.load_parser(),
            """These options affect all subcommands.

.. note::

   They must be specified before a subcommand on the command line
""",
        ),
        Path(__file__).parent / "../docs/pages/cli.rst",
        "cli",
    )
