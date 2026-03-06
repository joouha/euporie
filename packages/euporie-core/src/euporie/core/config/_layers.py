"""Value resolution layers for the setting store."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from ast import literal_eval
from typing import TYPE_CHECKING, Any

from euporie.core.config._toml import (
    get_app_values,
    get_global_values,
    load_toml,
    save_toml,
    set_app_value,
)

if TYPE_CHECKING:
    from argparse import ArgumentParser
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
    """Provides default values from setting definitions."""

    def load(self, settings: dict[str, Setting]) -> None:
        """Load default values into the layer.

        Args:
            settings: The settings to get defaults for.
        """
        self.clear()
        self.update({name: s.default for name, s in settings.items()})


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
        writable: Whether this layer supports saving.
    """

    def __init__(
        self,
        path: Path,
        namespace: str | None = None,
        *,
        writable: bool = False,
    ) -> None:
        """Initialize the TOML file layer.

        Args:
            path: Path to the TOML file.
            namespace: App namespace (reads [namespace] section if set).
            writable: Whether saving is supported.
        """
        self._path = path
        self._namespace = namespace
        self._writable = writable

    def load(self, settings: dict[str, Setting]) -> None:
        """Load values from the TOML file into the layer.

        Args:
            settings: The settings to load values for.
        """
        doc = load_toml(self._path)
        if self._namespace is not None:
            raw = get_app_values(doc, self._namespace)
        else:
            raw = get_global_values(doc)
        self.clear()
        self.update(raw)

    def save(self, key: str, value: Any) -> None:
        """Save a value to the TOML file.

        Args:
            key: The setting name.
            value: The value to save.

        Raises:
            NotImplementedError: If this layer is not writable.
        """
        if not self._writable:
            raise NotImplementedError("This layer is read-only")
        doc = load_toml(self._path)
        set_app_value(doc, self._namespace, key, value)
        save_toml(self._path, doc)


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

    Args:
        parser: The argument parser to use.
    """

    def __init__(self, parser: ArgumentParser) -> None:
        """Initialize the CLI layer.

        Args:
            parser: The argument parser.
        """
        self._parser = parser
        self._populated = False

    def load(self, settings: dict[str, Setting]) -> None:
        """Parse CLI arguments and load non-None values into the layer.

        Args:
            settings: Settings to add to the parser before parsing.
        """
        if not self._populated:
            self._populate(settings)
            self._populated = True

        namespace, _remainder = self._parser.parse_known_intermixed_args()
        self.clear()
        self.update({k: v for k, v in vars(namespace).items() if v is not None})

    def _populate(self, settings: dict[str, Setting]) -> None:
        """Add settings to the argument parser.

        Args:
            settings: Settings to register as CLI arguments.
        """
        for setting in settings.values():
            args, kwargs = setting.parser_args
            if args:
                self._parser.add_argument(*args, **kwargs)
