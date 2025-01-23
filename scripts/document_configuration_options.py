#!/usr/bin/env python
"""Fill in the configuration option in euporie's documentation."""

from __future__ import annotations

from textwrap import dedent, indent

from euporie.core.__main__ import available_apps
from euporie.core.config import Config

for app in available_apps().values():
    app.load()

for name, setting in Config._settings.items():
    print(f".. option:: {name}\n")
    if setting.flags and setting.flags[0].startswith("-"):
        print(
            ":flags:",
            " or ".join([f":option:`{x}`" for x in setting.flags]),
        )
    print()
    if name not in {"version"}:
        print(f":environment variable: :envvar:`EUPORIE_{name.upper()}`")
    if setting.default is not None:
        print(f":default: ``{setting.default!r}``")
    if (type_ := setting.schema.get("type")) is not None:
        print(f":type: :keyword:`{type_}`")
    if setting.choices:
        print(f":options: [``{'``, ``'.join([repr(x) for x in setting.choices])}``]")
    print(f":description: {setting.help}")
    print(indent(dedent(setting.description), "   "))
    print()
