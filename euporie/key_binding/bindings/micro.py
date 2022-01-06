# -*- coding: utf-8 -*-
import logging

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import has_selection, shift_selection_mode
from prompt_toolkit.key_binding import (
    ConditionalKeyBindings,
    KeyBindings,
    KeyBindingsBase,
)
from prompt_toolkit.key_binding.bindings.named_commands import get_by_name
from prompt_toolkit.key_binding.key_bindings import Binding
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys

from euporie.commands import get
from euporie.filters import micro_mode
from euporie.key_binding.load import dict_bindings

log = logging.getLogger(__name__)


def micro_bindings() -> "KeyBindingsBase":
    kb = dict_bindings(
        {
            "type-key": "<any>",
            "move-cursor-right": "right",
            "move-cursor-left": "left",
            "newline": "enter",
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
            "go-to-start-of-line": ("escape", "left"),
            "go-to-end-of-line": ("escape", "right"),
            "beginning-of-buffer": "c-up",
            "end-of-buffer": "c-down",
            "go-to-start-of-paragraph": ("escape", "{"),
            "go-to-end-of-paragraph": ("escape", "}"),
            "indent-lines": ["tab"],
            "unindent-line": "backspace",
            "unindent-lines": "s-tab",
            "undo": "c-z",
            "redo": "c-y",
            "copy-selection": "c-c",
            "cut-selection": "c-x",
            "cut-line": "c-k",
            "duplicate-line": "c-d",
            "paste-clipboard": "c-v",
            "select-all": "c-a",
            "go-to-start-of-line": ["home", ("escape", "a")],
            "go-to-end-of-line": ["end", ("escape", "e")],
            "beginning-of-buffer": "c-home",
            "end-of-buffer": "c-end",
            "scroll-page-up": "pageup",
            "scroll-page-down": "pagedown",
            "delete": "delete",
            "toggle-case": "f16",
            "toggle-micro-input-mode": "insert",
            "start-macro": "c-u",
            "end-macro": "c-u",
            "run-macro": "c-j",
            "accept-suggestion": ["right", "c-f"],
            "fill-sugestion": ("escape", "f"),
        }
    )

    return ConditionalKeyBindings(kb, micro_mode)

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
