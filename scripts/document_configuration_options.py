"""Fill in the configuration option in euporie's documentation."""

from __future__ import annotations

from importlib.metadata import entry_points

from euporie.core.config import Config

# Import all app classes to load config settings
for entry in entry_points()["euporie.apps"]:
    entry.load()

for name, setting in Config.settings.items():
    if setting.flags and setting.flags[0].startswith("-"):
        pass
    if name not in {"version"}:
        pass
    if setting.default is not None:
        pass
    if (type_ := setting.schema.get("type")) is not None:
        pass
    if setting.choices:
        pass
