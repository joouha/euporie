from __future__ import annotations

from enum import Enum


class EditingMode(Enum):
    """The set of key bindings that is active."""

    VI = "VI"
    EMACS = "EMACS"
    MICRO = "MICRO"
