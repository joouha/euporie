"""Value resolution layers for the setting store."""

from __future__ import annotations

import argparse
import json
import logging
import os
from abc import ABC, abstractmethod
from ast import literal_eval
from typing import TYPE_CHECKING, Any

import tomlkit
from tomlkit.items import Table

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from euporie.core.config._setting import Setting

log = logging.getLogger(__name__)


class Layer(ABC, dict[str, Any]):
    """A source of setting values in the resolution chain.

    Layers are ordered by priority. Higher-priority layers override
    lower-priority ones during value resolution.

    As a dict subclass, each layer instance *is* the mapping of its
    loaded values, so it can be used directly in a :py:class:`ChainMap`.
    """

    @property
    def persistable(self) -> bool:
        """Whether this layer supports persisting values to its backing store."""
        return False

    @abstractmethod
    def load(self, settings: dict[str, Setting]) -> None:
        """Load values from this layer into the dict.

        Args:
            settings: The settings to load values for.
        """
        ...

    def save(self, key: str, value: Any) -> None:
        """Persist a value to this layer.

        Args:
            key: The setting name.
            value: The value to save.

        Raises:
            NotImplementedError: If this layer doesn't support saving.
        """
        raise NotImplementedError


class DefaultsLayer(Layer):
    """Provides default values from setting definitions.

    Loaded at initialization as setting defaults are already known.
    """

    def __init__(self, settings: dict[str, Setting]) -> None:
        self.update({name: s.default for name, s in settings.items()})

    def load(self, settings: dict[str, Setting]) -> None:
        """No-op: default are loaded at initialization.

        Args:
            settings: The settings (unused, overrides are freeform).
        """


class OverridesLayer(Layer):
    """Programmatic overrides set via ``__setattr__``."""

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        """Initialize with optional initial values.

        Args:
            initial: Initial override values.
        """
        super().__init__()
        self.update(initial or {})

    def load(self, settings: dict[str, Setting]) -> None:
        """No-op: overrides are written directly to the layer dict.

        Args:
            settings: The settings (unused, overrides are freeform).
        """


