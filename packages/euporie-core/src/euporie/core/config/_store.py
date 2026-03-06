"""Base class for typed setting stores with layered resolution."""

from __future__ import annotations

import json
import logging
from collections import ChainMap
from collections.abc import Mapping
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, ClassVar

import fastjsonschema
from apptk.commands import add_cmd
from apptk.filters.base import Condition
from apptk.utils import Event

if TYPE_CHECKING:
    from collections.abc import Callable

    from euporie.core.config._layers import Layer
    from euporie.core.config._setting import Setting

log = logging.getLogger(__name__)


class JSONEncoderPlus(json.JSONEncoder):
    """JSON encoder that handles paths as strings."""

    def default(self, o: Any) -> bool | int | float | str | None:
        """Encode an object to JSON.

        Args:
            o: The object to encode.

        Returns:
            The encoded object.
        """
        from upath import UPath

        if isinstance(o, (Path, UPath)):
            return str(o)
        return json.JSONEncoder.default(self, o)


_json_encoder = JSONEncoderPlus()


class DefaultNamespace(SimpleNamespace):
    """A namespace that creates default values for undefined attributes.

    Attributes:
        _factory: A callable that generates default values.
    """

    def __init__(
        self,
        default_factory: Callable[[str], Any] | None = None,
        mapping_or_iterable: Mapping | tuple[tuple[str, Any], ...] | None = None,
        /,
        **kwargs: Any,
    ) -> None:
        """Initialize the DefaultNamespace.

        Args:
            default_factory: Factory for creating default values.
            mapping_or_iterable: Initial values.
            **kwargs: Additional initial values.
        """
        if mapping_or_iterable is None:
            mapping_or_iterable = {}
        super().__init__(**dict(mapping_or_iterable), **kwargs)
        self._factory = default_factory

    def __getattribute__(self, name: str) -> Any:
        """Get an attribute, creating it if needed.

        Args:
            name: The attribute name.

        Returns:
            The attribute value.

        Raises:
            AttributeError: If the attribute doesn't exist and no factory is set.
        """
        try:
            return super().__getattribute__(name)
        except AttributeError:
            factory = super().__getattribute__("_factory")
            if factory is None:
                raise
            value = factory(name)
            setattr(self, name, value)
            return value


