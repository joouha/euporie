# -*- coding: utf-8 -*-
"""Defines a configuration class for euporie."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Iterator, Union

import jsonschema  # type: ignore
from appdirs import user_config_dir  # type: ignore

from euporie import _app_name

log = logging.getLogger(__name__)

CONFIG_SCHEMA: "dict" = {
    "title": "Euporie Configuration",
    "description": "A configuration for euporie",
    "type": "object",
    "properties": {
        "max_notebook_width": {
            "description": "The maximum width of the notebook",
            "type": "integer",
            "minimum": 1,
            "default": 120,
        },
        "background": {
            "description": "The background pattern to use",
            "type": "integer",
            "minimum": 0,
            "maximum": 4,
            "default": 1,
        },
        "background_character": {
            "description": "The character to use to draw the background",
            "type": "string",
            "maxLength": 1,
            "default": "·",
        },
        "pygments_style": {
            "description": "The name of the pygments style for syntax highlighting",
            "type": "string",
            "default": "default",
        },
        "editing_mode": {
            "description": "The key-binding style to use for text editing",
            "type": "string",
            "pattern": "(emacs|vi)",
            "default": "emacs",
        },
        "show_line_numbers": {
            "description": "Whether line numbers are shown by default",
            "type": "boolean",
            "default": True,
        },
        "execute_after_external_edit": {
            "description": "Whether to execute a cell immediately after editing in $EDITOR",
            "type": "boolean",
            "default": False,
        },
    },
}


class Config:
    """A configuration object with configuration values available as attributes.

    Default configuration variables are loaded from the defaults defined in the
    schema, then overwritten with values defined in a configuration file.
    """

    defaults = {
        key: schema["default"] for key, schema in CONFIG_SCHEMA["properties"].items()
    }
    conf_file_name = "config.json"

    def __init__(self):
        """Ininitate the Configuration object."""
        self.valid_user_conf = True
        self.user_conf = {}
        conf_dir = Path(user_config_dir(_app_name, appauthor=False))
        conf_dir.mkdir(exist_ok=True, parents=True)
        self.config_file_path = conf_dir / self.conf_file_name
        self.load_config_file()

    def load_config_file(self) -> "None":
        """Attempts to load the configuration file json."""
        assert isinstance(self.config_file_path, Path)
        if self.valid_user_conf and self.config_file_path.exists():
            with open(self.config_file_path, "r") as f:
                try:
                    json_data = json.load(f)
                except json.decoder.JSONDecodeError:
                    log.error(
                        "Could not parse the configuration file: "
                        f"{self.config_file_path}\n"
                        "Is it valid json?"
                    )
                    self.valid_user_conf = False
                else:
                    try:
                        jsonschema.validate(instance=json_data, schema=CONFIG_SCHEMA)
                    except jsonschema.ValidationError as error:
                        log.error(
                            f"Error in config file: {self.config_file_path}\n"
                            f"{error}"
                        )
                        self.valid_user_conf = False
                    else:
                        self.user_conf.update(json_data)
                        return
            log.warning("The configuration file was not loaded")

    def get(self, name: "str") -> "Any":
        """Access a configuration variable, falling back to the default value if unset.

        Args:
            name: The name of the attribute to access.

        Returns:
            The configuration variable value.

        """
        return self.user_conf.get(name, self.defaults.get(name))

    def __getattr__(self, name: "str") -> "Union[bool, int, str]":
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
        self.user_conf[name] = value
        if self.valid_user_conf:
            with open(self.config_file_path, "w") as f:
                json.dump(self.user_conf, f, indent=2)

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
            del self.user_conf[name]
        except KeyError:
            raise KeyError(f"Variable not found in the user config: {name!r}")
        else:
            if self.valid_user_conf:
                with open(self.config_file_path, "w") as f:
                    json.dump(self.user_conf, f, indent=2)

    @property
    def all(self) -> "dict[str, Any]":
        """Return a combined dictionary of user and default values.

        Returns:
            The combined dictionary.

        """
        d = dict(self.defaults)
        d.update(self.user_conf)
        return d

    def __iter__(self) -> "Iterator[str]":
        """Iterate over all configuration variable names.

        Returns:
            An iterable of the combined dictionary.

        """
        return iter(self.all)

    def __len__(self) -> "int":
        """Return the length of the combined user and default settings.

        Returns:
            The length of the combined dictionary.

        """
        return len(set().union(self.defaults, self.user_conf))

    def __str__(self) -> "str":
        """Represent the configuration as a string.

        Returns:
            A string representing the configuration.

        """
        return f"Config({self.all!r})"

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
