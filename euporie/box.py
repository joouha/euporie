# -*- coding: utf-8 -*-
from prompt_toolkit.widgets import base


class Border:
    "Box drawing characters. (Thin)"
    HORIZONTAL = "─"
    VERTICAL = "│"
    TOP_LEFT = "╭"
    TOP_RIGHT = "╮"
    BOTTOM_LEFT = "╰"
    BOTTOM_RIGHT = "╯"
    SPLIT_BOTTOM = "┴"
    SPLIT_TOP = "┬"
    SPLIT_LEFT = "├"
    SPLIT_RIGHT = "┤"
    CROSS = "┼"


base.Border = Border
