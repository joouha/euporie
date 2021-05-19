# -*- coding: utf-8 -*-
"""Defines a configuration class for euporie."""
from __future__ import annotations

import json
import logging
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Union

import jsonschema  # type: ignore

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

    win = sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt")

    def __init__(self):
        """Ininitate the Configuration object."""
        super().__setattr__("valid", True)
        self.load_defaults()
        self.load_config_file()

    @property  # type: ignore
    @lru_cache
    def config_file_path(self) -> "Path":
        """Determine where the user's config file should be stored.

        TODO: Consider replacing this with https://github.com/ActiveState/appdirs
        """
        if self.win:
            path = (
                Path(os.getenv("APPDATA", "~/appdata")).expanduser()
                / "roaming"
                / _app_name
            )
        elif sys.platform == "darwin":
            path = Path("~/Library/Application Support/").expanduser() / _app_name
        else:
            path = (
                Path(os.getenv("XDG_CONFIG_HOME", "~/.config")).expanduser() / _app_name
            )
        # Create config folder if it doesn't exist
        path.mkdir(exist_ok=True, parents=True)
        return path / "config.json"

    @property
    def json_data(self) -> "dict[str, Union[str, bool, int]]":
        """Attempts to load the configuration file json."""
        assert isinstance(self.config_file_path, Path)
        if self.valid and self.config_file_path.exists():
            with open(self.config_file_path, "r") as f:
                try:
                    json_data = json.load(f)
                except json.decoder.JSONDecodeError:
                    log.error(
                        "Could not parse the configuration file: "
                        f"{self.config_file_path}\n"
                        "Is it valid json?"
                    )
                    super().__setattr__("valid", False)
                else:
                    try:
                        jsonschema.validate(instance=json_data, schema=CONFIG_SCHEMA)
                    except jsonschema.ValidationError as error:
                        log.error(
                            f"Error in config file: {self.config_file_path}\n"
                            f"{error}"
                        )
                        super().__setattr__("valid", False)
                    else:
                        return json_data
            log.warning("The configuration file was not loaded")
        return {}

    def set(self, attr: "str", value: "Union[bool, int, str]") -> "None":
        """Set a configuration attribute.

        Args:
            attr: The name of the attribute to set
            value: The value to give the attribute

        """
        if hasattr(self, attr):
            setattr(self, attr, value)

    def toggle(self, attr: "str") -> "None":
        """Switches attributes between permitted configuration states.

        For boolean values, they are toggled between True and False. Integer values are
        incremented and reset within the permitted range.

        Args:
            attr: The name of the attribute to toggle.

        """
        if hasattr(self, attr):
            current = getattr(self, attr)
            schema = CONFIG_SCHEMA["properties"][attr]
            if schema["type"] == "boolean":
                setattr(self, attr, not current)
            elif schema["type"] == "integer":
                setattr(
                    self,
                    attr,
                    schema["minimum"]
                    + (current - schema["minimum"] + 1) % (schema["maximum"] + 1),
                )

    def load_defaults(self) -> "None":
        """Sets attributes from the default values in the JSON schema."""
        for key, schema in CONFIG_SCHEMA["properties"].items():
            super().__setattr__(key, schema["default"])

    def load_config_file(self) -> "None":
        """Sets attributes from JSON data loaded from the configuration file."""
        for key, value in self.json_data.items():
            super().__setattr__(key, value)

    def __getattr__(self, name: "str") -> "Union[bool, int, str]":
        """Defined to prevent mypy attemptint to type check dynamic attributes."""
        return getattr(self, name)

    def __setattr__(self, name: "str", value: "Union[bool, int, str]") -> "None":
        """Sets configuration attributes and writes their values to the config file."""
        if self.valid:
            json_data = self.json_data
            json_data[name] = value
            assert isinstance(self.config_file_path, Path)
            with open(self.config_file_path, "w") as f:
                json.dump(json_data, f, indent=2)
        return super().__setattr__(name, value)


config = Config()
