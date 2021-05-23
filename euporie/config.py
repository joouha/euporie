# -*- coding: utf-8 -*-
"""Defines a configuration class for euporie."""
from __future__ import annotations

import argparse
import json
import logging
import os
from collections import ChainMap
from pathlib import Path
from typing import Any, Iterator, Union

import jsonschema  # type: ignore
from appdirs import user_config_dir  # type: ignore
from pygments.styles import get_all_styles  # type: ignore

from euporie import __version__, _app_name

log = logging.getLogger(__name__)

CONFIG_SCHEMA: "dict" = {
    "title": "Euporie Configuration",
    "description": "A configuration for euporie",
    "type": "object",
    "properties": {
        "files": {
            "description": "List of file names to open",
            "type": "array",
            "items": {
                "file": {
                    "description": "File path",
                    "type": "string",
                }
            },
            "default": [],
            "positional": True,
            "python_type": Path,
            "nargs": "*",
        },
        "max_notebook_width": {
            "description": "The maximum width of the notebook",
            "type": "integer",
            "python_type": int,
            "minimum": 1,
            "default": 120,
        },
        "background": {
            "description": "The background pattern to use",
            "type": "integer",
            "python_type": int,
            "minimum": 0,
            "maximum": 4,
            "default": 1,
        },
        "background_character": {
            "description": "The character to use to draw the background",
            "type": "string",
            "python_type": str,
            "maxLength": 1,
            "default": "·",
        },
        "pygments_style": {
            "description": "The name of the pygments style for syntax highlighting",
            "type": "string",
            "python_type": str,
            "default": "default",
            "pattern": "(" + "|".join(get_all_styles()) + ")",
        },
        "editing_mode": {
            "description": "The key-binding style to use for text editing",
            "type": "string",
            "python_type": str,
            "pattern": "(emacs|vi)",
            "default": "emacs",
        },
        "show_line_numbers": {
            "description": "Whether line numbers are shown by default",
            "type": "boolean",
            "python_type": bool,
            "default": True,
        },
        "execute_after_external_edit": {
            "description": "Whether to execute a cell immediately after editing in $EDITOR",
            "type": "boolean",
            "python_type": bool,
            "default": False,
        },
    },
}


class Config:
    """A configuration object with configuration values available as attributes.

    Default configuration variables are loaded from the defaults defined in the
    schema, then overwritten with values defined in a configuration file.
    """

    conf_file_name = "config.json"
    defaults = {
        key: schema["default"]
        for key, schema in CONFIG_SCHEMA["properties"].items()
        if schema.get("default")
    }

    def __init__(self):
        """Ininitate the Configuration object."""
        self.user = {}
        self.env = {}
        self.args = {}

        user_conf_dir = Path(user_config_dir(_app_name, appauthor=False))
        user_conf_dir.mkdir(exist_ok=True, parents=True)
        self.config_file_path = user_conf_dir / self.conf_file_name
        self.valid_user = True

        self.load_user()
        self.load_env()
        self.load_args()

        self.chain = ChainMap(
            self.args,
            self.env,
            self.user,
            self.defaults,
        )

    def load_args(self) -> "None":
        """Attempts to load configuration settings from commandline flags."""
        parser = argparse.ArgumentParser(
            description="A TUI editor for Jupyter notebooks",
            epilog="euporie © 2021 Josiah Outram Halstead",
            allow_abbrev=True,
            formatter_class=argparse.MetavarTypeHelpFormatter,
        )
        parser.add_argument(
            "-V", "--version", action="version", version=f"%(prog)s {__version__}"
        )
        for name, schema in CONFIG_SCHEMA.get("properties", {}).items():
            name = name.replace("_", "-")
            kwargs = {
                # 'default': schema.get('default'),
                "help": schema.get("description"),
                "type": schema.get("python_type"),
            }
            if nargs := schema.get("nargs"):
                kwargs["nargs"] = nargs
            if pattern := schema.get("pattern"):
                kwargs["choices"] = pattern.strip("()").split("|")
            elif (
                schema.get("type") == "integer"
                and "minimum" in schema
                and "maximum" in schema
            ):
                kwargs["choices"] = range(schema["minimum"], schema["maximum"] + 1)
            if kwargs["type"] is bool:
                kwargs["action"] = argparse.BooleanOptionalAction
            prefix = "" if schema.get("positional") else "--"
            parser.add_argument(f"{prefix}{name}", **kwargs)
        for name, value in vars(parser.parse_args()).items():
            if value is not None:
                json = {name: value}
                try:
                    jsonschema.validate(instance=json, schema=CONFIG_SCHEMA)
                except jsonschema.ValidationError as error:
                    log.error(f"Error in command line parameter: `{name}`\n{error}")
                else:
                    self.args[name] = value

    def load_env(self) -> "None":
        """Attempt to load configuration settings from environment variables."""
        for name, schema in CONFIG_SCHEMA.get("properties", {}).items():
            env = f"{_app_name.upper()}_{name.upper()}"
            if env in os.environ:
                python_type = schema.get("python_type", str)
                try:
                    value = python_type(os.environ[env])
                except (ValueError, TypeError):
                    log.warning(
                        f"Environment variable `{env}` not understood"
                        f" - {schema.get('type')} expected"
                    )
                else:
                    json = {name: value}
                    try:
                        jsonschema.validate(instance=json, schema=CONFIG_SCHEMA)
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
                        log.error(
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
        except KeyError:
            raise KeyError(f"Variable not found in the user config: {name!r}")
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


config = Config()
