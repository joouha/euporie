# -*- coding: utf-8 -*-
"""Defines the application's menu structure."""
from functools import partial

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from pygments.styles import get_all_styles  # type: ignore

from euporie.commands.registry import get
from euporie.components.menu.item import MenuItem
from euporie.config import config


def load_menu_items() -> "list[MenuItem]":
    """Loads the list of menu items to display in the menu."""
    separator = MenuItem(separator=True)
    return [
        MenuItem(
            "File",
            children=[
                get("new-notebook").menu,
                get("open-file").menu,
                separator,
                get("save-notebook").menu,
                get("close-file").menu,
                separator,
                get("quit").menu,
            ],
        ),
        MenuItem(
            "Edit",
            children=[
                get("cut-cell").menu,
                get("copy-cell").menu,
                get("paste-cell").menu,
            ],
        ),
        MenuItem(
            "Run",
            children=[
                get("run-cell").menu,
                get("run-all-cells").menu,
            ],
        ),
        MenuItem(
            "Kernel",
            children=[
                get("interrupt-kernel").menu,
                get("restart-kernel").menu,
                get("change-kernel").menu,
            ],
        ),
        MenuItem(
            "Settings",
            children=[
                MenuItem(
                    "Editor key bindings",
                    children=[
                        MenuItem(
                            choice.title(),
                            handler=partial(get_app().set_edit_mode, choice),
                            toggled=Condition(
                                partial(lambda x: config.edit_mode == x, choice),
                            ),
                        )
                        for choice in config.choices("edit_mode")
                    ],
                ),
                separator,
                MenuItem(
                    "Color scheme",
                    children=[
                        MenuItem(
                            choice.title(),
                            handler=partial(
                                get_app().update_style, color_scheme=choice
                            ),
                            toggled=Condition(
                                partial(lambda x: config.color_scheme == x, choice)
                            ),
                        )
                        for choice in config.choices("color_scheme")
                    ],
                ),
                MenuItem(
                    "Syntax Theme",
                    children=[
                        MenuItem(
                            style,
                            handler=partial(
                                get_app().update_style, pygments_style=style
                            ),
                            toggled=Condition(
                                partial(lambda x: config.syntax_theme == x, style)
                            ),
                        )
                        for style in sorted(get_all_styles())
                    ],
                ),
                get("switch-background-pattern").menu,
                get("show-cell-borders").menu,
                separator,
                get("use-full-width").menu,
                get("show-line-numbers").menu,
                get("show-status-bar").menu,
                separator,
                get("autocomplete").menu,
                get("autosuggest").menu,
                get("run-after-external-edit").menu,
            ],
        ),
        MenuItem(
            "Help",
            children=[
                get("keyboard-shortcuts").menu,
                get("view-logs").menu,
                separator,
                get("about").menu,
            ],
        ),
    ]
