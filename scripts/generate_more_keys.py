"""Register additional key escape sequences."""

from __future__ import annotations

import unicodedata
from itertools import combinations

# Map key-modifier to key-name & emacs style shortcut prefix
_modifiers = {
    # 0b00000000: ("", ""),
    0b00000001: ("Shift", "s"),
    0b00000010: ("Alt", "A"),
    0b00000100: ("Control", "c"),
    # 0b00001000: ("Super", "S"),
    # 0b00010000: ("Meta", "M"),
    # 0b00100000: ("Hyper", "H"),
    0b01000000: ("", ""),  # ScrollLock - pass-through
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
    "escape": (27, "u"),
    "insert": (2, "~"),
    "delete": (3, "~"),
    "pageup": (5, "~"),
    "pagedown": (6, "~"),
    "up": (1, "A"),
    "down": (1, "B"),
    "right": (1, "C"),
    "left": (1, "D"),
    "home": (1, "H"),
    "end": (1, "F"),
    "printscreen": (57361, "u"),
    "pause": (57362, "u"),
    "menu": (57363, "u"),
    "f1": (1, "P"),
    "f2": (1, "Q"),
    "f3": (13, "~"),
    "f4": (1, "S"),
    "f5": (15, "~"),
    "f6": (17, "~"),
    "f7": (18, "~"),
    "f8": (19, "~"),
    "f9": (20, "~"),
    "f10": (21, "~"),
    "f11": (23, "~"),
    "f12": (24, "~"),
    "backspace": (127, "u"),
    "enter": (13, "u"),
    "tab": (9, "u"),
}

new_keys: dict[str, str] = {}
new_ansi: dict[str, str] = {}

# Add Alt-key shortcuts
for key in _key_nos.values():
    key_name = f"A-{key}"
    title = (
        unicodedata.name(key).title().replace(" ", "").replace("-", "")
        if len(key) == 1
        else key
    )
    key_title = f"Alt{title.title()}"
    new_keys.setdefault(key_title, key_name)
    new_ansi[f"\x1b{key}"] = key_title

# Add various CSI-u style keys
for n in range(len(_modifiers)):
    for mod_combo in combinations(_modifiers.items(), n):
        mod_name = "".join(name for _bit, (name, _short) in mod_combo[::-1])
        mod_short = "-".join(short for _bit, (_name, short) in mod_combo[::-1] if _name)
        mod_no = 1 + sum(bit for bit, _ in mod_combo)

        if mod_name:
            for i, key in _key_nos.items():
                key_name = f"{mod_short}-{key}"
                title = (
                    unicodedata.name(key).title().replace(" ", "").replace("-", "")
                    if len(key) == 1
                    else key
                )
                key_title = f"{mod_name}{title.title()}"
                new_keys.setdefault(f"{mod_name}{title.title()}", key_name)
                # CSI-u style escape sequence
                new_ansi[f"\x1b[{i};{mod_no}u"] = key_title
                # xterm style escape sequence
                new_ansi[f"\x1b[27;{mod_no};{i}~"] = key_title

        for key, (number, suffix) in _kitty_functional_codes.items():
            mod_str = f"{mod_short}-" if mod_short else ""
            key_name = f"{mod_str}{key}"
            mod_str = str(mod_no)
            num_str = str(number)
            if mod_no == 1:
                mod_str = ""
                if number == 1:
                    num_str = ""
            seq = "\x1b[" + (";".join(x for x in [num_str, mod_str] if x)) + suffix
            key_title = f"{mod_name}{key.title()}"
            new_keys.setdefault(key_title, key_name)
            new_ansi[seq] = key_title


print('''"""Register additional key escape sequences."""

from enum import Enum
from typing import TYPE_CHECKING, cast

from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES

if TYPE_CHECKING:
    from prompt_toolkit.keys import Keys


class MoreKeys(str, Enum):
    """Additional key definitions."""

    # Special terminal response keys
    ColorsResponse = "<colors-response>"
    PixelSizeResponse = "<pixel-size-response>"
    KittyGraphicsStatusResponse = "<kitty-graphics-status-response>"
    DeviceAttributesResponse = "<device-attributes-response>"
    ItermGraphicsStatusResponse = "<iterm-graphics-status-response>"
    SgrPixelStatusResponse = "<sgr-pixel-status-response>"
    ClipboardDataResponse = "<clipboard-data-response>"

    # Regular key-presses
''')

for k, v in new_keys.items():
    print(f"    {k} = {v!r}")


print("""
# Update PTK's mapping of escape codes to known key-presses
ANSI_SEQUENCES.update(
    cast("dict[str, Keys]", {""")
for seq, title in new_ansi.items():
    print(f"        {seq!r}: MoreKeys.{title},")
print("""    })
)
""")
