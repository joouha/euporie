# -*- coding: utf-8 -*-
import logging

from prompt_toolkit.key_binding import (
    ConditionalKeyBindings,
    KeyBindings,
    KeyBindingsBase,
)
from prompt_toolkit.key_binding.bindings.emacs import (
    load_emacs_shift_selection_bindings,
)
from prompt_toolkit.key_binding.key_bindings import KeyBindings, merge_key_bindings

from euporie.config import config
from euporie.key_binding.bindings.commands import command_default_bindings
from euporie.key_binding.bindings.micro import micro_bindings
from euporie.key_binding.load import dict_bindings

log = logging.getLogger(__name__)


def load_key_bindings() -> "KeyBindingsBase":
    """"""
    all_bindings = [
        command_default_bindings(),
        micro_bindings(),
        # dict_bindings(config.key_bindings or {})
    ]

    return merge_key_bindings(all_bindings)
