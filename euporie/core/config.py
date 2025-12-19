"""Define a configuration class for euporie.core."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from ast import literal_eval
from collections.abc import Callable
from functools import cached_property, partial
from pathlib import Path
from types import SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Any,
    TextIO,
    cast,
)

import fastjsonschema
from platformdirs import user_config_dir
from prompt_toolkit.filters.base import Condition
from prompt_toolkit.filters.utils import to_filter
from prompt_toolkit.utils import Event
from upath import UPath

from euporie.core import __app_name__, __copyright__
from euporie.core.commands import add_cmd, get_cmd

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence
    from typing import Any, ClassVar

    from _typeshed import SupportsWrite
    from prompt_toolkit.filters.base import FilterOrBool

    from euporie.core.widgets.menu import MenuItem


log = logging.getLogger(__name__)

_SCHEMA_TYPES: dict[type | Callable, str] = {
    bool: "boolean",
    str: "string",
    int: "integer",
    float: "number",
    UPath: "string",
}


class ArgumentParser(argparse.ArgumentParser):
    """An argument parser which lexes and formats the help message before printing it."""

    def __init__(self, *args: Any, config: Config, **kwargs: Any) -> None:
        """Initialize while saving a reference to the current config."""
        super().__init__(*args, **kwargs)
        self.config = config
        # Prevent coloring in the help message on 3.14+ (we do it ourselves)
        self.color = False

    def _print_message(
        self, message: str, file: SupportsWrite[str] | None = None
    ) -> None:
        from prompt_toolkit.formatted_text.base import FormattedText
        from prompt_toolkit.lexers.pygments import _token_cache
        from prompt_toolkit.shortcuts.utils import print_formatted_text
        from prompt_toolkit.styles.pygments import style_from_pygments_cls

        from euporie.core.pygments import ArgparseLexer
        from euporie.core.style import get_style_by_name

        if message:
            file = cast("TextIO | None", file)
            style = style_from_pygments_cls(get_style_by_name(self.config.syntax_theme))
            print_formatted_text(
                FormattedText(
                    [
                        (_token_cache[t], v)
                        for _, t, v in ArgparseLexer().get_tokens_unprocessed(
                            message.rstrip("\n")
                        )
                    ]
                ),
                file=file,
                style=style,
                include_default_pygments_style=False,
            )


class BooleanOptionalAction(argparse.Action):
    """Action for boolean flags.

    Included because `argparse.BooleanOptionalAction` is not present in `python<=3.9`.
    """

    def __init__(self, option_strings: list[str], *args: Any, **kwargs: Any) -> None:
        """Initiate the Action, as per `argparse.BooleanOptionalAction`."""
        _option_strings = list(option_strings)
        for option_string in option_strings:
            if option_string.startswith("--"):
                _option_strings.append(f"--no-{option_string[2:]}")
        kwargs["nargs"] = 0
        super().__init__(_option_strings, *args, **kwargs)

    def format_usage(self) -> str:
        """Format the action string.

        Returns:
            The formatted string.

        """
        return " | ".join(self.option_strings)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        """Set the value to True or False depending on the flag provided."""
        if option_string in self.option_strings:
            assert isinstance(option_string, str)
            setattr(namespace, self.dest, not option_string.startswith("--no-"))


TYPE_ACTIONS: dict[Callable[[Any], Any], type[argparse.Action]] = {
    bool: BooleanOptionalAction
}


class JSONEncoderPlus(json.JSONEncoder):
    """JSON encode class which encodes paths as strings."""

    def default(self, o: Any) -> bool | int | float | str | None:
        """Encode an object to JSON.

        Args:
            o: The object to encode

        Returns:
            The encoded object

        """
        if isinstance(o, Path):
            return str(o)
        return json.JSONEncoder.default(self, o)


_json_encoder = JSONEncoderPlus()


class Setting:
    """A single configuration item."""

    def __init__(
        self,
        name: str,
        group: str | Sequence[str],
        default: Any = None,
        help_: str = "",
        description: str = "",
        type_: Callable[[Any], Any] | None = None,
        title: str | None = None,
        choices: list[Any] | Callable[[], list[Any]] | None = None,
        action: argparse.Action | str | None = None,
        flags: list[str] | None = None,
        schema: dict[str, Any] | None = None,
        nargs: str | int | None = None,
        hidden: FilterOrBool = False,
        hooks: list[Callable[[Setting], None]] | None = None,
        cmd_filter: FilterOrBool = True,
        **kwargs: Any,
    ) -> None:
        """Create a new configuration item."""
        self.name = name
        self.groups = {group} if isinstance(group, str) else set(group)
        self.default = default
        self._value = default
        self.title = title or self.name.replace("_", " ")
        self.help = help_
        self.description = description
        self._choices = choices
        self.type = type_ or type(default)
        self.action = action or TYPE_ACTIONS.get(self.type)
        self.flags = flags or [f"--{name.replace('_', '-')}"]
        self._schema: dict[str, Any] = {
            "type": _SCHEMA_TYPES.get(self.type),
            **(schema or {}),
        }
        self.nargs = nargs
        self.hidden = to_filter(hidden)
        self.hooks = hooks or []
        self.cmd_filter = cmd_filter
        self.kwargs = kwargs

    @cached_property
    def choices(self) -> list[Any] | None:
        """Compute the setting's available options."""
        if callable(self._choices):
            return self._choices()
        else:
            return self._choices

    @property
    def schema(self) -> dict[str, Any]:
        """Return a json schema property for the config item."""
        schema = {
            "description": self.help,
            **({"default": self.default} if self.default is not None else {}),
            **self._schema,
        }
        if self.choices:
            if self.nargs == "*" or "items" in schema:
                schema["items"]["enum"] = self.choices
            else:
                schema["enum"] = self.choices
        return schema

    @property
    def menu(self) -> MenuItem:
        """Return a menu item for the setting."""
        from euporie.core.widgets.menu import MenuItem

        choices = (self.choices or self.schema.get("enum", [])) or []
        if choices:
            return MenuItem(
                self.title.capitalize(),
                children=[
                    cmd.menu
                    for cmd in sorted(
                        (
                            get_cmd(f"set-{self.name.replace('_', '-')}-{choice}")
                            for choice in choices
                        ),
                        key=lambda x: x.menu_title,
                    )
                ],
                description=self.help,
            )
        elif self.type in (bool, int):
            return get_cmd(f"toggle-{self.name.replace('_', '-')}").menu
        else:
            raise NotImplementedError

    @property
    def parser_args(self) -> tuple[list[str], dict[str, Any]]:
        """Return arguments for construction of an :class:`argparse.ArgumentParser`."""
        # If empty flags are passed, do not expose setting on command line
        if self.flags is not None and not self.flags:
            return [], {}
        args = self.flags or [self.name]

        kwargs: dict[str, Any] = {
            "action": self.action,
            "help": argparse.SUPPRESS if self.hidden() else self.help,
            # Do not set defaults for command line arguments, as default values
            # would override values set in the configuration file
            # "default": self.default,
        }

        if self.nargs:
            kwargs["nargs"] = self.nargs
        if self.type is not None and self.name != "version":
            kwargs["type"] = self.type
        if self.choices:
            kwargs["choices"] = self.choices
        if "version" in self.kwargs:
            kwargs["version"] = self.kwargs["version"]
        if "const" in self.kwargs:
            kwargs["const"] = self.kwargs["const"]

        return args, kwargs

    def __repr__(self) -> str:
        """Represent a :py:class`Setting` instance as a string."""
        return f"<Setting {self.name}: {self.type}>"


