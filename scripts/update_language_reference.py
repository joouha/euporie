"""Generate euporie language reference data from Helix editor's languages.toml.

Fetches the Helix languages.toml, parses it, and writes:
  - packages/euporie-core/src/euporie/core/languages.py

containing KNOWN_LANGUAGES, KNOWN_LSP_SERVERS, and KNOWN_FORMATTERS dicts.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from pprint import pformat
from typing import Any

import tomllib
from upath import UPath

OUTPUT_PATH = Path("packages/euporie-core/src/euporie/core/languages.py")

SOURCE_URL = "https://github.com/helix-editor/helix/raw/master/languages.toml"


def replace_helix(obj: Any) -> Any:
    """Recursively replace 'helix' with 'euporie' in all string values."""
    if isinstance(obj, str):
        return obj.replace("helix", "euporie").replace("Helix", "Euporie")
    if isinstance(obj, dict):
        return {k: replace_helix(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [replace_helix(v) for v in obj]
    if isinstance(obj, set):
        return {replace_helix(v) for v in obj}
    return obj


def extract_server_name(entry: str | dict[str, Any]) -> str | None:
    """Extract the LSP server name from a language-servers list entry.

    Entries can be plain strings or dicts like
    ``{"name": "erlang-ls", "except-features": [...]}``.
    """
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return entry.get("name")
    return None


def merge_command_args(data: dict[str, Any]) -> list[str]:
    """Merge 'command' and 'args' into a single command list."""
    cmd = data.get("command", "")
    args = data.get("args", [])
    return [cmd, *args]


def build_lsp_servers(raw_servers: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build the KNOWN_LSP_SERVERS dict from parsed TOML data."""
    servers: dict[str, dict[str, Any]] = {}
    for name, raw in raw_servers.items():
        entry: dict[str, Any] = {}
        entry["command"] = merge_command_args(raw)
        if "config" in raw:
            entry["settings"] = raw["config"]
        if "timeout" in raw:
            entry["timeout"] = raw["timeout"]
        servers[name] = replace_helix(entry)
    return servers


def build_languages(
    raw_languages: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build the KNOWN_LANGUAGES dict from parsed TOML data."""
    languages: dict[str, dict[str, Any]] = {}
    for raw in raw_languages:
        name = raw.get("name")
        if not name:
            continue

        entry: dict[str, Any] = {}

        # Language servers
        ls_names = []
        for ls_entry in raw.get("language-servers", []):
            if sname := extract_server_name(ls_entry):
                ls_names.append(sname)
        entry["language_servers"] = ls_names

        # Comment tokens (always a list)
        ct = raw.get("comment-tokens") or raw.get("comment-token")
        if ct is None:
            entry["comment_token"] = []
        elif isinstance(ct, str):
            entry["comment_token"] = [ct]
        else:
            entry["comment_token"] = list(ct)

        # Indent
        indent_raw = raw.get("indent")
        if isinstance(indent_raw, dict):
            entry["indent"] = {
                "tab_width": indent_raw.get("tab-width", 4),
                "unit": indent_raw.get("unit", "    "),
            }
        else:
            entry["indent"] = None

        # File types (plain strings only, skip glob dicts)
        entry["file_types"] = [
            ft for ft in raw.get("file-types", []) if isinstance(ft, str)
        ]

        # Formatter (raw, will be processed by build_formatters)
        fmt_raw = raw.get("formatter")
        if isinstance(fmt_raw, dict) and "command" in fmt_raw:
            entry["formatter"] = {
                "command": merge_command_args(fmt_raw),
            }
        else:
            entry["formatter"] = None

        # Formatters list will be populated by build_formatters
        entry["formatters"] = []

        languages[name] = replace_helix(entry)

    return languages


def build_formatters(
    languages: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build the KNOWN_FORMATTERS dict from language data.

    Extracts unique formatter definitions keyed by the executable name,
    and updates each language entry with a ``formatters`` list referencing
    the formatter names.
    """
    formatters: dict[str, dict[str, Any]] = {}
    for _lang_name, lang_data in languages.items():
        if fmt := lang_data.get("formatter"):
            command = fmt["command"]
            # Use the executable name as the formatter key
            fmt_name = command[0]
            if fmt_name not in formatters:
                formatters[fmt_name] = {"command": command}
            lang_data["formatters"] = [fmt_name]
        else:
            lang_data["formatters"] = []
        # Remove the raw formatter entry from the language data
        lang_data.pop("formatter", None)
    return formatters


def format_value(obj: Any, indent: int = 0) -> str:
    """Format a Python value for readable output.

    Uses pformat but fixes sets to use set literal syntax sorted alphabetically.
    """
    if isinstance(obj, set):
        if not obj:
            return "set()"
        items = ", ".join(repr(s) for s in sorted(obj))
        return "{" + items + "}"
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        pad = " " * (indent + 8)
        items = []
        for k, v in obj.items():
            formatted_v = format_value(v, indent + 8)
            items.append(f"{pad}{k!r}: {formatted_v},")
        inner = "\n".join(items)
        return "{\n" + inner + "\n" + " " * (indent + 4) + "}"
    return pformat(obj)


def format_dict(
    name: str, data: dict[str, Any], value_type: str = "dict[str, Any]"
) -> str:
    """Format a top-level dict assignment as readable Python source."""
    lines = [f"{name}: dict[str, {value_type}] = {{"]
    for key, value in data.items():
        formatted = format_value(value, 4)
        lines.append(f"    {key!r}: {formatted},")
    lines.append("}")
    return "\n".join(lines)


def generate_module(
    languages: dict[str, dict[str, Any]],
    servers: dict[str, dict[str, Any]],
    formatters: dict[str, list[str]],
) -> str:
    """Generate the full Python module source."""
    header = textwrap.dedent('''\
        """Language support reference data.

        Auto-generated from Helix editor's languages.toml by
        scripts/clone_helix_lsp_config.py - do not edit manually.
        """

        from __future__ import annotations

        from typing import Any

    ''')

    body_parts = [
        format_dict("KNOWN_LANGUAGES", languages),
        "",
        format_dict("KNOWN_LSP_SERVERS", servers),
        "",
        format_dict("KNOWN_FORMATTERS", formatters),
        "",
    ]

    return header + "\n".join(body_parts)


def main() -> None:
    """Fetch Helix languages.toml and generate languages.py."""
    print(f"Fetching {SOURCE_URL} ...")
    source = UPath(SOURCE_URL)
    with source.open("rb") as f:
        c = tomllib.load(f)

    print("Building LSP server definitions ...")
    servers = build_lsp_servers(c.get("language-server", {}))

    print("Building language definitions ...")
    languages = build_languages(c.get("language", []))

    print("Building formatter definitions ...")
    formatters = build_formatters(languages)

    print(f"Writing {OUTPUT_PATH} ...")
    module_src = generate_module(languages, servers, formatters)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(module_src)

    n_langs = len(languages)
    n_servers = len(servers)
    n_fmts = len(formatters)
    print(f"Done: {n_langs} languages, {n_servers} LSP servers, {n_fmts} formatters.")


if __name__ == "__main__":
    main()
