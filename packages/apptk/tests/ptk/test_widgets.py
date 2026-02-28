from __future__ import annotations

from apptk.formatted_text import fragment_list_to_text
from apptk.layout import to_window
from apptk.widgets import Button


def _to_text(button: Button) -> str:
    control = to_window(button).content
    return fragment_list_to_text(control.text())


def test_default_button():
    button = Button("Exit")
    assert _to_text(button) == "<   Exit   >"


def test_custom_button():
    button = Button("Exit", left_symbol="[", right_symbol="]")
    assert _to_text(button) == "[   Exit   ]"
