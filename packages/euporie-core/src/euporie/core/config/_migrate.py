"""Migration utilities for converting old JSON config to TOML."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import tomlkit

from euporie.core.config._toml import _to_toml_value

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)


def migrate_json_to_toml(
    json_path: Path,
    config_path: Path,
    state_path: Path,
    config_keys: set[str],
    state_keys: set[str],
) -> bool:
    """Migrate old config.json to config.toml and state.toml.

    The old JSON format stored both configuration and state in a single file::

        {
            "notebook": {"color_scheme": "dark", "recent_files": [...]},
            "color_scheme": "light",
            "recent_files": [...],
        }

    This migrates configuration settings to ``config_path`` and state
    settings to ``state_path``, partitioned using the provided key sets.
    Keys not found in either set are treated as configuration.

    After migration, the JSON file is renamed to config.json.bak.

    Args:
        json_path: Path to the old JSON config file.
        config_path: Path for the new TOML config file.
        state_path: Path for the new TOML state file.
        config_keys: Setting names registered as configuration.
        state_keys: Setting names registered as state.

    Returns:
        True if migration was performed, False otherwise.
    """
    if not json_path.exists():
        return False

    if config_path.exists():
        log.debug("TOML config already exists, skipping migration")
        return False

    try:
        with json_path.open() as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        log.error("Failed to parse old config.json for migration: %s", e)
        return False

    config_doc = tomlkit.document()
    config_doc.add(tomlkit.comment("Migrated from config.json"))
    config_doc.add(tomlkit.nl())

    state_doc = tomlkit.document()
    state_doc.add(tomlkit.comment("Migrated from config.json"))
    state_doc.add(tomlkit.nl())

    has_state = False

    # Top-level scalar values -> global settings (skip None, TOML has no null)
    for key, value in data.items():
        if not isinstance(value, dict) and value is not None:
            if key in state_keys:
                state_doc.add(key, _to_toml_value(value))
                has_state = True
            else:
                config_doc.add(key, _to_toml_value(value))

    # Dict values -> app sections
    for key, value in data.items():
        if isinstance(value, dict):
            config_table = tomlkit.table()
            state_table = tomlkit.table()
            for k, v in value.items():
                if v is not None:
                    if k in state_keys:
                        state_table[k] = _to_toml_value(v)
                    else:
                        config_table[k] = _to_toml_value(v)
            if config_table:
                config_doc.add(tomlkit.nl())
                config_doc.add(key, config_table)
            if state_table:
                state_doc.add(tomlkit.nl())
                state_doc.add(key, state_table)
                has_state = True

    # Write new config TOML file
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w") as f:
        tomlkit.dump(config_doc, f)

    # Write new state TOML file if there are state entries and it doesn't exist
    if has_state and not state_path.exists():
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with state_path.open("w") as f:
            tomlkit.dump(state_doc, f)

    # Rename old file as backup
    backup_path = json_path.with_suffix(".json.bak")
    json_path.rename(backup_path)

    log.info(
        "Migrated configuration from %s to %s and %s (backup: %s)",
        json_path,
        config_path,
        state_path,
        backup_path,
    )
    return True
