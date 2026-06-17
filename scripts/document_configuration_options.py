#!/usr/bin/env python
"""Fill in the configuration option in euporie's documentation."""

from __future__ import annotations

from importlib import import_module
from inspect import isabstract
from textwrap import dedent, indent

from euporie.core.app.base import ConfigurableApp
from euporie.core.app.current import available_apps
from euporie.core.config import Config

# Import each app's package so its ConfigurableApp subclass is registered
for app in available_apps().values():
    module_name = app.split(":", 1)[0]
    import_module(module_name)


def _all_subclasses(cls: type) -> set[type]:
    """Recursively collect all subclasses of a class."""
    result = set()
    for sub in cls.__subclasses__():
        result.add(sub)
        result |= _all_subclasses(sub)
    return result


settings = {}
for app_cls in _all_subclasses(ConfigurableApp):
    if isabstract(app_cls):
        continue
    for setting in app_cls.settings:
        settings[setting.name] = setting

config = Config(app="document", settings=list(settings.values()))
for name, setting in config.settings.items():
    print(f".. confval:: {name}\n")
    if setting.flags and setting.flags[0].startswith("-"):
        print(
            "   :flags:",
            " or ".join([f":option:`{x}`" for x in setting.flags]),
        )
    if name not in {"version"}:
        print(f"   :environment variable: :envvar:`EUPORIE_{name.upper()}`")
    if setting.default is not None:
        print(f"   :default: ``{setting.default!r}``")
    if (type_ := setting.schema.get("type")) is not None:
        print(f"   :type: ``{type_}``")
    if setting.choices:
        print(f"   :options: [``{'``, ``'.join([str(x) for x in setting.choices])}``]")
    print(f"   :description: {setting.help}")
    print()
    description = dedent(setting.description).strip()
    if description:
        print(indent(description, "   "))
        print()