class SettingStore:
    """Base class for typed, validated setting stores.

    Subclasses configure which layers to use for value resolution.
    Each subclass maintains its own setting registry via ``_registry``.

    Attributes:
        events: Namespace of events for each setting.
        filters: Namespace of filters for each setting.
        defaults: Namespace providing default values.
        choices: Namespace providing choices for each setting.
        menus: Namespace providing menu items for each setting.
    """

    _registry: ClassVar[dict[str, Setting]]

    def __init__(
        self,
        app: str,
        *,
        layers: list[Layer],
        overrides: dict[str, Any] | None = None,
    ) -> None:
        """Create a new setting store.

        Args:
            app: The application name.
            layers: Middle layers (between defaults and overrides).
            overrides: Initial programmatic override values.
        """
        from euporie.core.config._layers import DefaultsLayer, OverridesLayer, TomlFileLayer

        self._app = app
        self._settings_cache: dict[str, Setting] | None = None
        self._resolved_cache: dict[str, Any] = {}

        # Build full layer stack: defaults (bottom) -> middle -> overrides (top)
        self._defaults_layer = DefaultsLayer()
        self._overrides_layer = OverridesLayer(overrides or {})
        self._layers = [self._defaults_layer, *layers, self._overrides_layer]

        # Find the writable layer for persisting changes
        self._writable_layer: TomlFileLayer | None = None
        for layer in layers:
            if isinstance(layer, TomlFileLayer) and layer._writable:
                self._writable_layer = layer
                break

        # ChainMap over the layer dicts: highest-priority first
        self._chain: ChainMap[str, Any] = ChainMap(
            *(layer for layer in reversed(self._layers))
        )

        # Create event/filter/etc namespaces
        self.events = DefaultNamespace(
            lambda name: Event(self._registry.get(name), self._on_change)
        )
        self.filters = DefaultNamespace(
            lambda name: Condition(lambda: bool(self._resolve(name)))
        )
        self.defaults = DefaultNamespace(lambda name: self._defaults.get(name))
        self.choices = DefaultNamespace(
            lambda name: (
                self._registry[name].choices if name in self._registry else None
            )
        )
        self.menus = DefaultNamespace(
            lambda name: self._registry[name].menu if name in self._registry else None
        )

        # Schema validation
        self._valid_config = True
        self._schema_validate = fastjsonschema.compile(self._schema, use_default=False)

    @property
    def settings(self) -> dict[str, Setting]:
        """Return settings applicable to this app."""
        if self._settings_cache is None:
            self._settings_cache = {
                name: setting
                for name, setting in self._registry.items()
                if setting.applies_to(self._app)
            }
        return self._settings_cache

    @property
    def _schema(self) -> dict[str, Any]:
        """Return a JSON schema for validation."""
        return {
            "title": f"{type(self).__name__} Schema",
            "description": f"Schema for {type(self).__name__}",
            "type": "object",
            "properties": {
                name: setting.schema for name, setting in self.settings.items()
            },
        }

    def _resolve(self, name: str) -> Any:
        """Resolve a setting value through the layer chain.

        Higher-index layers have higher priority. Defaults form the
        lowest-priority layer in the chain.

        Args:
            name: The setting name.

        Returns:
            The resolved value, or ``None`` if unknown.
        """
        return self._chain.get(name)

    def load(self) -> None:
        """Load values from all layers."""
        self._resolved_cache.clear()
        applicable = self.settings
        for layer in self._layers:
            layer.load(applicable)
            validated = self._validate(layer, type(layer).__name__)
            # Replace contents in-place so the ChainMap sees new values
            layer.clear()
            layer.update(validated)

        self._register_all_commands()

    def _validate(self, data: dict[str, Any], source: str) -> dict[str, Any]:
        """Validate setting values against the schema.

        Args:
            data: The values to validate.
            source: Description of the source for error messages.

        Returns:
            Dictionary of validated values.
        """
        validated = {}
        applicable = self.settings
        for name, value in data.items():
            if name in applicable:
                setting = applicable[name]
                if value is None and setting.nullable:
                    validated[name] = value
                    continue
                json_data = json.loads(_json_encoder.encode({name: value}))
                try:
                    self._schema_validate(json_data)
                    validated[name] = value
                except fastjsonschema.JsonSchemaValueException as error:
                    log.warning(
                        "Invalid %s setting: `%s = %r`\n%s",
                        source,
                        name,
                        value,
                        error.message.replace("data.", ""),
                    )
            elif name not in self._registry:
                if not isinstance(value, dict):
                    log.warning("Option '%s' not recognised in %s", name, source)
        return validated

    def _on_change(self, setting: Setting) -> None:
        """Handle a setting value change by saving to the writable layer.

        Args:
            setting: The setting that changed.
        """
        if not self._valid_config:
            return

        if self._writable_layer is None:
            return

        value = self._resolve(setting.name)
        self._writable_layer.save(setting.name, value)
        log.debug("Saved `%s = %r`", setting.name, value)

    def _register_all_commands(self) -> None:
        """Register commands for all applicable settings."""
        for setting in self.settings.values():
            self._register_commands(setting)
            for hook in setting.hooks:
                event = getattr(self.events, setting.name)
                event += hook

    def _register_commands(self, setting: Setting) -> None:
        """Register commands to modify a setting.

        Args:
            setting: The setting to register commands for.
        """
        cmd_name = setting.name.replace("_", "-")
        schema = setting.schema

        if schema.get("type") == "array":
            for choice in setting.choices or schema.get("items", {}).get("enum") or []:
                add_cmd(
                    name=f"toggle-{cmd_name}-{choice}",
                    hidden=setting.hidden,
                    toggled=Condition(
                        partial(
                            lambda c: c in (self._resolve(setting.name) or []),
                            choice,
                        )
                    ),
                    title=f"Toggle {choice} in {setting.title}",
                    menu_title=str(choice).replace("_", " ").capitalize(),
                    description=f'Toggle "{choice}" in "{setting.name}"',
                    filter=setting.kwargs.get("filter", True),
                )(
                    partial(
                        lambda c: (
                            self._resolve(setting.name).remove
                            if c in self._resolve(setting.name)
                            else self._resolve(setting.name).append
                        )(c),
                        choice,
                    )
                )

        elif setting.type is bool:
            add_cmd(
                name=f"toggle-{cmd_name}",
                toggled=Condition(lambda: bool(self._resolve(setting.name))),
                hidden=setting.hidden,
                title=f"Toggle {setting.title}",
                menu_title=setting.kwargs.get("menu_title", setting.title.capitalize()),
                description=setting.help,
                filter=setting.kwargs.get("filter", True),
                keys=setting.kwargs.get("keys"),
            )(partial(self.toggle, setting.name))

        elif setting.type is int or setting.choices is not None:
            add_cmd(
                name=f"switch-{cmd_name}",
                hidden=setting.hidden,
                title=f"Switch {setting.title}",
                menu_title=setting.kwargs.get("menu_title"),
                description=f'Cycle through values for "{setting.name}"',
                filter=setting.kwargs.get("filter", True),
                keys=setting.kwargs.get("keys"),
            )(partial(self.toggle, setting.name))

        choices = setting.choices or schema.get("enum", []) or []
        if isinstance(choices, dict):
            choices = list(choices.keys())
        for choice in choices:
            add_cmd(
                name=f"set-{cmd_name}-{choice}",
                hidden=setting.hidden,
                toggled=Condition(
                    partial(lambda c: self._resolve(setting.name) == c, choice)
                ),
                title=f"Set {setting.title} to {choice}",
                menu_title=str(choice).replace("_", " ").capitalize(),
                description=f'Set "{setting.name}" to "{choice}"',
                filter=setting.kwargs.get("filter", True),
            )(partial(setattr, self, setting.name, choice))

    def toggle(self, name: str) -> None:
        """Toggle or cycle a setting's value.

        Args:
            name: The setting name.
        """
        setting = self._registry[name]
        value = self._resolve(name)

        if setting.type is bool:
            new = not value
        elif (
            setting.type is int
            and "minimum" in (schema := setting.schema)
            and "maximum" in schema
        ):
            new = schema["minimum"] + (value - schema["minimum"] + 1) % (
                schema["maximum"] + 1
            )
        elif setting.choices is not None:
            choices = (
                list(setting.choices.keys())
                if isinstance(setting.choices, dict)
                else setting.choices
            )
            new = choices[(choices.index(value) + 1) % len(choices)]
        else:
            raise NotImplementedError(f"Cannot toggle setting {name}")

        setattr(self, name, new)

    def __getattribute__(self, name: str) -> Any:
        """Enable access of settings via dotted attributes."""
        try:
            return super().__getattribute__(name)
        except AttributeError as exc:
            if name in self.settings:
                cache = super().__getattribute__("_resolved_cache")
                if name in cache:
                    return cache[name]

                setting = self.settings[name]
                value = self._resolve(name)

                # Convert choice aliases
                if isinstance(choices := setting.choices, Mapping):
                    value = choices.get(value, value)

                # Apply validation/transformation
                if isinstance(value, list):
                    # Cast to native list
                    value = list(value)
                    for i, item in enumerate(value):
                        if setting.validate:
                            try:
                                value[i] = setting.validate(item)
                            except (ValueError, TypeError) as e:
                                raise e
                else:
                    if setting.validate:
                        try:
                            value = setting.validate(value)
                        except (ValueError, TypeError):
                            pass

                cache[name] = value
                return value
            raise exc

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the store for the current app."""
        return key in self.settings and key in self._chain and self._chain[key] is not None

    @classmethod
    def register(cls, name: str, *args: Any, **kwargs: Any) -> None:
        """Register a new setting in this store's registry.

        Args:
            name: The setting name.
            *args: Positional arguments for Setting.
            **kwargs: Keyword arguments for Setting.
        """
        from euporie.core.config._setting import Setting

        if name in cls._registry:
            log.warning("Setting '%s' already registered, overwriting", name)
        setting = Setting(name, *args, **kwargs)
        cls._registry[name] = setting

    def __setattr__(self, name: str, value: Any) -> None:
        """Set a setting value via the overrides layer."""
        if name in self._registry and name in self.settings:
            setting = self.settings[name]
            if isinstance(choices := setting.choices, Mapping):
                for k, v in choices.items():
                    if v == value:
                        value = k
                        break
            # Invalidate cached resolved value
            self._resolved_cache.pop(name, None)
            # Writing to the overrides layer automatically updates the
            # ChainMap, so _resolve sees the new value immediately.
            self._overrides_layer[name] = value
            getattr(self.events, name)()
        else:
            super().__setattr__(name, value)
