# -*- coding: utf-8 -*-
"""Generates a markdown table of key-bindings used in euporie."""
from pathlib import Path

from euporie.app import App
from euporie.cell import Cell
from euporie.keys import KeyBindingsInfo
from euporie.notebook import Notebook
from euporie.scroll import ScrollingContainer

app = App()
nb = Notebook(Path("/this/file/does/not/exist.ipynb"))
ScrollingContainer([])
Cell(0, {}, nb)

key_details = {
    group: {
        "`"
        + "` / `".join(
            [
                " ".join(
                    (
                        part.replace("c-", "ctrl-").replace("s-", "shift-")
                        for part in key
                    )
                )
                for key in keys
            ]
        )
        + "`": desc
        for desc, keys in info.items()
    }
    for group, info in KeyBindingsInfo.details.items()
}

max_key_len = max([len(key) for group in key_details.values() for key in group]) + 1
max_desc_len = (
    max([len(desc) for group in key_details.values() for desc in group.values()]) + 1
)

print(f"| {'Key Binding'.rjust(max_key_len)} | {'Command'.ljust(max_desc_len)} |")
print(f"| {'-'.ljust(max_key_len, '-')}:|:{'-'.rjust(max_desc_len, '-')} |")
for group, item in key_details.items():
    print(f"| {('**' + group + '**').rjust(max_key_len)} | {' '.rjust(max_desc_len)} |")
    for key, desc in item.items():
        print(f"| {key.rjust(max_key_len)} | {desc.ljust(max_desc_len)} |")


nb.close(lambda: None)
