# -*- coding: utf-8 -*-
"""Defines the application's menu structure."""
from pygments.styles import get_all_styles  # type: ignore

from euporie.commands.registry import get
from euporie.config import config
from euporie.menu.item import MenuItem


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
                separator,
                get("reformat-cell-black").menu,
                get("reformat-notebook").menu,
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
                        get(f"set-edit-mode-{choice}").menu
                        for choice in config.choices("edit_mode")
                    ],
                ),
                separator,
                MenuItem(
                    "Color scheme",
                    children=[
                        get(f"set-color-scheme-{choice}").menu
                        for choice in config.choices("color_scheme")
                    ],
                ),
                MenuItem(
                    "Syntax Theme",
                    children=[
                        get(f"set-syntax-theme-{choice}").menu
                        for choice in sorted(get_all_styles())
                    ],
                ),
                get("switch-background-pattern").menu,
                get("show-cell-borders").menu,
                get("tmux-terminal-graphics").menu,
                separator,
                get("use-full-width").menu,
                get("show-line-numbers").menu,
                get("show-status-bar").menu,
                separator,
                MenuItem(
                    "Cell formatting",
                    children=[
                        get("autoformat").menu,
                        separator,
                        get("format-black").menu,
                        get("format-isort").menu,
                        get("format-ssort").menu,
                    ],
                ),
                get("autocomplete").menu,
                get("autosuggest").menu,
                get("autoinspect").menu,
                get("run-after-external-edit").menu,
            ],
        ),
        MenuItem(
            "Help",
            children=[
                get("show-command-palette").menu,
                get("keyboard-shortcuts").menu,
                get("view-documentation").menu,
                separator,
                get("view-logs").menu,
                separator,
                get("about").menu,
            ],
        ),
    ]
