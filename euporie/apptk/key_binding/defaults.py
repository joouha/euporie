"""Default key bindings."""

from __future__ import annotations

import logging

from euporie.apptk.key_binding.bindings.cpr import load_cpr_bindings
from euporie.apptk.key_binding.bindings.emacs import (
    load_emacs_bindings,
    load_emacs_search_bindings,
    load_emacs_shift_selection_bindings,
)
from euporie.apptk.key_binding.bindings.vi import (
    load_vi_bindings,
    load_vi_search_bindings,
)
from euporie.apptk.key_binding.key_bindings import (
    ConditionalKeyBindings,
    KeyBindingsBase,
    merge_key_bindings,
)

from euporie.apptk.filters import buffer_has_focus
from euporie.apptk.key_binding.bindings.basic import load_basic_bindings
from euporie.apptk.key_binding.bindings.micro import load_micro_bindings
from euporie.apptk.key_binding.bindings.mouse import load_mouse_bindings
from euporie.apptk.key_binding.bindings.terminal import load_terminal_bindings

__all__ = [
    "load_key_bindings",
]

log = logging.getLogger(__name__)


def load_key_bindings() -> KeyBindingsBase:
    """Create a KeyBindings object that contains the default key bindings."""
    all_bindings = merge_key_bindings(
        [
            # Load basic bindings.
            load_basic_bindings(),
            # Load emacs bindings.
            load_emacs_bindings(),
            load_emacs_search_bindings(),
            load_emacs_shift_selection_bindings(),
            # Load Vi bindings.
            load_vi_bindings(),
            load_vi_search_bindings(),
            # Load micro bindings
            load_micro_bindings(),
        ]
    )

    return merge_key_bindings(
        [
            # Make sure that the above key bindings are only active if the
            # currently focused control is a `BufferControl`. For other controls, we
            # don't want these key bindings to intervene. (This would break "ptterm"
            # for instance, which handles 'Keys.Any' in the user control itself.)
            ConditionalKeyBindings(all_bindings, buffer_has_focus),
            # Active, even when no buffer has been focused.
            load_mouse_bindings(),
            load_cpr_bindings(),
            load_terminal_bindings(),
        ]
    )