class DefaultNamespace(SimpleNamespace):
    """A namespace that creates default values for undefined attributes using a factory function.

    This class extends SimpleNamespace to provide automatic creation of default values when
    accessing undefined attributes, similar to collections.defaultdict but for object attributes.

    Attributes:
        _factory: A callable that generates default values for undefined attributes.
            If None, AttributeError will be raised for undefined attributes.

    Examples:
        >>> # Create namespace with list factory
        >>> ns = DefaultNamespace(default_factory=list)
        >>> ns.numbers.append(1)  # Creates new list automatically
        >>> ns.numbers
        [1]

        >>> # Create with initial values
        >>> ns = DefaultNamespace(default_factory=int, x=1, y=2)
        >>> ns.x
        1
        >>> ns.z  # Creates new int (0) automatically
        0
    """

    def __init__(
        self,
        default_factory: Callable[[str], Any] | None = None,
        mapping_or_iterable: Mapping | Iterable[tuple[str, Any]] | None = None,
        /,
        **kwargs: Any,
    ) -> None:
        """Initialize the DefaultNamespace.

        Args:
            default_factory: A callable that takes an attribute name and returns a default value
                when accessing undefined attributes. If None, AttributeError is raised for
                undefined attributes.
            mapping_or_iterable: An optional mapping or iterable of (key, value) pairs to
                initialize the namespace with.
            **kwargs: Additional keyword arguments to initialize the namespace with.
        """
        if mapping_or_iterable is None:
            mapping_or_iterable = {}
        super().__init__(**dict(mapping_or_iterable), **kwargs)
        self._factory = default_factory

    def __getattribute__(self, name: str) -> Any:
        """Get an attribute value, creating it if undefined using the default_factory.

        This method intercepts attribute access to provide default value creation
        for undefined attributes using the default_factory.

        Args:
            name: The name of the attribute to access.

        Returns:
            The attribute value, either existing or newly created.

        Raises:
            AttributeError: If the attribute doesn't exist and no default_factory is set.
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


class Config:
    """A configuration store."""

    _conf_file_name = "config.json"
    _settings: ClassVar[dict[str, Setting]] = {}

    def __init__(self, _help: str = "", **kwargs: Any) -> None:
        """Create a new configuration object instance."""
        self._help = _help

        # Create stores
        self.events = DefaultNamespace(
            lambda name: Event(self._settings[name], self._save)
        )
        self.filters = DefaultNamespace(
            lambda name: Condition(lambda: bool(self._values[name]))
        )
        self.defaults = DefaultNamespace(lambda x: self._settings[x].default)
        self.choices = DefaultNamespace(lambda x: self._settings[x].choices)
        self.menus = DefaultNamespace(lambda x: self._settings[x].menu)

        user_conf_dir = Path(user_config_dir(__app_name__, appauthor=None))
        user_conf_dir.mkdir(exist_ok=True, parents=True)
        self._config_file_path = (user_conf_dir / self._conf_file_name).with_suffix(
            ".json"
        )
        self._valid_user = True
        self._schema_validate = fastjsonschema.compile(self._schema, use_default=False)

        # Register commands for each setting
        for setting in self._settings.values():
            self._register_commands(setting)
            for hook in setting.hooks:
                event = getattr(self.events, setting.name)
                event += hook

        self._values = {
            # Setting defaults
            **{k: v.default for k, v in self._settings.items()},
            # Key-word arguments
            **kwargs,
        }

    def load(self) -> None:
        """Load the configuration options from non-local sources."""
        from euporie.core.log import BufferedLogs, setup_logs

        # Buffer logs and replay them after settings are configured
        with BufferedLogs(logger=log):
            try:
                # Validate configured values
                self._values.update(self._validate(self._load_user(), "config file"))
                self._values.update(
                    self._validate(self._load_user(prefix=self.app), "app config file")
                )
                self._values.update(
                    self._validate(self._load_env(), "environment variable")
                )
                self._values.update(
                    self._validate(
                        self._load_env(prefix=self.app), "app environment variable"
                    )
                )
                self._values.update(
                    self._validate(self._load_args(), "command line parameter")
                )
            finally:
                # Set-up logs even if configuration validation fails
                setup_logs(self)

    def _validate(self, data: dict[str, Any], group: str) -> dict[str, Any]:
        """Validate settings values."""
        validated = {}
        for name, value in data.items():
            if name in self._settings:
                # Convert to json and back to attain json types
                json_data = json.loads(_json_encoder.encode({name: value}))
                try:
                    self._schema_validate(json_data)
                except fastjsonschema.JsonSchemaValueException as error:
                    # Warn about badly configured settings
                    log.warning(
                        "Error in %s setting: `%s = %r`\n%s",
                        group,
                        name,
                        value,
                        error.message.replace("data.", ""),
                    )
                else:
                    # Store validated setting values
                    validated[name] = value
            else:
                # Warn about unknown configuration options
                if not isinstance(value, dict):
                    log.warning(
                        "Configuration option '%s' not recognised in %s", name, group
                    )
        return validated

    def _save(self, setting: Setting) -> None:
        """Save settings to user's configuration file."""
        json_data = self._load_config_file()
        json_data.setdefault(self.app, {})[setting.name] = getattr(self, setting.name)
        if self._valid_user:
            log.debug("Saving setting `%s`", setting)
            with self._config_file_path.open("w") as f:
                json.dump(json_data, f, indent=2, cls=JSONEncoderPlus)

    @property
    def _schema(self) -> dict[str, Any]:
        """Return a JSON schema for the config."""
        return {
            "title": "Euporie Configuration",
            "description": "A configuration for euporie",
            "type": "object",
            "properties": {name: item.schema for name, item in self._settings.items()},
        }

    @property
    def settings(self) -> dict[str, Setting]:
        """Return the currently active settings."""
        return {
            name: setting
            for name, setting in self._settings.items()
            if any(group in sys.modules or group == "*" for group in setting.groups)
        }

    def _load_parser(self) -> argparse.ArgumentParser:
        """Construct an :py:class:`ArgumentParser`."""
        parser = ArgumentParser(
            description=self._help,
            epilog=__copyright__,
            allow_abbrev=True,
            formatter_class=argparse.MetavarTypeHelpFormatter,
            config=self,
            argument_default=argparse.SUPPRESS,
            # exit_on_error=False,
        )
        # Add options to the relevant subparsers
        for setting in self.settings.values():
            # if self._values[setting.name] != setting.default:
            args, kwargs = setting.parser_args
            # Make already specified positional arguments optional
            if (
                not any(x.startswith("-") for x in setting.flags)
                and getattr(self, setting.name) != setting.default
            ):
                kwargs["nargs"] = "?"
            parser.add_argument(*args, **kwargs)
        return parser

    def _load_args(self) -> dict[str, Any]:
        """Attempt to load configuration settings from commandline flags."""
        # Parse known arguments
        namespace, _remainder = self._load_parser().parse_known_intermixed_args()
        # Validate arguments
        return vars(namespace)

    def _load_env(self, prefix: str = "") -> dict[str, Any]:
        """Attempt to load configuration settings from environment variables."""
        result = {}
        for name, setting in self._settings.items():
            if prefix:
                env = f"{__app_name__}_{prefix}_{setting.name}"
            else:
                env = f"{__app_name__}_{setting.name}"
            env = env.upper()
            if env in os.environ:
                value = os.environ.get(env)
                parsed_value: Any = value
                # Attempt to parse the value as a literal
                if value:
                    try:
                        parsed_value = literal_eval(value)
                    except (
                        ValueError,
                        TypeError,
                        SyntaxError,
                        MemoryError,
                        RecursionError,
                    ):
                        pass
                # Attempt to cast the value to the desired type
                if isinstance(value, list):
                    for i, item in enumerate(value[:]):
                        value[i] = setting.type(item)
                else:
                    try:
                        value = setting.type(value)
                    except (ValueError, TypeError):
                        pass
                result[name] = parsed_value
        return result

    def _load_config_file(self) -> dict[str, Any]:
        """Attempt to load JSON configuration file."""
        results = {}
        assert isinstance(self._config_file_path, Path)
        if self._valid_user and self._config_file_path.exists():
            with self._config_file_path.open() as f:
                try:
                    json_data = json.load(f)
                except json.decoder.JSONDecodeError:
                    log.error(
                        "Could not parse the configuration file: %s\nIs it valid json?",
                        self._config_file_path,
                    )
                    self._valid_user = False
                else:
                    results.update(json_data)
        return results

    def _load_user(self, prefix: str | None = None) -> dict[str, Any]:
        """Attempt to load JSON configuration file."""
        results = {}
        # Load config file
        json_data = self._load_config_file()
        # Load section for the current app
        if prefix is not None:
            json_data = json_data.get(prefix, {})
        for name, value in json_data.items():
            if (setting := self._settings.get(name)) is not None:
                # Attempt to cast the value to the desired type
                if isinstance(value, list):
                    for i, item in enumerate(value[:]):
                        try:
                            value[i] = setting.type(item)
                        except (ValueError, TypeError):
                            pass
                else:
                    try:
                        value = setting.type(value)
                    except (ValueError, TypeError):
                        pass
            results[name] = value
        return results

    def _register_commands(self, setting: Setting) -> None:
        """Register commands to set this setting."""
        cmd_name = setting.name.replace("_", "-")
        schema = setting.schema

        if schema.get("type") == "array":
            for choice in setting.choices or schema.get("items", {}).get("enum") or []:
                add_cmd(
                    name=f"toggle-{cmd_name}-{choice}",
                    hidden=setting.hidden,
                    toggled=Condition(
                        partial(lambda x: x in self._values[setting.name], choice)
                    ),
                    title=f"Add {choice} to {setting.title} setting",
                    menu_title=str(choice).replace("_", " ").capitalize(),
                    description=f'Add or remove "{choice}" to or from the list of "{setting.name}"',
                    filter=setting.cmd_filter,
                )(
                    partial(
                        lambda choice: (
                            self._values[setting.name].remove
                            if choice in getattr(self, setting.name)
                            else self._values[setting.name].append
                        )(choice),
                        choice,
                    )
                )

        elif setting.type is bool:
            add_cmd(
                name=f"toggle-{cmd_name}",
                toggled=Condition(lambda: bool(self._values[setting.name])),
                hidden=setting.hidden,
                title=f"Toggle {setting.title}",
                menu_title=setting.kwargs.get("menu_title", setting.title.capitalize()),
                description=setting.help,
                filter=setting.cmd_filter,
            )(partial(self.toggle, setting.name))

        elif setting.type is int or setting.choices is not None:
            add_cmd(
                name=f"switch-{cmd_name}",
                hidden=setting.hidden,
                title=f"Switch {setting.title}",
                menu_title=setting.kwargs.get("menu_title"),
                description=f'Switch the value of the "{setting.name}" configuration option.',
                filter=setting.cmd_filter,
            )(partial(self.toggle, setting.name))

        for choice in setting.choices or schema.get("enum", []) or []:
            add_cmd(
                name=f"set-{cmd_name}-{choice}",
                hidden=setting.hidden,
                toggled=Condition(
                    partial(lambda x: self._values[setting.name] == x, choice)
                ),
                title=f"Set {setting.title} to {choice}",
                menu_title=str(choice).replace("_", " ").capitalize(),
                description=f'Set the value of the "{setting.name}" '
                f'configuration option to "{choice}"',
                filter=setting.cmd_filter,
            )(partial(setattr, self, setting.name, choice))

    def toggle(self, name: str) -> None:
        """Toggle the setting's value."""
        setting = self._settings[name]
        value = self._values[name]

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
            new = setting.choices[
                (setting.choices.index(value) + 1) % len(setting.choices)
            ]
        else:
            raise NotImplementedError
        setattr(self, name, new)

    def __getattribute__(self, name: str) -> Any:
        """Enable access of config elements via dotted attributes."""
        try:
            return super().__getattribute__(name)
        except AttributeError as exc:
            if name in self._values:
                return self._values[name]
            raise exc

    def __setattr__(self, name: str, value: Any) -> None:
        """Set a configuration attribute."""
        if name in self._settings:
            self._values[name] = value
            getattr(self.events, name)()
        else:
            super().__setattr__(name, value)

    @classmethod
    def add_setting(cls, name: str, *args: Any, **kwargs: Any) -> None:
        """Register a new config item."""
        setting = Setting(name, *args, **kwargs)
        Config._settings[name] = setting


add_setting = Config.add_setting
