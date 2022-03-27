"""Defines a configuration class for euporie."""

from __future__ import annotations

import argparse
import json
import logging
import os
from ast import literal_eval
from collections import ChainMap
from pathlib import Path
from typing import TYPE_CHECKING

import jsonschema  # type: ignore
from appdirs import user_config_dir  # type: ignore
from pygments.styles import get_all_styles  # type: ignore

from euporie import __app_name__, __copyright__, __strapline__, __version__

if TYPE_CHECKING:
    from typing import Any, Iterator, Optional, Sequence, Union

__all__ = ["JSONEncoderPlus", "BooleanOptionalAction", "Config", "config"]

log = logging.getLogger(__name__)


class JSONEncoderPlus(json.JSONEncoder):
    """JSON encode class which encodes paths as strings."""

    def default(self, o: "Any") -> "Union[bool, int, float, str, None]":
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


class BooleanOptionalAction(argparse.Action):
    """Action for boolean flags.

    Included because `argparse.BooleanOptionalAction` is not present in `python<=3.9`.
    """

    def __init__(self, option_strings: "list[str]", *args: "Any", **kwargs: "Any"):
        """Initiate the Action, as per `argparse.BooleanOptionalAction`."""
        _option_strings = list(option_strings)
        for option_string in option_strings:
            if option_string.startswith("--"):
                _option_strings.append(f"--no-{option_string[2:]}")
        kwargs["nargs"] = 0
        super().__init__(_option_strings, *args, **kwargs)

    def format_usage(self) -> "str":
        """Formats the action string.

        Returns:
            The formatted string.

        """
        return " | ".join(self.option_strings)

    def __call__(
        self,
        parser: "argparse.ArgumentParser",
        namespace: "argparse.Namespace",
        values: "Union[str, Sequence[Any], None]",
        option_string: "Optional[str]" = None,
    ) -> "None":
        """Set the value to True or False depending on the flag provided."""
        if option_string in self.option_strings:
            assert isinstance(option_string, str)
            setattr(namespace, self.dest, not option_string.startswith("--no-"))


