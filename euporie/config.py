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
from pygments.styles import STYLE_MAP as pygments_styles  # type: ignore

from euporie import __app_name__, __copyright__, __strapline__, __version__
from euporie.enums import TabMode

if TYPE_CHECKING:
    from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union

__all__ = ["JSONEncoderPlus", "BooleanOptionalAction", "Config", "config"]

log = logging.getLogger(__name__)


APPS: "List[Dict]" = [
    {
        "name": "edit",
        "help": "Interactively edit a notebook file",
        "class": "euporie.app.edit.EditApp",
        "default": True,
        "description": """
            Launches the interactive TUI notebook editor, allowing you to run and edit
            Jupyter notebooks in the terminal.
        """,
    },
    {
        "name": "preview",
        "help": "Preview a notebook",
        "class": "euporie.app.preview.PreviewApp",
        "description": """
            Outputs a formatted notebook file. The formatted output will be written to
            the the output file path given by `output_file` (the standard output by
            default).
        """,
    },
    {
        "name": "hub",
        "help": "Launch euporie hub",
        "class": "euporie.app.hub.HubApp",
        "description": """
            Launches euporie hub, a multi-client SSH server running euporie, which
            launches an instance of the TUI editor for each connected user.
        """,
    },
]


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


CONFIG_PARAMS: "Dict[str, Dict]" = {
    # Global options
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
    "app": {
        "default": "euporie.app.edit.EditApp",
        "type": str,
        "choices": [app["class"] for app in APPS],
        "help": "The euporie app to launch",
        "schema_": {
            "type": "string",
        },
        "description_": """
            The dotted import path of the :class:`EuporieApp` to run.
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
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            When set, logging events at the debug level are emitted.
        """,
    },
    # Edit options
    "edit_mode": {
        "apps_": ["edit"],
        "flags_": ["--edit-mode"],
        "type": str,
        "choices": ["micro", "emacs", "vi"],
        "help": "Key-binding mode for text editing",
        "default": "micro",
        "schema_": {
            "type": "string",
        },
        "description_": """
            Key binding mode to use when editing cells.
        """,
    },
    "tab_size": {
        "apps_": ["edit"],
        "flags_": ["--tab-size"],
        "type": int,
        "help": "Spaces per indentation level",
        "default": 4,
        "schema_": {
            "type": "integer",
            "minimum": 1,
        },
        "description_": """
            The number of spaces to use per indentation level. Should be set to 4.
        """,
    },
    "show_cell_borders": {
        "apps_": ["edit"],
        "flags_": ["--show-cell-borders"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Show or hide cell borders.",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            Whether cell borders should be drawn for unselected cells.
        """,
    },
    "line_numbers": {
        "apps_": ["edit"],
        "flags_": ["--line-numbers"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Show or hide line numbers",
        "default": True,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            Whether line numbers are shown by default.
        """,
    },
    "show_status_bar": {
        "apps_": ["edit"],
        "flags_": ["--show-status-bar"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Show the status bar",
        "default": True,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            Whether the status bar should be shown at the bottom of the screen.
        """,
    },
    "show_scroll_bar": {
        "apps_": ["edit"],
        "flags_": ["--show-scroll-bar"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Show the scroll bar",
        "default": True,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            Whether the scroll bar should be shown on the right of the screen.
        """,
    },
    "tab_mode": {
        "apps_": ["edit"],
        "flags_": ["--tab-mode"],
        "type": str,
        "choices": [mode.value for mode in TabMode],
        "default": "stack",
        "help": "The method used to display multiple tabs",
        "schema_": {"type": "string"},
        "description_": """
            Determines how multiple tabs are displayed when more than one tab is open.
            * ``stack`` displays one tab at a time with a tab-bar
            * ``tile_horizontally`` displays tabs side-by-side
            * ``tile_vertically`` displays tabs one-atop-the-next
        """,
    },
    "always_show_tab_bar": {
        "apps_": ["edit"],
        "flags_": ["--always-show-tab-bar"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Always show the tab bar",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            When set, the tab bar will always be shown - otherwise the tab bar is only
            shown when multiple tabs are open.
        """,
    },
    "background_pattern": {
        "apps_": ["edit"],
        "flags_": ["--background-pattern", "--bg-pattern"],
        "type": int,
        "choices": list(range(6)),
        "help": "The background pattern to use",
        "default": 2,
        "schema_": {
            "type": "integer",
            "minimum": 0,
            "maximum": 5,
        },
        "description_": """
            The background pattern to use when the notebook is narrower than the
            available width. Zero mean no pattern is used.
        """,
    },
    "background_character": {
        "apps_": ["edit"],
        "flags_": ["--background-character", "--bg-char"],
        "type": str,
        "help": "Character for background pattern",
        "default": "·",
        "schema_": {
            "type": "string",
            "maxLength": 1,
        },
        "description_": """
            The character to use when drawing the background pattern.

            Recommended characters include: "·", "⬤", "╳", "╱", "╲", "░", "▒", "▓", "▞", "╬"
        """,
    },
    "terminal_polling_interval": {
        "apps_": ["edit"],
        "flags_": ["--terminal-polling-interval"],
        "type": int,
        "help": "Time between terminal colour queries",
        "default": 0,
        "schema_": {
            "type": "integer",
            "min": 0,
        },
        "description_": """
            Determine how frequently the terminal should be polled for changes to the
            background / foreground colours. Set to zero to disable terminal polling.
        """,
    },
    "autocomplete": {
        "apps_": ["edit"],
        "flags_": ["--autocomplete"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Provide completions suggestions automatically",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            Whether to automatically suggestion completions while typing in code cells.
        """,
    },
    "autosuggest": {
        "apps_": ["edit"],
        "flags_": ["--autosuggest"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Provide line completion suggestions",
        "default": True,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            Whether to automatically suggestion line content while typing in code cells.
        """,
    },
    "autoinspect": {
        "apps_": ["edit"],
        "flags_": ["--autoinspect"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Display contextual help automatically",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            Whether to automatically display contextual help when navigating through code cells.
        """,
    },
    "run_after_external_edit": {
        "apps_": ["edit"],
        "flags_": ["--run-after-external-edit"],
        "type": bool,
        "help": "Run cells after editing externally",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            Whether to execute a cell immediately after editing in `$EDITOR`.
        """,
    },
    "autoformat": {
        "apps_": ["edit"],
        "flags_": ["--autoformat"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Automatically re-format code cells when run",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            Whether to automatically reformat code cells before they are run.
        """,
    },
    "format_black": {
        "apps_": ["edit"],
        "flags_": ["--format-black"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Use black when re-formatting code cells",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            Whether to use :py:mod:`black` when reformatting code cells.
        """,
    },
    "format_isort": {
        "apps_": ["edit"],
        "flags_": ["--format-isort"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Use isort when re-formatting code cells",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            Whether to use :py:mod:`isort` when reformatting code cells.
        """,
    },
    "format_ssort": {
        "apps_": ["edit"],
        "flags_": ["--format-ssort"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Use ssort when re-formatting code cells",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            Whether to use :py:mod:`ssort` when reformatting code cells.
        """,
    },
    # Preview options
    "output_file": {
        "apps_": ["preview"],
        "flags_": ["--output-file"],
        "nargs": "?",
        "const": "-",
        "type": Path,
        "help": "Output path when previewing file",
        "default": None,
        "schema_": {
            "type": "string",
        },
        "description_": """
                When set to a file path, the formatted output will be written to the
                given path. If no value is given (or the default "-" is passed) output
                will be printed to standard output.
            """,
    },
    "page": {
        "apps_": ["preview"],
        "flags_": ["--page"],
        "type": bool,
        "action": BooleanOptionalAction,
        "help": "Pass output to pager",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
                Whether to pipe output to the system pager when using ``--dump``.
            """,
    },
    # Edit / Preview options
    "files": {
        "apps_": ["edit", "preview", "hub"],
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
    "run": {
        "apps_": ["edit", "preview"],
        "flags_": ["--run"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Run the notebook when loaded",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            If set, notebooks will be run automatically when opened, or if previewing a
            file, the notebooks will be run before being output.
        """,
    },
    "expand": {
        "apps_": ["edit", "preview"],
        "flags_": ["--expand"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Use the full width to display notebooks",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            Whether the notebook page should expand to fill the available width
        """,
    },
    "max_notebook_width": {
        "apps_": ["edit", "preview"],
        "flags_": ["--max-notebook-width"],
        "type": int,
        "help": "Maximum width of notebooks",
        "default": 120,
        "schema_": {
            "type": "integer",
            "minimum": 1,
        },
        "description_": """
            The maximum width at which to display a notebook.
        """,
    },
    "tmux_graphics": {
        "apps_": ["edit", "preview"],
        "flags_": ["--tmux-graphics"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Enable terminal graphics in tmux (experimental)",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            If set, terminal graphics will be used if :program:`tmux` is running by
            performing terminal escape sequence pass-through. You must restart euporie
            forthis to take effect.

            .. warning::

               Terminal graphics in :program:`tmux` is experimental, and is not
               guaranteed to work. Use at your own risk!
        """,
    },
    "color_scheme": {
        "apps_": ["edit", "preview"],
        "flags_": ["--color-scheme"],
        "type": str,
        "choices": ["default", "inverse", "light", "dark", "black", "white", "custom"],
        "help": "The color scheme to use",
        "default": "default",
        "schema_": {
            "type": "string",
        },
        "description_": """
            The color scheme to use: `auto` means euporie will try to use your
            terminal's color scheme, `light` means black text on a white background,
            and `dark` means white text on a black background.
        """,
    },
    "custom_background_color": {
        "apps_": ["edit", "preview"],
        "flags_": ["--custom-background-color", "--custom-bg-color", "--bg"],
        "type": str,
        "help": 'Background color for "Custom" color theme',
        "default": "",
        "schema_": {
            "type": "string",
            "maxLength": 7,
        },
        "description_": """
            The hex code of the color to use for the background in the "Custom" color
            scheme.
        """,
    },
    "custom_foreground_color": {
        "apps_": ["edit", "preview"],
        "flags_": ["--custom-foreground-color", "--custom-fg-color", "--fg"],
        "type": str,
        "help": 'Background color for "Custom" color theme',
        "default": "",
        "schema_": {
            "type": "string",
            "maxLength": 7,
        },
        "description_": """
            The hex code of the color to use for the foreground in the "Custom" color
            scheme.
        """,
    },
    "syntax_theme": {
        "apps_": ["edit", "preview"],
        "flags_": ["--syntax-theme"],
        "type": str,
        # Do not want to print all theme names in --help screen as it looks messy
        "help": "Syntax highlighting theme",
        "default": "default",
        "schema_": {
            "type": "string",
            "enum": list(pygments_styles.keys()),
        },
        "description_": """
            The name of the pygments style to use for syntax highlighting.
        """,
    },
    "color_depth": {
        "apps_": ["edit", "preview"],
        "flags_": ["--color-depth"],
        "type": int,
        "choices": [1, 4, 8, 24],
        "default": None,
        "help": "The color depth to use",
        "schema_": {"type": "integer"},
        "description_": """
            The number of bits to use to represent colors displayable on the screen.
            If set to None, the supported color depth of the terminal will be detected
            automatically.
        """,
    },
    # Hub Options
    "host": {
        "apps_": ["hub"],
        "flags_": ["--host"],
        "type": str,
        "help": "The host address to bind to",
        "default": "",
        "schema_": {
            "type": "string",
        },
        "description_": """
                This determines the host address the euporie hub SSH server will bind to.
            """,
    },
    "port": {
        "apps_": ["hub"],
        "flags_": ["--port"],
        "type": int,
        "help": "The port for the ssh server to use",
        "default": 8022,
        "schema_": {
            "type": "integer",
            "minimum": 1,
            "maximum": 65535,
        },
        "description_": """
                This determines which port euporie will listen on for connections to
                euporie hub.
            """,
    },
    "host_keys": {
        "apps_": ["hub"],
        "flags_": ["--host-keys"],
        "nargs": "*",
        "type": Path,
        "help": "Host keys to use for the SSH server",
        "default": ["/etc/ssh/ssh_host_ecdsa_key"],
        "schema_": {
            "type": "array",
            "items": {
                "file": {
                    "description": "SSH host key file path",
                    "type": "string",
                },
            },
        },
        "description_": """
                One or more SSH host key files to use for the euporie hub SSH server.
            """,
    },
    "client_keys": {
        "apps_": ["hub"],
        "flags_": ["--client-keys"],
        "nargs": "*",
        "type": Path,
        "help": "Client public keys authorized to connect",
        "default": ["~/.ssh/authorized_keys"],
        "schema_": {
            "type": "array",
            "items": {
                "file": {
                    "description": "Path to file containing authorized public keys",
                    "type": "string",
                },
            },
        },
        "description_": """
                One or more OpenSSH-style :file:`authorized_keys` files, containing
                public keys for authorized clients.
            """,
    },
    "no_auth": {
        "apps_": ["hub"],
        "flags_": ["--no-auth"],
        "action": BooleanOptionalAction,
        "type": bool,
        "help": "Allow unauthenticated access to euporie hub",
        "default": False,
        "schema_": {
            "type": "boolean",
        },
        "description_": """
            When set, users will be able to access euporie hub without authentication.

            .. warning::

               This option is dangerous, as arbitrary code can be executed through
               Jupyter notebooks in euporie.
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
            **({"enum": choices} if (choices := param.get("choices", [])) else {}),
            **({"default": default} if (default := param.get("default")) else {}),
            **param["schema_"],
        }
        for name, param in CONFIG_PARAMS.items()
        if param.get("schema_")
    },
}


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
            return str(o.expanduser())
        return json.JSONEncoder.default(self, o)


_json_encoder = JSONEncoderPlus()


class ArgumentParser(argparse.ArgumentParser):
    """An argument parser with a default sub-command."""

    __default_subparser = None

    def set_default_subparser(self, name: "str") -> "None":
        """Sets the default subparser."""
        self.__default_subparser = name

    def _parse_known_args(
        self, arg_strings: "List[str]", *args: "Any", **kwargs: "Any"
    ) -> "Tuple[argparse.Namespace, List[str]]":
        in_args = set(arg_strings)
        d_sp = self.__default_subparser
        if d_sp is not None and not {"-h", "--help"}.intersection(in_args):
            assert self._subparsers is not None
            for x in self._subparsers._actions:
                subparser_found = isinstance(
                    x, argparse._SubParsersAction
                ) and in_args.intersection(x._name_parser_map.keys())
                if subparser_found:
                    break
            else:
                # insert default in first position, this implies no
                # global options without a sub_parsers specified
                arg_strings = [d_sp] + arg_strings
        return super(ArgumentParser, self)._parse_known_args(
            arg_strings, *args, **kwargs
        )


class Config:
    """A configuration object with configuration values available as attributes.

    Default configuration variables are loaded from the defaults defined in the
    schema, then overwritten with values defined in a configuration file.
    """

    valid_user: "bool"

    conf_file_name = "config.json"
    defaults = {name: param.get("default") for name, param in CONFIG_PARAMS.items()}

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

    def load_parser(self) -> "ArgumentParser":
        """Constructs an :py:class:`ArgumentParser`."""
        parser = ArgumentParser(
            description=__strapline__,
            epilog=__copyright__,
            allow_abbrev=True,
        )

        # Add a sub-parser for each app
        subparsers = parser.add_subparsers(
            title="subcommand",
            description="the subcommand to launch",
            help="The name of a subcommand to launch",
            dest="subcommand",
        )
        app_parsers = {}
        for app in APPS:
            name = app["name"]
            subparser = subparsers.add_parser(
                name=name,
                help=app["help"],
                description=app.get("description"),
                conflict_handler="resolve",
                formatter_class=argparse.MetavarTypeHelpFormatter,
            )
            subparser.set_defaults(app=app["class"])
            app_parsers[name] = subparser
            if app.get("default"):
                parser.set_default_subparser(name)

        # Add options to the relevant subparsers
        for name, data in CONFIG_PARAMS.items():
            if "flags_" in data:
                for subparser in [
                    app_parsers[app] for app in data.get("apps_", [])
                ] or [parser]:
                    subparser.add_argument(
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
