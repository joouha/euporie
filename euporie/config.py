# -*- coding: utf-8 -*-

CONFIG_DEFAULTS = {
    "max_notebook_width": 120,
    "show_background": True,
    "background_character": "·",
    "pygments_style": "default",
    "editing_mode": "emacs",
    "show_line_numbers": True,
}


class Config:
    def __init__(self):
        for key, value in CONFIG_DEFAULTS.items():
            setattr(self, key, value)


config = Config()
