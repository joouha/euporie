#!/usr/bin/env python
"""Fill in the configuration option in euporie's documentation."""

from __future__ import annotations

from importlib.metadata import entry_points
from textwrap import dedent, indent

from euporie.core.config import Config

_EPS = entry_points()
if isinstance(_EPS, dict):
    APP_ENTRY_POINTS = _EPS.get("euporie.apps")
else:
    APP_ENTRY_POINTS = _EPS.select(group="euporie.apps")

# Import all app classes to load config settings
for entry in APP_ENTRY_POINTS:
    entry.load()

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
        print(f":default: ``{setting.default.__repr__()}``")
    if (type_ := setting.schema.get("type")) is not None:
        print(f":type: :keyword:`{type_}`")
    if setting.choices:
        print(
            f":options: [``{'``, ``'.join([x.__repr__() for x in setting.choices])}``]"
        )
    print(f":description: {setting.help}")
    print(indent(dedent(setting.description), "   "))
    print()
