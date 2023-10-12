"""Register additional key escape sequences."""

from itertools import combinations

from aenum import extend_enum
from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES
from prompt_toolkit.keys import Keys

# Map key-modifier to key-name & emacs style shortcut prefix
_modifiers = {
    # 0b00000000: ("", ""),
    0b00000001: ("Shift", "s"),
    0b00000010: ("Alt", "A"),
    0b00000100: ("Control", "c"),
    # 0b00001000: ("Super", "S"),
    # 0b00010000: ("Meta", "M"),
    # 0b00100000: ("Hyper", "H"),
    0b01000000: ("", ""),  # ScollLock - pass-through
    0b10000000: ("", ""),  # NumLock - pass-through
}

_key_nos = {
    9: "tab",
    13: "enter",
    27: "escape",
    32: "space",
    **{i: chr(i) for i in range(126, 32, -1)},
    127: "backspace",
}


# Kitty style legacy function keys
_kitty_functional_codes = {
    "Insert": (2, "~"),
    "Delete": (3, "~"),
    "PageUp": (5, "~"),
    "PageDown": (6, "~"),
    "Up": (1, "A"),
    "Down": (1, "B"),
    "Right": (1, "C"),
    "Left": (1, "D"),
    "Home": (1, "H"),
    "End": (1, "F"),
    "PrintScreen": (57361, "u"),
    "Pause": (57362, "u"),
    "Menu": (57363, "u"),
    "F1": (1, "P"),
    "F2": (1, "Q"),
    "F3": (13, "~"),
    "F4": (1, "S"),
    "F5": (15, "~"),
    "F6": (17, "~"),
    "F7": (18, "~"),
    "F8": (19, "~"),
    "F9": (20, "~"),
    "F10": (21, "~"),
    "F11": (23, "~"),
    "F12": (24, "~"),
    # "Menu": (29, "~"),
}

# Add Alt-key shortcuts
for key in _key_nos.values():
    key_var = f"Alt{key.title()}"
    if not hasattr(Keys, key_var):
        extend_enum(Keys, key_var, f"A-{key}")
    key_enum = getattr(Keys, key_var)
    # Alias escape + key for Alt-key
    ANSI_SEQUENCES[f"\x1b{key}"] = key_enum  # type: ignore

# Add CSI-u escape key
ANSI_SEQUENCES["\x1b[27u"] = Keys.Escape

# Add various CSI-u style keys
for n in range(len(_modifiers)):
    for mod_combo in combinations(_modifiers.items(), n):
        mod_name = "".join(name for _bit, (name, _short) in mod_combo[::-1])
        mod_short = "-".join(short for _bit, (_name, short) in mod_combo[::-1] if _name)
        mod_no = 1 + sum(bit for bit, _ in mod_combo)

        if mod_name:
            for i, key in _key_nos.items():
                key_var = f"{mod_name}{key.title()}"
                if not hasattr(Keys, key_var):
                    extend_enum(Keys, key_var, f"{mod_short}-{key}")
                key_enum = getattr(Keys, key_var)
                # CSI-u style
                ANSI_SEQUENCES[f"\x1b[{i};{mod_no}u"] = key_enum  # type: ignore
                # xterm style
                ANSI_SEQUENCES[f"\x1b[27;{mod_no};{i}~"] = key_enum  # type: ignore

        for key, (number, suffix) in _kitty_functional_codes.items():
            key_var = f"{mod_name}{key}"
            if not hasattr(Keys, key_var):
                mod_str = f"{mod_short}-" if mod_short else ""
                extend_enum(Keys, key_var, f"{mod_str}{key.lower()}")
            mod_str = str(mod_no)
            num_str = str(number)
            if mod_no == 1:
                mod_str = ""
                if number == 1:
                    num_str = ""
            seq = "\x1b[" + (";".join(x for x in [num_str, mod_str] if x)) + suffix
            ANSI_SEQUENCES[seq] = getattr(Keys, key_var)  # type: ignore
