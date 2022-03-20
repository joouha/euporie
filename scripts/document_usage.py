"""Fill in the usage option in euporie's documentation."""

from __future__ import annotations

from pathlib import Path
from subprocess import check_output  # noqa S404 - security implications considered

from euporie.config import config

parser = config.load_parser()

s = ""

for action in parser._actions:

    type_ = ""
    if action.type and action.type != bool:
        type_ = f"<{action.type.__name__}>"
    if action.choices:
        type_ = f"{{{','.join(map(str, action.choices))}}}"

    flags = [f"{flag} {type_}".strip() for flag in action.option_strings]

    s += f"""
.. option:: {", ".join(flags)}

   {action.help}
"""

rst_file = Path(__file__).parent / "../docs/pages/usage.rst"

with open(rst_file, "r") as f:
    lines = f.readlines()

start = lines.index(".. _usage-start:\n")
end = lines.index(".. _usage-end:\n")

with open(rst_file, "w") as f:

    f.writelines(lines[: start + 1])
    f.write(s)
    f.writelines(lines[end:])
