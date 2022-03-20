"""Prints the application's key bindings as a RST table."""

from __future__ import annotations

from pathlib import Path

from euporie.commands import get
from euporie.commands.format import format_command_attrs
from euporie.key_binding.bindings.micro import MICRO_BINDINGS

# Register micro bindings
for name, micro_keys in MICRO_BINDINGS.items():
    get(name).add_keys(micro_keys)


data = format_command_attrs(
    attrs=["keys", "description"],
    groups=[
        "app",
        "config",
        "notebook",
        "cell",
        "completion",
        "pager",
        "suggestion",
        "micro-edit-mode",
    ],
    escape=True,
)

s = []

for group, info in data.items():
    if info:
        total_w = len(info[0]["description"]) + len(info[0]["keys"][0]) + 3
        # Section title
        s.append("")
        s.append(group)
        s.append("=" * len(group))
        s.append("")
        # Table header
        w1 = len(info[0]["keys"][0]) + 7
        w2 = len(info[0]["description"])
        s.append("+-" + "-" * w1 + "-+-" + "-" * w2 + "-+")
        s.append("| " + "Keys".ljust(w1) + " | " + "Command".ljust(w2) + " |")
        s.append("+=" + "=" * w1 + "=+=" + "=" * w2 + "=+")
        # Rows
        for rec in info:
            for j, key in enumerate(rec["keys"]):
                key_str = key.strip().replace("\\", "\\\\")
                key_str = f":kbd:`{key_str}`".ljust(len(key) + 7)
                title_str = (
                    rec["description"] if j == 0 else " " * len(rec["description"])
                )
                s.append(f"| {key_str} | {title_str} |")
                s.append(
                    "| " + " " * len(key_str) + " | " + " " * len(title_str) + " |"
                )
            s.pop()
            s.append("+-" + "-" * len(key_str) + "-+-" + "-" * len(title_str) + "-+")

rst_file = Path(__file__).parent / "../docs/pages/keybindings.rst"

with open(rst_file, "r") as f:
    lines = f.readlines()

start = lines.index(".. _keybinding-definitions-start:\n")
end = lines.index(".. _keybinding-definitions-end:\n")

with open(rst_file, "w") as f:

    f.writelines(lines[: start + 1])
    f.writelines((x + "\n" for x in s))
    f.writelines(lines[end:])
