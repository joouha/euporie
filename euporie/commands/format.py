"""Define commands at the application level."""

import logging
from itertools import chain
from typing import TYPE_CHECKING

from euporie.commands.registry import commands
from euporie.key_binding.util import format_keys

if TYPE_CHECKING:
    from typing import Dict, List, Optional, Union

log = logging.getLogger(__name__)


def format_command_attrs(
    groups: "Optional[List[str]]" = None,
    attrs: "Optional[List[str]]" = None,
    pad: "bool" = True,
    escape: "bool" = False,
) -> "Dict[str, List[Dict[str, Union[str, List[str]]]]]":
    """Format command attributes by group.

    Args:
        groups: List of command groups to include. If None, includes all groups
        attrs: List of command attributes to include. If None, includes all attributes
        pad: Whether to pad attribute strings to equal lengths
        escape: Whether to escape back-ticks in strings

    Returns:
        A dictionary mapping group names to lists of command details

    """
    if groups is None:
        groups = [str(cmd.group) for cmd in set(commands.values()) if not cmd.hidden()]

    if attrs is None:
        attrs = ["name", "title", "description", "keys"]

    # Calculate maximum length for each attribute
    max_lens = {}
    if pad:
        for attr in attrs:
            if attr == "keys":
                max_lens[attr] = max(
                    map(
                        len,
                        chain(
                            *[
                                [
                                    x.replace("`", r"\`" if escape else "`")
                                    for x in format_keys(cmd.keys)
                                ]
                                for cmd in commands.values()
                                if not cmd.hidden() and cmd.group in groups and cmd.keys
                            ]
                        ),
                    )
                )
            else:
                max_lens[attr] = max(
                    map(
                        len,
                        (
                            getattr(cmd, attr).replace("`", r"\`" if escape else "`")
                            for cmd in commands.values()
                            if not cmd.hidden() and cmd.group in groups
                        ),
                    )
                )

    # Populate attribute data for each command group
    data: "Dict[str, List[Dict[str, Union[str, List[str]]]]]" = {}
    for group in groups:
        group_title = group.replace("-", " ").capitalize()
        if group_title not in data:
            data[group_title] = []

        for cmd in commands.values():
            if not cmd.hidden() and cmd.group == group:
                cmd_info: "Dict[str, Union[str, List[str]]]" = {}
                for attr in attrs:
                    if attr == "keys":
                        keys = format_keys(cmd.keys)
                        if pad:
                            keys = [
                                key.replace("`", r"\`" if escape else "`").ljust(
                                    max_lens[attr]
                                )
                                for key in keys
                            ]
                        cmd_info[attr] = keys
                    else:
                        value = getattr(cmd, attr)
                        if pad:
                            value = value.replace("`", r"\`" if escape else "`").ljust(
                                max_lens[attr]
                            )
                        cmd_info[attr] = value

                data[group_title].append(cmd_info)

    return data
