"""Defines application settings."""

from __future__ import annotations

import json

from pygments.styles import STYLE_MAP as pygments_styles
from upath import UPath

from euporie.core.config import add_setting
from euporie.core.filters import in_mplex

# euporie.core.app.launch


def _euporie_core_launch_app_choices() -> list[str]:
    """List known euporie-apps and their aliases."""
    from euporie.core.__main__ import available_apps
    from euporie.core.app import APP_ALIASES

    return sorted(
        {entry.name for entry in available_apps().values()} - {"launch"}
        | APP_ALIASES.keys()
    )


add_setting(
    name="app",
    group="euporie.core.app.launch",
    flags=["app"],
    type_=str,
    help_="The application to launch",
    choices=_euporie_core_launch_app_choices,
    description="""
        The name of the application to launch.
    """,
)

# euporie.core.app

add_setting(
    name="files",
    group="euporie.core.app.app",
    default=[],
    flags=["files"],
    nargs="*",
    type_=UPath,
    help_="List of file names to open",
    schema={
        "type": "array",
        "items": {
            "description": "File path",
            "type": "string",
        },
    },
    description="""
        A list of file paths to open when euporie is launched.
    """,
)

add_setting(
    name="edit_mode",
    group="euporie.core.app.app",
    flags=["--edit-mode"],
    type_=str,
    choices=["micro", "emacs", "vi"],
    title="Editor key bindings",
    help_="Key-binding mode for text editing",
    default="micro",
    description="""
        Key binding style to use when editing cells.
    """,
)

add_setting(
    name="tab_size",
    group="euporie.core.app.app",
    flags=["--tab-size"],
    type_=int,
    help_="Spaces per indentation level",
    default=4,
    schema={
        "minimum": 1,
    },
    description="""
        The number of spaces to use per indentation level. Should be set to 4.
    """,
)

add_setting(
    name="terminal_polling_interval",
    group="euporie.core.app.app",
    flags=["--terminal-polling-interval"],
    type_=float,
    help_="Time between terminal colour queries",
    default=0.0,
    schema={
        "min": 0.0,
    },
    description="""
        Determine how frequently the terminal should be polled for changes to the
        background / foreground colours. Set to zero to disable terminal polling.
    """,
)

add_setting(
    name="formatters",
    group="euporie.core.app.app",
    flags=["--formatters"],
    type_=json.loads,
    help_="List of external code formatters",
    default=[
        # {"command": ["ruff", "format", "-"], "languages": ["python"]},
        # {"command": ["black", "-"], "languages": ["python"]},
        # {"command": ["isort", "-"], "languages": ["python"]},
    ],
    action="append",
    schema={
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "array",
                    "items": [{"type": "string"}],
                },
                "languages": {
                    "type": "array",
                    "items": [{"type": "string", "unique": True}],
                },
            },
            "required": ["command", "languages"],
        },
    },
    description="""
        An array listing languages and commands of formatters to use for
        reformatting code cells. The command is an array of the command any any
        arguments. Code to be formatted is pass in via the standard input, and
        replaced with the standard output.

        e.g.

        .. code-block:: json

           [
             {"command": ["ruff", "format", "-"], "languages": ["python"]},
             {"command": ["black", "-"], "languages": ["python"]},
             {"command": ["isort", "-"], "languages": ["python"]}
           ]
    """,
)

add_setting(
    name="syntax_highlighting",
    group="euporie.core.app.base",
    flags=["--syntax-highlighting"],
    type_=bool,
    help_="Syntax highlighting",
    default=True,
    description="""
        Enable or disable syntax highlighting in code input fields.
    """,
)

add_setting(
    name="syntax_theme",
    group="euporie.core.app.base",
    flags=["--syntax-theme"],
    type_=str,
    help_="Syntax highlighting theme",
    default="euporie",
    schema={
        # Do not want to print all theme names in `--help` screen as it looks messy
        # so we only add them in the scheme, not as setting choices
        "enum": ["euporie", *pygments_styles.keys()],
    },
    description="""
        The name of the pygments style to use for syntax highlighting.
    """,
)

add_setting(
    name="color_depth",
    group="euporie.core.app.app",
    flags=["--color-depth"],
    type_=int,
    choices=[1, 4, 8, 24],
    default=None,
    help_="The color depth to use",
    description="""
        The number of bits to use to represent colors displayable on the screen.
        If set to None, the supported color depth of the terminal will be detected
        automatically.
    """,
)

add_setting(
    name="multiplexer_passthrough",
    group="euporie.core.app.app",
    flags=["--multiplexer-passthrough"],
    type_=bool,
    help_="Use passthrough from within terminal multiplexers",
    default=False,
    hidden=~in_mplex,
    description="""
        If set and euporie is running inside a terminal multiplexer
        (:program:`screen` or :program:`tmux`), then certain escape sequences
        will be passed-through the multiplexer directly to the terminal.

        This affects things such as terminal color detection and graphics display.

        for tmux, you will also need to ensure that ``allow-passthrough`` is set to
        ``on`` in your :program:`tmux` configuration.

        .. warning::

           Terminal graphics in :program:`tmux` is experimental, and is not
           guaranteed to work. Use at your own risk!

        .. note::
           As of version :command:`tmux` version ``3.4`` sixel graphics are
           supported, which may result in better terminal graphics then using
           multiplexer passthrough.
    """,
)

add_setting(
    name="color_scheme",
    group="euporie.core.app.app",
    flags=["--color-scheme"],
    type_=str,
    choices=["default", "inverse", "light", "dark", "black", "white", "custom"],
    help_="The color scheme to use",
    default="default",
    description="""
        The color scheme to use: `auto` means euporie will try to use your
        terminal's color scheme, `light` means black text on a white background,
        and `dark` means white text on a black background.
    """,
)

