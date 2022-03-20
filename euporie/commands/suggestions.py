"""Defines command relating to suggestions."""

import re
from typing import TYPE_CHECKING

from euporie.app.current import get_base_app as get_app
from euporie.commands.registry import add
from euporie.filters import has_suggestion

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyPressEvent


@add(
    # keys=["right", "c-f"],
    filter=has_suggestion,
    group="suggestion",
)
def accept_suggestion(event: "KeyPressEvent") -> "None":
    """Accept suggestion."""
    b = get_app().current_buffer
    suggestion = b.suggestion
    if suggestion:
        b.insert_text(suggestion.text)


@add(
    # keys=("escape", "f"),
    filter=has_suggestion,
    group="suggestion",
)
def fill_sugestion(event: "KeyPressEvent") -> "None":
    """Fill partial suggestion."""
    b = get_app().current_buffer
    suggestion = b.suggestion
    if suggestion:
        t = re.split(r"(\S+\s+)", suggestion.text)
        b.insert_text(next(x for x in t if x))
