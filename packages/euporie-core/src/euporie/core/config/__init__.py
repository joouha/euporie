"""Configuration system for euporie applications."""

from __future__ import annotations

from euporie.core.config._config import Config
from euporie.core.config._setting import Setting
from euporie.core.config._state import State

__all__ = [
    "Config",
    "Setting",
    "State",
    "add_setting",
    "add_state",
]

add_setting = Config.register
add_state = State.register