class TomlFileLayer(Layer):
    """Read and write values from a TOML file.

    When namespace is None, reads top-level (global) values.
    When namespace is set (e.g. "notebook"), reads from that section.

    Args:
        path: Path to the TOML file.
        namespace: Optional app namespace for section-scoped access.
        persistable: Whether this layer supports persisting values.
    """

    def __init__(
        self,
        path: Path,
        namespace: str | None = None,
        *,
        persistable: bool = False,
    ) -> None:
        """Initialize the TOML file layer.

        Args:
            path: Path to the TOML file.
            namespace: App namespace (reads [namespace] section if set).
            persistable: Whether persisting is supported.
        """
        self._path = path
        self._namespace = namespace
        self._persistable = persistable

    @property
    def persistable(self) -> bool:
        """Whether this layer supports persisting values to its backing store."""
        return self._persistable

    def load(self, settings: dict[str, Setting]) -> None:
        """Load values from the TOML file into the layer.

        Args:
            settings: The settings to load values for.
        """
        doc = self._load_toml()
        if self._namespace is not None:
            raw = self._get_app_values(doc)
        else:
            raw = self._get_global_values(doc, settings)
        self.clear()
        self.update(raw)

    def save(self, key: str, value: Any) -> None:
        """Save a value to the TOML file.

        Args:
            key: The setting name.
            value: The value to save.

        Raises:
            NotImplementedError: If this layer is not persistable.
        """
        if not self.persistable:
            raise NotImplementedError("This layer is not persistable")
        doc = self._load_toml()
        self._set_value(doc, key, value)
        self._save_toml(doc)

    def _load_toml(self) -> tomlkit.TOMLDocument:
        """Load the TOML file, returning an empty document if it doesn't exist.

        Returns:
            The parsed TOML document.
        """
        if self._path.exists():
            try:
                with self._path.open() as f:
                    return tomlkit.load(f)
            except tomlkit.exceptions.TOMLKitError as e:
                log.error("Failed to parse TOML file %s: %s", self._path, e)
        return tomlkit.document()

    def _save_toml(self, doc: tomlkit.TOMLDocument) -> None:
        """Save a TOML document to the file.

        Args:
            doc: The TOML document to save.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as f:
            tomlkit.dump(doc, f)

    def _get_global_values(
        self, doc: tomlkit.TOMLDocument, settings: dict[str, Setting]
    ) -> dict[str, Any]:
        """Extract top-level values from a TOML document.

        Top-level tables are included only when they correspond to a known
        setting name (e.g. ``key_bindings``).  Other tables are assumed to
        be app-namespace sections and are skipped.

        Args:
            doc: The TOML document.
            settings: Known settings, used to distinguish setting tables
                from namespace sections.

        Returns:
            Dictionary of global values.
        """
        return {
            key: value
            for key, value in doc.items()
            if not isinstance(value, (dict, Table)) or key in settings
        }

    def _get_app_values(self, doc: tomlkit.TOMLDocument) -> dict[str, Any]:
        """Extract app-specific values from the TOML document.

        Args:
            doc: The TOML document.

        Returns:
            Dictionary of app-specific values.
        """
        section = doc.get(self._namespace, {})
        if isinstance(section, (dict, Table)):
            return dict(section)
        return {}

    def _set_value(self, doc: tomlkit.TOMLDocument, key: str, value: Any) -> None:
        """Set a value in the TOML document.

        If value is ``None``, the key is removed instead, since TOML has
        no null type.

        Args:
            doc: The TOML document.
            key: The setting key.
            value: The value to set, or ``None`` to remove the key.
        """
        ns = self._namespace
        if ns is not None:
            if value is None:
                if ns in doc and key in doc[ns]:
                    del doc[ns][key]
            else:
                if ns not in doc:
                    doc.add(ns, tomlkit.table())
                doc[ns][key] = self._to_toml_value(value)
        else:
            if value is None:
                if key in doc:
                    del doc[key]
            else:
                doc[key] = self._to_toml_value(value)

    @staticmethod
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
            return [TomlFileLayer._to_toml_value(v) for v in value]
        if isinstance(value, dict):
            return {k: TomlFileLayer._to_toml_value(v) for k, v in value.items()}
        return value


class JsonFileLayer(Layer):
    """Read and write values from a JSON file.

    When namespace is None, reads top-level (global) values.
    When namespace is set (e.g. "notebook"), reads from that section.

    Args:
        path: Path to the JSON file.
        namespace: Optional app namespace for section-scoped access.
        persistable: Whether this layer supports persisting values.
    """

    def __init__(
        self,
        path: Path,
        namespace: str | None = None,
        *,
        persistable: bool = False,
    ) -> None:
        """Initialize the JSON file layer.

        Args:
            path: Path to the JSON file.
            namespace: App namespace (reads [namespace] section if set).
            persistable: Whether persisting is supported.
        """
        self._path = path
        self._namespace = namespace
        self._persistable = persistable

    @property
    def persistable(self) -> bool:
        """Whether this layer supports persisting values to its backing store."""
        return self._persistable

    def load(self, settings: dict[str, Setting]) -> None:
        """Load values from the JSON file into the layer.

        Args:
            settings: The settings to load values for.
        """
        doc = self._load_json()
        if self._namespace is not None:
            raw = self._get_app_values(doc)
        else:
            raw = self._get_global_values(doc, settings)
        self.clear()
        self.update(raw)

    def save(self, key: str, value: Any) -> None:
        """Save a value to the JSON file.

        Args:
            key: The setting name.
            value: The value to save.

        Raises:
            NotImplementedError: If this layer is not persistable.
        """
        if not self.persistable:
            raise NotImplementedError("This layer is not persistable")
        doc = self._load_json()
        self._set_value(doc, key, value)
        self._save_json(doc)

    def _load_json(self) -> dict[str, Any]:
        """Load the JSON file, returning an empty dict if it doesn't exist.

        Returns:
            The parsed JSON data.
        """
        if self._path.exists():
            try:
                with self._path.open() as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
                log.error("JSON file %s does not contain an object", self._path)
            except (json.JSONDecodeError, OSError) as e:
                log.error("Failed to parse JSON file %s: %s", self._path, e)
        return {}

    def _save_json(self, doc: dict[str, Any]) -> None:
        """Save a dictionary to the JSON file.

        Args:
            doc: The data to save.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as f:
            json.dump(doc, f, indent=2, default=self._to_json_value)
            f.write("\n")

    def _get_global_values(
        self, doc: dict[str, Any], settings: dict[str, Setting]
    ) -> dict[str, Any]:
        """Extract top-level values from a JSON document.

        Top-level dicts are included only when they correspond to a known
        setting name (e.g. ``key_bindings``).  Other dicts are assumed to
        be app-namespace sections and are skipped.

        Args:
            doc: The JSON data.
            settings: Known settings, used to distinguish setting dicts
                from namespace sections.

        Returns:
            Dictionary of global values.
        """
        return {
            key: value
            for key, value in doc.items()
            if not isinstance(value, dict) or key in settings
        }

    def _get_app_values(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Extract app-specific values from the JSON document.

        Args:
            doc: The JSON data.

        Returns:
            Dictionary of app-specific values.
        """
        section = doc.get(self._namespace, {})
        if isinstance(section, dict):
            return dict(section)
        return {}

    def _set_value(self, doc: dict[str, Any], key: str, value: Any) -> None:
        """Set a value in the JSON document.

        Unlike the TOML layer, JSON supports ``null``, so ``None`` values
        are stored rather than causing key removal.

        Args:
            doc: The JSON data.
            key: The setting key.
            value: The value to set.
        """
        value = self._to_json_value(value)
        ns = self._namespace
        if ns is not None:
            if ns not in doc:
                doc[ns] = {}
            doc[ns][key] = value
        else:
            doc[key] = value

    @staticmethod
    def _to_json_value(value: Any) -> Any:
        """Convert a Python value to a JSON-compatible value.

        Args:
            value: The value to convert.

        Returns:
            The JSON-compatible value.
        """
        from pathlib import Path

        from upath import UPath

        if value is None:
            return None
        if isinstance(value, (Path, UPath)):
            return str(value)
        if isinstance(value, list):
            return [JsonFileLayer._to_json_value(v) for v in value]
        if isinstance(value, dict):
            return {k: JsonFileLayer._to_json_value(v) for k, v in value.items()}
        return value


class EnvironmentLayer(Layer):
    """Read values from environment variables.

    Without namespace: reads ``EUPORIE_COLOR_SCHEME``.
    With namespace "notebook": reads ``EUPORIE_NOTEBOOK_COLOR_SCHEME``.

    Args:
        prefix: Base prefix (e.g. "euporie").
        namespace: Optional app namespace inserted after prefix.
    """

    def __init__(self, prefix: str, namespace: str | None = None) -> None:
        """Initialize the environment layer.

        Args:
            prefix: Base prefix for env var names.
            namespace: Optional app namespace inserted after prefix.
        """
        self._prefix = prefix
        self._namespace = namespace

    def load(self, settings: dict[str, Setting]) -> None:
        """Load values from environment variables into the layer.

        Args:
            settings: The settings to look up env vars for.
        """
        self.clear()
        for name in settings:
            if self._namespace:
                env_var = f"{self._prefix}_{self._namespace}_{name}".upper()
            else:
                env_var = f"{self._prefix}_{name}".upper()

            if env_var in os.environ:
                self[name] = self._parse(os.environ[env_var])

    @staticmethod
    def _parse(value: str) -> Any:
        """Parse an environment variable string value.

        Args:
            value: The raw string value.

        Returns:
            The parsed value.
        """
        try:
            return literal_eval(value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            return value


class CliLayer(Layer):
    """Read values from command-line arguments.

    Performs a two-pass parse so that settings like ``syntax_theme`` are
    available to the argument parser before ``--help`` is processed:

    1. First pass: populate the parser **without** help and parse all known
       args.  The resulting values are loaded into the layer so that lazily
       evaluated references (e.g. the parser's ``syntax_theme`` callable)
       resolve correctly.
    2. Second pass: enable help on the parser and parse the remaining args.
       If ``--help`` was given it will now trigger with the correct theme.

    Args:
        validate: Function to validate the passed CLI arguments.
        description: Help text for the argument parser.
        epilog: Epilog text for the argument parser.
        syntax_theme: Callable returning the syntax theme name.
    """

    def __init__(
        self,
        validate: Callable[[dict[str, Any]], dict[str, Any]],
        description: str = "",
        epilog: str = "",
        syntax_theme: Callable[[], str] | None = None,
        args: list[str] | None = None,
    ) -> None:
        """Initialize the CLI layer.

        Args:
            validate: Function to validate the passed CLI arguments.
            description: Help text for the argument parser.
            epilog: Epilog text for the argument parser.
            syntax_theme: Callable returning the syntax theme name.
            args: Explicit argument list to parse instead of ``sys.argv``.
        """
        from euporie.core.config._parser import ArgumentParser, MetavarTypeHelpFormatter

        self.parser = ArgumentParser(
            description=description,
            epilog=epilog,
            allow_abbrev=True,
            formatter_class=MetavarTypeHelpFormatter,
            argument_default=argparse.SUPPRESS,
            add_help=False,
            syntax_theme=syntax_theme,
        )
        self._validate = validate
        self._loaded = False
        self._args = args
        self.remaining_args: list[str] = []

    def load(self, settings: dict[str, Setting]) -> None:
        """Parse CLI arguments in two passes and load values.

        On first load, settings are added to the parser in two phases:

        1. Optional (non-required) settings are added and parsed without
           help so that values like ``syntax_theme`` become available
           before help is rendered.
        2. Required settings and the help action are added, then the
           remaining args are parsed.  If ``--help`` is present it now
           renders with the correct theme.

        On subsequent loads the parser is already fully populated, so a
        single parse pass is sufficient.

        Args:
            settings: Settings to add to the parser before parsing.
        """
        if self._loaded:
            # Parser is already fully populated — single pass is enough.
            namespace, remaining = self.parser.parse_known_intermixed_args(self._args)
            self.clear()
            self.update(
                {k: v for k, v in vars(namespace).items() if v is not argparse.SUPPRESS}
            )
            self.remaining_args = remaining
            return

        _all_settings = set(settings)
        # First pass: add only optional settings, parse without help
        for name, setting in settings.items():
            args, kwargs = setting.parser_args
            if not kwargs.get("required") and all(x.startswith("-") for x in args):
                _all_settings.remove(name)
                self.parser.add_argument(*args, **kwargs)

        namespace, remaining = self.parser.parse_known_intermixed_args(self._args)
        self.clear()
        self.update(
            self._validate(
                {k: v for k, v in vars(namespace).items() if v is not argparse.SUPPRESS}
            )
        )

        # Second pass: add required settings and help, parse remaining
        for name in _all_settings:
            args, kwargs = settings[name].parser_args
            self.parser.add_argument(*args, **kwargs)

        # Add help parameter
        self.parser.add_argument(
            "-h",
            "--help",
            action="help",
            default=argparse.SUPPRESS,
            help="show this help message and exit",
        )

        namespace, final_remaining = self.parser.parse_known_intermixed_args(remaining)
        self.update({k: v for k, v in vars(namespace).items() if v is not None})
        self.remaining_args = final_remaining

        self._loaded = True
