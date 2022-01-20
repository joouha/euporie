"""Load the key-bindings for the application."""

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.key_binding import merge_key_bindings

# from euporie.config import config
from euporie.key_binding.bindings.commands import command_default_bindings
from euporie.key_binding.bindings.micro import micro_bindings

# from euporie.key_binding.util import dict_bindings

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyBindingsBase

log = logging.getLogger(__name__)


def load_key_bindings() -> "KeyBindingsBase":
    """Load all application key-bindings."""
    all_bindings = [
        command_default_bindings(),
        micro_bindings(),
        # dict_bindings(config.key_bindings or {})
    ]

    return merge_key_bindings(all_bindings)