CONFIG_PARAMS: "dict[str, dict]" = {
    "version": {
        "flags_": ["--version", "-V"],
        "action": "version",
        "version": f"%(prog)s {__version__}",
        "help": "Show the version number and exit",
        "description_": """
            If set, euporie will print the current version number of the application and exit.
            All other configuration options will be ignored.

            .. note::
               This cannot be set in the configuration file or via an environment variable
        """,
    },
    "log_file": {
        "flags_": ["--log-file"],
        "nargs": "?",
        "default": "",
        "type": str,
        "help": "File path for logs",
        "schema_": {
            "type": "string",
            "default": "",
        },
        "description_": """
            When set to a file path, the log output will be written to the given path.
            If no value is given output will be sent to the standard output.
        """,
    },
    "debug": {
        "flags_": ["--debug"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Include debug output in logs",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            When set, logging events at the debug level are emitted.
        """,
    },
    "dump": {
        "flags_": ["--dump"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Output formatted file to display or file",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            When set, the formatted output will be written to the the output file path
            given by `dump_file` (standard output by default).
        """,
    },
    "dump_file": {
        "flags_": ["--dump-file"],
        "nargs": "?",
        "const": "-",
        "type": Path,
        "help": "Output path when dumping file",
        "schema_": {
            "type": "string",
            "default": None,
        },
        "description_": """
            When set to a file path, the formatted output will be written to the
            given path. If no value is given (or the default "-" is passed) output
            will be printed to standard output.
        """,
    },
    "page": {
        "flags_": ["--page"],
        "type": bool,
        "action": BooleanOptionalAction,
        "help": "Pass output to pager",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            Whether to pipe output to the system pager when using ``--dump``.
        """,
    },
    "run": {
        "flags_": ["--run"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Run the notebook when loaded",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
        If set, notebooks will be run automatically when opened, or if dumping
        output, notebooks will be run before being output.
    """,
    },
    "tmux_graphics": {
        "flags_": ["--tmux-graphics"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Enable terminal graphics in tmux (experimental)",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
        If set, terminal graphics will be used if :program:`tmux` is running by
        performing terminal escape sequence pass-through. You must restart euporie for
        this to take effect.

        .. warning::

           Terminal graphics in :program:`tmux` is experimental, and is not guaranteed
           to work. Use at your own risk!
    """,
    },
    "terminal_polling_interval": {
        "flags_": ["--terminal-polling-interval"],
        "type": int,
        "help": "Time between terminal colour queries",
        "schema_": {
            "type": "integer",
            "default": 0,
            "min": 0,
        },
        "description_": """
        Determine how frequently the terminal should be polled for changes to the
        background / foreground colours. Set to zero to disable terminal polling.

    """,
    },
    "edit_mode": {
        "flags_": ["--edit-mode"],
        "type": str,
        "choices": ["micro", "emacs", "vi"],
        "help": "Key-binding mode for text editing",
        "schema_": {
            "type": "string",
            "default": "micro",
        },
        "description_": """
            Key binding mode to use when editing cells.
        """,
    },
    "tab_size": {
        "flags_": ["--tab-size"],
        "type": int,
        "help": "Spaces per indentation level",
        "schema_": {
            "type": "integer",
            "minimum": 1,
            "default": 4,
        },
        "description_": """
            The number of spaces to use per indentation level. Should be set to 4.
        """,
    },
    "run_after_external_edit": {
        "flags_": ["--run-after-external-edit"],
        "type": bool,
        "help": "Run cells after editing externally",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            Whether to execute a cell immediately after editing in `$EDITOR`.
        """,
    },
    "format_black": {
        "flags_": ["--format-black"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Use black when re-formatting code cells",
        "schema_": {
            "type": "boolean",
            "default": True,
        },
        "description_": """
            Whether to use :py:mod:`black` when reformatting code cells.
        """,
    },
    "format_isort": {
        "flags_": ["--format-isort"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Use isort when re-formatting code cells",
        "schema_": {
            "type": "boolean",
            "default": True,
        },
        "description_": """
            Whether to use :py:mod:`isort` when reformatting code cells.
        """,
    },
    "format_ssort": {
        "flags_": ["--format-ssort"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Use ssort when re-formatting code cells",
        "schema_": {
            "type": "boolean",
            "default": True,
        },
        "description_": """
            Whether to use :py:mod:`ssort` when reformatting code cells.
        """,
    },
    "autoformat": {
        "flags_": ["--autoformat"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Automatically re-format code cells when run",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            Whether to automatically reformat code cells before they are run.
        """,
    },
    "autocomplete": {
        "flags_": ["--autocomplete"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Provide completions suggestions automatically",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            Whether to automatically suggestion completions while typing in code cells.
        """,
    },
    "autosuggest": {
        "flags_": ["--autosuggest"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Provide line completion suggestions",
        "schema_": {
            "type": "boolean",
            "default": True,
        },
        "description_": """
            Whether to automatically suggestion line content while typing in code cells.
        """,
    },
    "autoinspect": {
        "flags_": ["--autoinspect"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Display contextual help automatically",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            Whether to automatically display contextual help when navigating through code cells.
        """,
    },
    "expand": {
        "flags_": ["--expand"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Use the full width to display notebooks",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            Whether the notebook page should expand to fill the available width
        """,
    },
    "max_notebook_width": {
        "flags_": ["--max-notebook-width"],
        "type": int,
        "help": "Maximum width of notebooks",
        "schema_": {
            "type": "integer",
            "minimum": 1,
            "default": 120,
        },
        "description_": """
            The maximum width at which to display a notebook.
        """,
    },
    "show_status_bar": {
        "flags_": ["--show-status-bar"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Show the status bar",
        "schema_": {
            "type": "boolean",
            "default": True,
        },
        "description_": """
            Whether the status bar should be shown at the bottom of the screen.
        """,
    },
    "color_scheme": {
        "flags_": ["--color-scheme"],
        "type": str,
        "choices": ["default", "inverse", "light", "dark"],
        "help": "The color scheme to use",
        "schema_": {
            "type": "string",
            "default": "default",
        },
        "description_": """
            The color scheme to use: `auto` means euporie will try to use your
            terminal's color scheme, `light` means black text on a white background,
            and `dark` means white text on a black background.
        """,
    },
    "background_pattern": {
        "flags_": ["--background-pattern", "--bg-pattern"],
        "type": int,
        "choices": range(6),
        "help": "The background pattern to use",
        "schema_": {
            "type": "integer",
            "minimum": 0,
            "maximum": 5,
            "default": 2,
        },
        "description_": """
            The background pattern to use when the notebook is narrower than the
            available width. Zero mean no pattern is used.
        """,
    },
    "background_character": {
        "flags_": ["--background-character", "--bg-char"],
        "type": str,
        "help": "Character for background pattern",
        # "choices": ,
        "schema_": {
            "type": "string",
            "maxLength": 1,
            "default": "·",
        },
        "description_": """
            The character to use when drawing the background pattern.

            Recommended characters include: "·", "⬤", "╳", "╱", "╲", "░", "▒", "▓", "▞", "╬"
        """,
    },
    "background_color": {
        "flags_": ["--background-color", "--bg-color"],
        "type": str,
        "help": "Color for background pattern",
        "schema_": {
            "type": "string",
            "maxLength": 7,
            "default": "",
        },
        "description_": """
            The color to use for the background pattern.
        """,
    },
    "show_cell_borders": {
        "flags_": ["--show-cell-borders"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Show or hide cell borders.",
        "schema_": {
            "type": "boolean",
            "default": False,
        },
        "description_": """
            Whether cell borders should be drawn for unselected cells.
        """,
    },
    "line_numbers": {
        "flags_": ["--line-numbers"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Show or hide line numbers",
        "schema_": {
            "type": "boolean",
            "default": True,
        },
        "description_": """
            Whether line numbers are shown by default.
        """,
    },
    "syntax_theme": {
        "flags_": ["--syntax-theme"],
        "type": str,
        # Do not want to print all theme names in --help screen as it looks messy
        # "choices": list(get_all_styles()),
        "help": "Syntax highlighting theme",
        "schema_": {
            "type": "string",
            "pattern": f"({'|'.join(get_all_styles())})",
            "default": "default",
        },
        "description_": """
            The name of the pygments style to use for syntax highlighting.
        """,
    },
    "files": {
        "flags_": ["files"],
        "nargs": "*",
        "type": Path,
        "help": "List of file names to open",
        "schema_": {
            "type": "array",
            "items": {
                "file": {
                    "description": "File path",
                    "type": "string",
                },
            },
            "default": [],
        },
        "description_": """
            A list of file paths to open when euporie is launched.
        """,
    },
}

CONFIG_SCHEMA: "dict" = {
    "title": "Euporie Configuration",
    "description": "A configuration for euporie",
    "type": "object",
    "properties": {
        name: {
            "description": param.get("help"),
            **(
                {"pattern": f"({'|'.join(choices)})"}
                if (choices := param.get("choices")) and param.get("type") == str
                else {}
            ),
            **({"default": default} if (default := param.get("default")) else {}),
            **param["schema_"],
        }
        for name, param in CONFIG_PARAMS.items()
        if param.get("schema_")
    },
}


class Config:
    """A configuration object with configuration values available as attributes.

    Default configuration variables are loaded from the defaults defined in the
    schema, then overwritten with values defined in a configuration file.
    """

    valid_user: "bool"

    conf_file_name = "config.json"
    defaults = {
        name: param.get("schema_", {}).get("default")
        for name, param in CONFIG_PARAMS.items()
    }

    def __init__(self):
        """Ininitate the Configuration object."""
        self.user = {}
        self.env = {}
        self.args = {}

        user_conf_dir = Path(user_config_dir(__app_name__, appauthor=False))
        user_conf_dir.mkdir(exist_ok=True, parents=True)
        self.config_file_path = user_conf_dir / self.conf_file_name
        self.valid_user = True

        self.chain = ChainMap(
            self.args,
            self.env,
            self.user,
            self.defaults,
        )

    def load(self) -> "Config":
        """Loads the command line, environment, and user configuration."""
        self.load_user()
        self.load_env()
        self.load_args()
        return self

    def load_parser(self) -> "argparse.ArgumentParser":
        """Constructs an :py:class:`argparse.ArgumentParser`."""
        parser = argparse.ArgumentParser(
            description=__strapline__,
            epilog=__copyright__,
            allow_abbrev=True,
            formatter_class=argparse.MetavarTypeHelpFormatter,
        )
        for name, data in CONFIG_PARAMS.items():
            parser.add_argument(
                *data.get("flags_") or [name],
                # Do not set defaults for command line arguments, as default values
                # would override values set in the configuration file
                **{
                    key: value
                    for key, value in data.items()
                    if not key.endswith("_") and key != "default"
                },
            )
        return parser

    def load_args(self) -> "None":
        """Attempts to load configuration settings from commandline flags."""
        for name, value in vars(self.load_parser().parse_args()).items():
            if value is not None:
                # Convert to json and back to attain json types
                json_data = json.loads(_json_encoder.encode({name: value}))
                try:
                    jsonschema.validate(instance=json_data, schema=CONFIG_SCHEMA)
                except jsonschema.ValidationError as error:
                    log.warning(f"Error in command line parameter `{name}`: {error}")
                else:
                    self.args[name] = value

    def load_env(self) -> "None":
        """Attempt to load configuration settings from environment variables."""
        for name, param in CONFIG_PARAMS.items():
            env = f"{__app_name__.upper()}_{name.upper()}"
            if env in os.environ:
                type_ = param.get("type", str)
                value = os.environ.get(env)
                # Attempt to parse the value as a literal
                if value:
                    try:
                        value = literal_eval(value)
                    except (
                        ValueError,
                        TypeError,
                        SyntaxError,
                        MemoryError,
                        RecursionError,
                    ):
                        pass
                # Attempt to cast the value to the desired type
                try:
                    value = type_(value)
                except (ValueError, TypeError):
                    log.warning(
                        f"Environment variable `{env}` not understood"
                        f" - `{type_.__name__}` expected"
                    )
                else:
                    json_data = json.loads(_json_encoder.encode({name: value}))
                    try:
                        jsonschema.validate(instance=json_data, schema=CONFIG_SCHEMA)
                    except jsonschema.ValidationError as error:
                        log.error(f"Error in environment variable: `{env}`\n{error}")
                    else:
                        self.env[name] = value

    def load_user(self) -> "None":
        """Attempt to load JSON configuration file."""
        assert isinstance(self.config_file_path, Path)
        if self.valid_user and self.config_file_path.exists():
            with open(self.config_file_path, "r") as f:
                try:
                    json_data = json.load(f)
                except json.decoder.JSONDecodeError:
                    log.error(
                        "Could not parse the configuration file: "
                        f"{self.config_file_path}\n"
                        "Is it valid json?"
                    )
                    self.valid_user = False
                else:
                    try:
                        jsonschema.validate(instance=json_data, schema=CONFIG_SCHEMA)
                    except jsonschema.ValidationError as error:
                        log.warning(
                            f"Error in config file: {self.config_file_path}\n"
                            f"{error}"
                        )
                        self.valid_user = False
                    else:
                        self.user.update(json_data)
                        return
            log.warning("The configuration file was not loaded")

    def get(self, name: "str") -> "Any":
        """Access a configuration variable, falling back to the default value if unset.

        Args:
            name: The name of the attribute to access.

        Returns:
            The configuration variable value.

        """
        return self.chain.get(name)

    def choices(self, name: "str") -> "list":
        """Returns a list of valid choices for a configuration item.

        Args:
            name: The name of the attribute to query.

        Returns:
            A list of valid choices

        """
        return CONFIG_PARAMS.get(name, {}).get("choices", [])

    def toggle(self, name: "str") -> "None":
        """Switches attributes between permitted configuration states.

        For boolean values, they are toggled between True and False. Integer values are
        incremented and reset within the permitted range.

        Args:
            name: The name of the attribute to toggle.

        """
        if name in self.defaults:
            current = getattr(self, name)
            schema = CONFIG_SCHEMA["properties"][name]
            if schema["type"] == "boolean":
                setattr(self, name, not current)
            elif schema["type"] == "integer":
                setattr(
                    self,
                    name,
                    schema["minimum"]
                    + (current - schema["minimum"] + 1) % (schema["maximum"] + 1),
                )

    def __getattr__(self, name: "str") -> "Any":
        """Enables access of config elements via dotted attributes.

        Args:
            name: The name of the attribute to access.

        Returns:
            The configuration variable value.

        """
        return self.get(name)

    def __setitem__(self, name: "str", value: "Any") -> "None":
        """Set a configuration attribute.

        Args:
            name: The name of the attribute to set.
            value: The value to give the attribute.

        """
        if name in self.args:
            del self.args[name]
        self.user[name] = value
        if self.valid_user:
            with open(self.config_file_path, "w") as f:
                json.dump(self.user, f, indent=2)

    def __setattr__(self, attr: "str", value: "Union[bool, int, str]") -> "None":
        """Sets configuration attributes and writes their values to the config file."""
        if attr in self.defaults:
            self.__setitem__(attr, value)
        else:
            return super().__setattr__(attr, value)

    def __delitem__(self, name: "str") -> "None":
        """Unset a user's configuration variable.

        This removes a configuration setting from the user's configuration, so the
        default value will be used.

        Args:
            name: The name of the attribute to unset.

        Raises:
            KeyError: When the configuration does not exist in the configuration
                schema.

        """
        try:
            del self.user[name]
        except KeyError as exc:
            raise KeyError(f"Variable not found in the user config: {name!r}") from exc
        else:
            if self.valid_user:
                with open(self.config_file_path, "w") as f:
                    json.dump(self.user, f, indent=2)

    def __iter__(self) -> "Iterator[str]":
        """Iterate over all configuration variable names.

        Returns:
            An iterable of the combined dictionary.

        """
        return iter(self.chain)

    def __len__(self) -> "int":
        """Return the length of the combined user and default settings.

        Returns:
            The length of the combined dictionary.

        """
        return len(self.chain)

    def __str__(self) -> "str":
        """Represent the configuration as a string.

        Returns:
            A string representing the configuration.

        """
        return f"Config({self.chain!r})"

    __repr__ = __str__


config = Config()
