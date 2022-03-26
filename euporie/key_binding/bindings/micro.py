"""Defines editor key-bindings in the style of the ``micro`` text editor."""

from typing import TYPE_CHECKING

from aenum import extend_enum  # type: ignore
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.key_binding import ConditionalKeyBindings, merge_key_bindings

from euporie.filters import micro_mode
from euporie.key_binding.bindings.commands import load_command_bindings
from euporie.key_binding.util import dict_bindings

if TYPE_CHECKING:
    from typing import Dict, List, Tuple, Union

    from prompt_toolkit.key_binding import KeyBindingsBase
    from prompt_toolkit.keys import Keys


extend_enum(EditingMode, "MICRO", "MICRO")


# TODO - move these keybindings into command definitions
MICRO_BINDINGS: "Dict[str, Union[List[Union[Tuple[Union[Keys, str], ...], Keys, str]], Union[Tuple[Union[Keys, str], ...], Keys, str]]]" = {  # noqa B950
    "type-key": "<any>",
    "move-cursor-right": "right",
    "move-cursor-left": "left",
    "newline": "enter",
    "accept-line": "enter",
    "backspace": ["backspace", "c-h"],
    "backward-kill-word": [("escape", "backspace"), ("escape", "c-h")],
    "start-selection": [
        "s-up",
        "s-down",
        "s-right",
        "s-left",
        ("escape", "s-left"),
        ("escape", "s-right"),
        "c-s-left",
        "c-s-right",
        "s-home",
        "s-end",
        "c-s-home",
        "c-s-end",
    ],
    "extend-selection": [
        "s-up",
        "s-down",
        "s-right",
        "s-left",
        ("escape", "s-left"),
        ("escape", "s-right"),
        "c-s-left",
        "c-s-right",
        "s-home",
        "s-end",
        "c-s-home",
        "c-s-end",
    ],
    "cancel-selection": [
        "up",
        "down",
        "right",
        "left",
        ("escape", "left"),
        ("escape", "right"),
        "c-left",
        "c-right",
        "home",
        "end",
        "c-home",
        "c-end",
    ],
    "replace-selection": "<any>",
    "delete-selection": ["delete", "backspace", "c-h"],
    "backward-word": ["c-left", ("escape", "b")],
    "forward-word": ["c-right", ("escape", "f")],
    "move-lines-up": ("escape", "up"),
    "move-lines-down": ("escape", "down"),
    "go-to-start-of-line": ["home", ("escape", "left"), ("escape", "a")],
    "go-to-end-of-line": ["end", ("escape", "right"), ("escape", "e")],
    "beginning-of-buffer": ["c-up", "c-home"],
    "end-of-buffer": ["c-down", "c-end"],
    "go-to-start-of-paragraph": ("escape", "{"),
    "go-to-end-of-paragraph": ("escape", "}"),
    "indent-lines": "tab",
    "unindent-line": "backspace",
    "unindent-lines": "s-tab",
    "undo": "c-z",
    "redo": "c-y",
    "copy-selection": "c-c",
    "cut-selection": "c-x",
    "cut-line": "c-k",
    "duplicate-line": "c-d",
    "duplicate-selection": "c-d",
    "paste-clipboard": "c-v",
    "select-all": "c-a",
    "scroll-page-up": "pageup",
    "scroll-page-down": "pagedown",
    "delete": "delete",
    "toggle-case": "f4",
    "toggle-overwrite-mode": "insert",
    "start-macro": "c-u",
    "end-macro": "c-u",
    "run-macro": "c-j",
    "accept-suggestion": ["right", "c-f"],
    "fill-sugestion": ("escape", "f"),
    "toggle-comment": "c-_",
}


def load_micro_bindings() -> "KeyBindingsBase":
    """Load editor key-bindings in the style of the ``micro`` text editor."""
    return ConditionalKeyBindings(
        merge_key_bindings(
            [
                load_command_bindings("micro-edit-mode"),
                dict_bindings(MICRO_BINDINGS),
            ]
        ),
        micro_mode,
    )

    # ----------------

    # // Search
    # "F3":  "Find",
    # "F7":  "Find",
    # "Ctrl-f":          "Find",
    # "Ctrl-n":          "FindNext",
    # "Ctrl-p":          "FindPrevious",

    # "Ctrl-q":          "Quit",
    # "F4":  "Quit",
    # "F2":  "Save",
    # "F10": "Quit",
    # "Ctrl-l":          "command-edit:goto",
    # "Ctrl-r":          "ToggleRuler",
    # "Alt-g":          "ToggleKeyMenu",
    # "Ctrl-g":          "ToggleHelp",
    # "Ctrl-w":          "NextSplit",
    # "Ctrl-o":          "OpenFile",
    # "Ctrl-s":          "Save",
    # "Ctrl-t":          "AddTab",
    # "Alt-,":           "PreviousTab",
    # "Alt-.":           "NextTab",
    # "CtrlPageUp":     "PreviousTab",
    # "CtrlPageDown":   "NextTab",

    # // Mouse bindings
    # "MouseWheelUp":   "ScrollUp",
    # "MouseWheelDown": "ScrollDown",
    # "MouseLeft":      "MousePress",
    # "MouseMiddle":    "PastePrimary",
    # "Ctrl-MouseLeft": "MouseMultiCursor",

    # // Multi-cursor stuff (TODO)
    # "Alt-n":        "SpawnMultiCursor",
    # "AltShiftUp":   "SpawnMultiCursorUp",
    # "AltShiftDown": "SpawnMultiCursorDown",
    # "Alt-m":        "SpawnMultiCursorSelect",
    # "Alt-p":        "RemoveMultiCursor",
    # "Alt-c":        "RemoveAllMultiCursors",
    # "Alt-x":        "SkipMultiCursor",
