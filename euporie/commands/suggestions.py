# -*- coding: utf-8 -*-
from prompt_toolkit.application import get_app

from euporie.commands.registry import add
from euporie.filters import has_suggestion


# Suggestions
@add(
    # keys=["right", "c-f"],
    filter=has_suggestion,
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
)
def fill_sugestion(event: "KeyPressEvent") -> "None":
    """Fill partial suggestion."""
    b = get_app().current_buffer
    suggestion = b.suggestion
    if suggestion:
        t = re.split(r"(\S+\s+)", suggestion.text)
        b.insert_text(next(x for x in t if x))
