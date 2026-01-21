"""Key bindings registry.

Adds a :py:method:`KeyBindings.from_commands` method.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prompt_toolkit.key_binding.key_bindings import KeyBindings as PtkKeyBindings

from euporie.apptk.commands import get_cmd

if TYPE_CHECKING:
    from collections.abc import Sequence

log = logging.getLogger(__name__)

__all__ = ["KeyBindings"]


class KeyBindings(PtkKeyBindings):
    """A container for a set of key bindings."""

    @classmethod
    def from_commands(cls, commands: Sequence[str]) -> KeyBindings:
        """Create a new :py:class:`KeyBindings` instance from a list of command names."""
        kb = cls()
        for name in commands:
            try:
                get_cmd(name).bind(kb)
            except KeyError:
                log.warning("Command '%s' not known", name)
        return kb
