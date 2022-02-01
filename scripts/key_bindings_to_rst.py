"""Prints the application's key bindings as a RST table."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from prompt_toolkit.keys import Keys

from euporie.commands import Command, commands, get
from euporie.key_binding.bindings.micro import MICRO_BINDINGS

# Register micro bindings
for name, micro_keys in MICRO_BINDINGS.items():
    get(name).add_keys(micro_keys)

# groups = set(c.group for c in commands.values())
groups = {
    "app": "Application",
    "config": "Application",
    "notebook": "Notebook",
    "cell": "Cell",
    "suggestion": "Completions",
    "completion": "Suggestions",
    "micro": "Micro Editing Mode",
}

key_dupes: "dict[Union[str, Keys], str]" = {
    Keys.ControlH: "backspace",
    Keys.ControlM: "enter",
    Keys.ControlI: "tab",
}

data: "dict[str, list[Command]]" = {}
for group, group_name in groups.items():
    if group_name not in data:
        data[group_name] = []
    for c in commands.values():
        if c.group == group and c.keys:
            data[group_name].append(c)


def parse_keys(
    keys: """Union[
        tuple[Union[str, Keys], ...],
        list[
            Union[str, Keys, tuple[Union[str, Keys], ...]]
        ],
        list[tuple[Union[str, Keys], ...]]
    ]""",
    done: "bool" = True,
) -> "list[str]":
    """Converts a list of tuples of keys to an RST string."""
    s: "list[str]" = []
    for key in keys:
        if isinstance(key, tuple):
            s.append(", ".join(parse_keys(key, False)))
        elif isinstance(key, Keys):
            s.append(key.value)
        elif isinstance(key, str):
            s.append(key)

        if s:
            s[-1] = (
                s[-1]
                .replace("Escape, ", "Alt+")
                .replace("c-", "Ctrl+")
                .replace("s-", "Shift+")
            )
            if min(map(len, s[-1].split("+"))) > 1:
                s[-1] = s[-1].title()
            if done:
                s[-1] = s[-1].replace("`", r"\`")
                s[-1] = f":kbd:`{s[-1]}`"
    return s


max_name_len = max(map(len, (name for name in commands)))
max_desc_len = max(map(len, (c.description for c in commands.values())))
max_key_len = max(
    map(
        len,
        "\n".join(
            ["\n".join(parse_keys(c.keys)) for c in commands.values() if c.keys]
        ).split("\n"),
    )
)

s = []

for group, cmds in data.items():

    w1 = max_key_len
    w2 = max_desc_len
    w3 = max_name_len
    w = w1 + w2 + 3

    if group and cmds:

        s.append(group.title())
        s.append("=" * len(group))
        s.append("")

        s.append("+-" + "-" * w1 + "-+-" + "-" * w2 + "-+")
        s.append("| " + "Keys".ljust(w1) + " | " + "Command".ljust(w2) + " |")
        s.append("+=" + "=" * w1 + "=+=" + "=" * w2 + "=+")

        for c in cmds:
            # Get unique values but retain order
            keys = list(dict(zip(c.keys, [None] * len(c.keys))).keys())
            for key in keys[:]:
                if len(key) == 1 and key[0] in key_dupes:
                    keys.insert(0, (key_dupes[key[0]],))

            key_strs = parse_keys(keys)
            s.append(
                "| "
                + key_strs[0].ljust(w1)
                + " | "
                + str(c.description or (c.title.capitalize() + "."))
                .replace("`", r"\`")
                .ljust(w2)
                + " |"
            )
            if len(key_strs) > 1:
                for key_str in key_strs[1:]:
                    s.append("| " + " " * w1 + " | " + " " * w2 + " |")
                    s.append("| " + key_str.ljust(w1) + " | " + " " * w2 + " |")
            s.append("+-" + "-" * w1 + "-+-" + "-" * w2 + "-+")

        s.append("")

rst_file = Path(__file__).parent / "../docs/pages/keybindings.rst"

with open(rst_file, "r") as f:
    lines = f.readlines()

start = lines.index(".. _keybinding-definitions-start:\n")
end = lines.index(".. _keybinding-definitions-end:\n")

with open(rst_file, "w") as f:

    f.writelines(lines[: start + 1])
    f.writelines(s)
    f.writelines(lines[end:])
