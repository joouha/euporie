# -*- coding: utf-8 -*-
import json
import os
import sys
from functools import lru_cache
from pathlib import Path

from euporie import _app_name

DEFAULT_CONFIG = {
    "max_notebook_width": 120,
    "background": 1,
    "background_character": "·",
    "pygments_style": "default",
    "editing_mode": "emacs",
    "show_line_numbers": True,
}


class Config:
    win = sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt")

    def __init__(self):
        self.load_defaults()
        self.load_config_file()

    @property
    @lru_cache
    def config_file_path(self):
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
    def json_data(self):
        if self.config_file_path.exists():
            with open(self.config_file_path, "r") as f:
                try:
                    return json.load(f)
                except json.decoder.JSONDecodeError:
                    pass
        return {}

    def set(self, attr, value):
        if hasattr(self, attr):
            setattr(self, attr, value)

    def toggle(self, attr):
        if hasattr(self, attr) and isinstance(getattr(self, attr), (bool, int)):
            setattr(self, attr, not getattr(self, attr))

    def load_defaults(self):
        for key, value in DEFAULT_CONFIG.items():
            super().__setattr__(key, value)

    def load_config_file(self):
        for key, value in self.json_data.items():
            super().__setattr__(key, value)

    def __setattr__(self, name, value):
        json_data = self.json_data
        json_data[name] = value
        with open(self.config_file_path, "w") as f:
            json.dump(json_data, f, indent=4)
        return super().__setattr__(name, value)


config = Config()
