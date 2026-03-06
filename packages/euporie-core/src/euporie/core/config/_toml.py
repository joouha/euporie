"""TOML file handling utilities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import tomlkit
from tomlkit.items import Table

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)


def load_toml(path: Path) -> tomlkit.TOMLDocument:
    """Load a TOML file, returning an empty document if it doesn't exist.

    Args:
        path: Path to the TOML file.

    Returns:
        The parsed TOML document.
    """
    if path.exists():
        try:
            with path.open() as f:
                return tomlkit.load(f)
        except tomlkit.exceptions.TOMLKitError as e:
            log.error("Failed to parse TOML file %s: %s", path, e)
    return tomlkit.document()


def save_toml(path: Path, doc: tomlkit.TOMLDocument) -> None:
    """Save a TOML document to a file.

    Args:
        path: Path to save to.
        doc: The TOML document to save.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        tomlkit.dump(doc, f)


def get_global_values(doc: tomlkit.TOMLDocument) -> dict[str, Any]:
    """Extract top-level scalar values from a TOML document.

    Args:
        doc: The TOML document.

    Returns:
        Dictionary of global (non-table) values.
    """
    return {
        key: value for key, value in doc.items() if not isinstance(value, (dict, Table))
    }


def get_app_values(doc: tomlkit.TOMLDocument, app: str) -> dict[str, Any]:
    """Extract app-specific values from a TOML document.

    Args:
        doc: The TOML document.
        app: The application name.

    Returns:
        Dictionary of app-specific values.
    """
    section = doc.get(app, {})
    if isinstance(section, (dict, Table)):
        return dict(section)
    return {}


def set_app_value(
    doc: tomlkit.TOMLDocument, app: str | None, key: str, value: Any
) -> tomlkit.TOMLDocument:
    """Set a value in an app-specific section.

    If value is ``None``, the key is removed from the section instead,
    since TOML has no null type.

    Args:
        doc: The TOML document.
        app: The application name.
        key: The setting key.
        value: The value to set, or ``None`` to remove the key.

    Returns:
        The modified document.
    """
    if app is not None:
        if value is None:
            # TOML has no null — remove the key to represent "unset"
            if app in doc and key in doc[app]:
                del doc[app][key]
        else:
            if app not in doc:
                doc.add(app, tomlkit.table())
            doc[app][key] = _to_toml_value(value)
    else:
        if value is None:
            if key in doc:
                del doc[key]
        else:
            doc[key] = _to_toml_value(value)
    return doc


def _to_toml_value(value: Any) -> Any:
    """Convert a Python value to a TOML-compatible value.

    Args:
        value: The value to convert.

    Returns:
        The TOML-compatible value.
    """
    from pathlib import Path

    from upath import UPath

    if isinstance(value, (Path, UPath)):
        return str(value)
    if isinstance(value, list):
        return [_to_toml_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_toml_value(v) for k, v in value.items()}
    return value
