"""Fill in the configuration option in euporie's documentation."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent, indent

from euporie.config import CONFIG_PARAMS

s = ""

for name, param in CONFIG_PARAMS.items():
    s += ".. option:: "
    s += name
    s += "\n\n"
    if "flags_" in param and param.get("flags_", [""])[0].startswith("-"):
        s += ":flags: "
        s += " or ".join([f":option:`{x}`" for x in param["flags_"]])
        s += "\n"
    if name not in {"version"}:
        s += f":environment variable: :envvar:`EUPORIE_{name.upper()}`\n"
    if (default := param.get("schema_", {}).get("default")) is not None:
        s += f":default: ``{default.__repr__()}``\n"
    if (type_ := param.get("schema_", {}).get("type")) is not None:
        s += f":type: :keyword:`{type_}`\n"
    if "choices" in param:
        s += f":options: [``{'``, ``'.join([x.__repr__() for x in param['choices']])}``]\n"
    s += f":description: {param.get('help')}\n"
    s += indent(dedent(param["description_"]), "   ")
    s += "\n"


rst_file = Path(__file__).parent / "../docs/pages/configuration.rst"

with open(rst_file, "r") as f:
    lines = f.readlines()

start = lines.index(".. _configuration-options-start:\n")
end = lines.index(".. _configuration-options-end:\n")

with open(rst_file, "w") as f:

    f.writelines(lines[: start + 1])
    f.write(s)
    f.writelines(lines[end:])
