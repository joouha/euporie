# -*- coding: utf-8 -*-
from collections import namedtuple

defaults = {
    "max_notebook_width": 120,
    "show_background": True,
    "background_character": "·",
    "pygments_style": "native",
    "editing_mode": "emacs",
}

Config = namedtuple(
    "config", **dict(zip(["field_names", "defaults"], zip(*defaults.items())))
)


config = Config()