add_setting(
    name="custom_background_color",
    group="euporie.core.app.app",
    flags=["--custom-background-color", "--custom-bg-color", "--bg"],
    type_=str,
    help_='Background color for "Custom" color theme',
    default="#073642",
    schema={
        "maxLength": 7,
    },
    description="""
        The hex code of the color to use for the background in the "Custom" color
        scheme.
    """,
)

add_setting(
    name="custom_foreground_color",
    group="euporie.core.app.app",
    flags=["--custom-foreground-color", "--custom-fg-color", "--fg"],
    type_=str,
    help_='Foreground color for "Custom" color theme',
    default="#839496",
    schema={
        "maxLength": 7,
    },
    description="""
        The hex code of the color to use for the foreground in the "Custom" color
        scheme.
    """,
)

add_setting(
    name="accent_color",
    group="euporie.core.app.app",
    flags=["--accent-color"],
    type_=str,
    help_="Accent color to use in the app",
    default="ansiblue",
    description="""
        The hex code of a color to use for the accent color in the application.
    """,
)

add_setting(
    name="custom_styles",
    group="euporie.core.style",
    flags=["--custom-styles"],
    type_=json.loads,
    default={},
    schema={
        "type": "object",
    },
    help_="Additional style settings",
    description="""
        A JSON object mapping style names to prompt-toolkit style values.

        The style keys used in euporie can be found in :py:func:`euporie.core.style.build_style`.

        e.g.:

        .. code-block:: json

           { "cell input prompt":"fg:purple", "cell output prompt": "fg:green" }

    """,
)

add_setting(
    name="key_bindings",
    group="euporie.core.app.app",
    flags=["--key-bindings"],
    type_=json.loads,
    help_="Additional key binding definitions",
    default={},
    schema={
        "type": "object",
    },
    description="""
        A mapping of component names to mappings of command name to key-binding lists.
""",
)

add_setting(
    name="graphics",
    group="euporie.core.app.app",
    flags=["--graphics"],
    choices=["none", "sixel", "kitty", "kitty-unicode", "iterm"],
    type_=str,
    default=None,
    help_="The preferred graphics protocol",
    description="""
        The graphics protocol to use, if supported by the terminal.
        If set to "none", terminal graphics will not be used.
""",
)

add_setting(
    name="force_graphics",
    group="euporie.core.app.app",
    flags=["--force-graphics"],
    type_=bool,
    default=False,
    help_="Force use of specified graphics protocol",
    description="""
        When set to :py:const:`True`, the graphics protocol specified by the
        :option:`graphics` configuration option will be used even if the terminal
        does not support it.

        This is also useful if you want to use graphics in :command:`euporie-hub`.
""",
)

add_setting(
    name="enable_language_servers",
    group="euporie.core.app.app",
    flags=["--enable-language-servers", "--lsp"],
    menu_title="Language servers",
    type_=bool,
    default=False,
    help_="Enable language server support",
    description="""
        When set to :py:const:`True`, language servers will be used for liniting,
        code inspection, and code formatting.

        Additional language servers can be added using the
        :option:`language-servers` option.
""",
)

add_setting(
    name="language_servers",
    group="euporie.core.app.app",
    flags=["--language-servers"],
    type_=json.loads,
    help_="Language server configurations",
    default={},
    schema={
        "type": "object",
        "items": {
            "type": "object",
            "patternProperties": {
                "^[0-9]+$": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "array",
                            "items": [{"type": "string"}],
                        },
                        "language": {
                            "type": "array",
                            "items": [{"type": "string", "unique": True}],
                        },
                    },
                    "required": ["command"],
                }
            },
        },
    },
    description="""
        Additional language servers can be defined here, e.g.:

        .. code-block:: json

           {
            "ruff": {"command": ["ruff-lsp"], "languages": ["python"]},
            "pylsp": {"command": ["pylsp"], "languages": ["python"]},
            "typos": {"command": ["typos-lsp"], "languages": []}
           }

        The following properties are required:
        - The name to be given to the the language server, must be unique
        - The command list consists of the process to launch, followed by any
          command line arguments
        - A list of language the language server supports. If no languages are
        given, the language server will be used for documents of any language.

        To disable one of the default language servers, its name can be set to an
        empty dictionary. For example, the following would disable the awk language
        server:

        .. code-block:: json

           {
             "awk-language-server": {},
           }
    """,
)

# euporie.core.app.cursor

add_setting(
    name="set_cursor_shape",
    group="euporie.core.app.cursor",
    flags=["--set-cursor-shape"],
    type_=bool,
    default=True,
    menu_title="Change cursor shape",
    help_="Whether to set the shape of the cursor depending on the editing mode",
    description="""
        When set to True, the euporie will set the shape of the terminal's cursor
        to a beam in insert mode and and underline in replace mode when editing.
""",
)

add_setting(
    name="cursor_blink",
    group="euporie.core.app.cursor",
    flags=["--cursor-blink"],
    type_=bool,
    default=False,
    help_="Whether to blink the cursor",
    description="""
        When set to True, the cursor will blink.
""",
)


add_setting(
    name="recent_files",
    group="euporie.core.app.app",
    default=[],
    flags=[],
    nargs="*",
    type_=UPath,
    help_="List of recently opened files",
    schema={
        "type": "array",
        "items": {
            "description": "File path",
            "type": "string",
        },
    },
    description="""
        A list of recently opened file paths.
    """,
)
