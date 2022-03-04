"""Fill in the usage option in euporie's documentation."""

from __future__ import annotations

from pathlib import Path
from subprocess import check_output  # noqa S404 - security implications considered
from textwrap import indent

s = check_output(["euporie", "--help"]).decode()  # noqa S607,S603

rst_file = Path(__file__).parent / "../docs/pages/usage.rst"

with open(rst_file, "r") as f:
    lines = f.readlines()

start = lines.index(".. _usage-start:\n")
end = lines.index(".. _usage-end:\n")

with open(rst_file, "w") as f:

    f.writelines(lines[: start + 1])
    f.write(".. code-block::\n\n")
    f.write(indent(s, prefix="  "))
    f.write("\n")
    f.writelines(lines[end:])
