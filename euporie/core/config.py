"""Define a configuration class for euporie.core."""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import sys
from ast import literal_eval
from collections import ChainMap
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TextIO, cast

import fastjsonschema
from platformdirs import user_config_dir
from prompt_toolkit.filters.base import Condition
from prompt_toolkit.filters.utils import to_filter
from prompt_toolkit.utils import Event
from upath import UPath

from euporie.core import __app_name__, __copyright__, __version__
from euporie.core.commands import add_cmd, get_cmd

if TYPE_CHECKING:
    from typing import IO, Any, Callable, ClassVar, Optional, Sequence

    from prompt_toolkit.filters.base import Filter, FilterOrBool

    from euporie.core.widgets.menu import MenuItem

    class ConfigurableApp(Protocol):
        """An application with configuration."""

        config: Config
        name: str
        log_stdout_level: str


log = logging.getLogger(__name__)

_SCHEMA_TYPES: dict[type | Callable, str] = {
    bool: "boolean",
    str: "string",
    int: "integer",
    float: "float",
    UPath: "string",
}


class ArgumentParser(argparse.ArgumentParser):
    """An argument parser which lexes and formats the help message before printing it."""

    def _print_message(self, message: str, file: IO[str] | None = None) -> None:
        from prompt_toolkit.formatted_text.base import FormattedText
        from prompt_toolkit.lexers.pygments import _token_cache
        from prompt_toolkit.shortcuts.utils import print_formatted_text
        from prompt_toolkit.styles.pygments import style_from_pygments_cls

        from euporie.core.pygments import ArgparseLexer, EuporiePygmentsStyle

        if message:
            file = cast("Optional[TextIO]", file)
            print_formatted_text(
                FormattedText(
                    [
                        (_token_cache[t], v)
                        for _, t, v in ArgparseLexer().get_tokens_unprocessed(message)
                    ]
                ),
                file=file,
                style=style_from_pygments_cls(EuporiePygmentsStyle),
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
        if isinstance(o, (Path, UPath)):
            return str(o)
        return json.JSONEncoder.default(self, o)


_json_encoder = JSONEncoderPlus()


class Setting:
    """A single configuration item."""

    def __init__(
        self,
        name: str,
        default: Any,
        help_: str,
        description: str,
        type_: Callable[[Any], Any] | None = None,
        title: str | None = None,
        choices: list[Any] | None = None,
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
        self.default = default
        self._value = default
        self.title = title or self.name.replace("_", " ")
        self.help = help_
        self.description = description
        self.choices = choices
        self.type = type_ or type(default)
        self.action = action or TYPE_ACTIONS.get(self.type)
        self.flags = flags or [f"--{name.replace('_','-')}"]
        self._schema: dict[str, Any] = {
            "type": _SCHEMA_TYPES.get(self.type),
            **(schema or {}),
        }
        self.nargs = nargs
        self.hidden = to_filter(hidden)
        self.kwargs = kwargs
        self.cmd_filter = cmd_filter

        self.event = Event(self)
        for hook in hooks or []:
            self.event += hook

        self.register_commands()

    def register_commands(self) -> None:
        """Register commands to set this setting."""
        name = self.name.replace("_", "-")
        if self.type in (bool, int) or self.choices is not None:
            toggled_filter = None
            if self.type == bool:

                def _toggled() -> bool:
                    from euporie.core.current import get_app

                    app = get_app()
                    value = app.config.get(self.name)
                    return bool(getattr(app.config, self.name, not value))

                toggled_filter = Condition(_toggled)

            add_cmd(
                name=f"toggle-{name}",
                toggled=toggled_filter,
                hidden=self.hidden,
                title=f"Toggle {self.title}",
                menu_title=self.kwargs.get("menu_title"),
                description=f'Toggle the value of the "{self.name}" configuration option.',
                filter=self.cmd_filter,
            )(self.toggle)

        for choice in (self.choices or self.schema.get("enum", [])) or []:
            add_cmd(
                name=f"set-{name}-{choice}",
                hidden=self.hidden,
                toggled=Condition(partial(lambda x: self.value == x, choice)),
                title=f"Set {self.title} to {choice}",
                menu_title=str(choice).replace("_", " ").capitalize(),
                description=f'Set the value of the "{self.name}" '
                f'configuration option to "{choice}"',
                filter=self.cmd_filter,
            )(partial(setattr, self, "value", choice))

    def toggle(self) -> None:
        """Toggle the setting's value."""
        if self.type == bool:
            new = not self.value
        elif (
            self.type == int
            and "minimum" in (schema := self.schema)
            and "maximum" in schema
        ):
            new = schema["minimum"] + (self.value - schema["minimum"] + 1) % (
                schema["maximum"] + 1
            )
        elif self.choices is not None:
            new = self.choices[(self.choices.index(self.value) + 1) % len(self.choices)]
        else:
            raise NotImplementedError
        self.value = new

    @property
    def value(self) -> Any:
        """Return the current value."""
        return self._value

    @value.setter
    def value(self, new: Any) -> None:
        """Set the current value."""
        self._value = new
        self.event.fire()

    @property
    def schema(self) -> dict[str, Any]:
        """Return a json schema property for the config item."""
        return {
            "description": self.help,
            **({"enum": self.choices} if self.choices is not None else {}),
            **({"default": self.default} if self.default is not None else {}),
            **self._schema,
        }

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
            )
        elif self.type in (bool, int):
            return get_cmd(f"toggle-{self.name.replace('_', '-')}").menu
        else:
            raise NotImplementedError

    @property
    def parser_args(self) -> tuple[list[str], dict[str, Any]]:
        """Return arguments for construction of an :class:`argparse.ArgumentParser`."""
        # Do not set defaults for command line arguments, as default values
        # would override values set in the configuration file
        args = self.flags or [self.name]

        kwargs: dict[str, Any] = {
            "action": self.action,
            "help": self.help,
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
        return f"<Setting {self.name}={self.value.__repr__()}>"


class Config:
    """A configuration store."""

    settings: ClassVar[dict[str, Setting]] = {}
    conf_file_name = "config.json"

    def __init__(self) -> None:
        """Create a new configuration object instance."""
        self.app_name: str = "base"
        self.app_cls: type[ConfigurableApp] | None = None

    def _save(self, setting: Setting) -> None:
        """Save settings to user's configuration file."""
        json_data = self.load_config_file()
        json_data.setdefault(self.app_name, {})[setting.name] = setting.value
        if self.valid_user:
            log.debug("Saving setting `%s`", setting)
            with self.config_file_path.open("w") as f:
                json.dump(json_data, f, indent=2)

    def load(self, cls: type[ConfigurableApp]) -> None:
        """Load the command line, environment, and user configuration."""
        from euporie.core.log import setup_logs

        self.app_cls = cls
        self.app_name = cls.name
        log.debug("Loading config for %s", self.app_name)

        user_conf_dir = Path(user_config_dir(__app_name__, appauthor=None))
        user_conf_dir.mkdir(exist_ok=True, parents=True)
        self.config_file_path = (user_conf_dir / self.conf_file_name).with_suffix(
            ".json"
        )
        self.valid_user = True

        config_maps = {
            # Load command line arguments
            "command line arguments": self.load_args(),
            # Load app specific env vars
            "app-specific environment variable": self.load_env(app_name=self.app_name),
            # Load global env vars
            "global environment variable": self.load_env(),
            # Load app specific user config
            "app-specific user configuration": self.load_user(app_name=self.app_name),
            # Load global user config
            "user configuration": self.load_user(),
        }
        set_values = ChainMap(*config_maps.values())

        for name, setting in Config.settings.items():
            if setting.name in set_values:
                # Set value without triggering hooks
                setting._value = set_values[name]
            setting.event += self._save

        # Set-up logs
        setup_logs(self)

        # Save a list of unknown configuration options so we can warn about them once
        # the logs are configured
        self.unrecognised = [
            (map_name, option_name)
            for map_name, map_values in config_maps.items()
            for option_name in map_values.keys() - Config.settings.keys()
            if not isinstance(set_values[option_name], dict)
        ]

    def warn(self) -> None:
        """Warn about unrecognised configuration items."""
        for map_name, option_name in self.unrecognised:
            log.warning(
                "Configuration option '%s' not recognised in %s", option_name, map_name
            )

    @property
    def schema(self) -> dict[str, Any]:
        """Return a JSON schema for the config."""
        return {
            "title": "Euporie Configuration",
            "description": "A configuration for euporie",
            "type": "object",
            "properties": {name: item.schema for name, item in self.settings.items()},
        }

    def load_parser(self) -> argparse.ArgumentParser:
        """Construct an :py:class:`ArgumentParser`."""
        parser = ArgumentParser(
            description=self.app_cls.__doc__,
            epilog=__copyright__,
            allow_abbrev=True,
            formatter_class=argparse.MetavarTypeHelpFormatter,
        )
        # Add options to the relevant subparsers
        for setting in self.settings.values():
            args, kwargs = setting.parser_args
            parser.add_argument(*args, **kwargs)
        return parser

    def load_args(self) -> dict[str, Any]:
        """Attempt to load configuration settings from commandline flags."""
        result = {}
        # Parse known arguments
        namespace, remainder = self.load_parser().parse_known_intermixed_args()
        # Update argv to leave the remaining arguments for subsequent apps
        sys.argv[1:] = remainder
        # Validate arguments
        for name, value in vars(namespace).items():
            if value is not None:
                # Convert to json and back to attain json types
                json_data = json.loads(_json_encoder.encode({name: value}))
                try:
                    fastjsonschema.validate(self.schema, json_data)
                except fastjsonschema.JsonSchemaValueException as error:
                    log.warning("Error in command line parameter `%s`: %s", name, error)
                else:
                    result[name] = value
        return result

    def load_env(self, app_name: str = "") -> dict[str, Any]:
        """Attempt to load configuration settings from environment variables."""
        result = {}
        for name, setting in self.settings.items():
            if app_name:
                env = f"{__app_name__.upper()}_{self.app_name.upper()}_{setting.name.upper()}"
            else:
                env = f"{__app_name__.upper()}_{setting.name.upper()}"
            if env in os.environ:
                value = os.environ.get(env)
                parsed_value: Any = value
                # Attempt to parse the value as a literal
                if value:
                    with contextlib.suppress(
                        ValueError, TypeError, SyntaxError, MemoryError, RecursionError
                    ):
                        parsed_value = literal_eval(value)
                # Attempt to cast the value to the desired type
                try:
                    parsed_value = setting.type(value)
                except (ValueError, TypeError):
                    log.warning(
                        "Environment variable `%s` not understood" " - `%s` expected",
                        env,
                        setting.type.__name__,
                    )
                else:
                    json_data = json.loads(_json_encoder.encode({name: parsed_value}))
                    try:
                        fastjsonschema.validate(self.schema, json_data)
                    except fastjsonschema.JsonSchemaValueException as error:
                        log.error("Error in environment variable: `%s`\n%s", env, error)
                    else:
                        result[name] = parsed_value
        return result

    def load_config_file(self) -> dict[str, Any]:
        """Attempt to load JSON configuration file."""
        results = {}
        assert isinstance(self.config_file_path, Path)
        if self.valid_user and self.config_file_path.exists():
            with self.config_file_path.open() as f:
                try:
                    json_data = json.load(f)
                except json.decoder.JSONDecodeError:
                    log.error(
                        "Could not parse the configuration file: %s\nIs it valid json?",
                        self.config_file_path,
                    )
                    self.valid_user = False
                else:
                    results.update(json_data)
        return results

    def load_user(self, app_name: str = "") -> dict[str, Any]:
        """Attempt to load JSON configuration file."""
        results = {}
        # Load config file
        json_data = self.load_config_file()
        # Load section for the current app
        if app_name:
            json_data = json_data.get(self.app_name, {})
        # Validate the configuration file
        try:
            # Validate a copy so the original data is not modified
            fastjsonschema.validate(self.schema, dict(json_data))
        except fastjsonschema.JsonSchemaValueException as error:
            log.warning("Error in config file: `%s`: %s", self.config_file_pathi, error)
            self.valid_user = False
        else:
            results.update(json_data)
        return results

    def get(self, name: str, default: Any = None) -> Any:
        """Access a configuration value, falling back to the default value if unset.

        Args:
            name: The name of the attribute to access.
            default: The value to return if the name is not found

        Returns:
            The configuration variable value.

        """
        if name in self.settings:
            return self.settings[name].value
        else:
            return default

    def get_item(self, name: str) -> Any:
        """Access a configuration item.

        Args:
            name: The name of the attribute to access.

        Returns:
            The configuration item.

        """
        return self.settings.get(name)

    def filter(self, name: str) -> Filter:
        """Return a :py:class:`Filter` for a configuration item."""
        return Condition(partial(self.get, name))

    def __getattr__(self, name: str) -> Any:
        """Enable access of config elements via dotted attributes.

        Args:
            name: The name of the attribute to access.

        Returns:
            The configuration variable value.

        """
        return self.get(name)

    def __setitem__(self, name: str, value: Any) -> None:
        """Set a configuration attribute.

        Args:
            name: The name of the attribute to set.
            value: The value to give the attribute.

        """
        setting = self.settings[name]
        setting.value = value


def add_setting(
    name: str,
    default: Any,
    help_: str,
    description: str,
    type_: Callable[[Any], Any] | None = None,
    action: argparse.Action | str | None = None,
    flags: list[str] | None = None,
    schema: dict[str, Any] | None = None,
    nargs: str | int | None = None,
    hidden: FilterOrBool = False,
    hooks: list[Callable[[Setting], None]] | None = None,
    cmd_filter: FilterOrBool = True,
    **kwargs: Any,
) -> None:
    """Register a new config item."""
    Config.settings[name] = Setting(
        name=name,
        default=default,
        help_=help_,
        description=description,
        type_=type_,
        action=action,
        flags=flags,
        schema=schema,
        nargs=nargs,
        hidden=hidden,
        hooks=hooks,
        cmd_filter=cmd_filter,
        **kwargs,
    )


# ################################### Settings ####################################

add_setting(
    name="version",
    default=False,
    flags=["--version", "-V"],
    action="version",
    hidden=True,
    version=f"%(prog)s {__version__}",
    help_="Show the version number and exit",
    description="""
        If set, euporie will print the current version number of the application and exit.
        All other configuration options will be ignored.

        .. note::

           This cannot be set in the configuration file or via an environment variable
    """,
)
