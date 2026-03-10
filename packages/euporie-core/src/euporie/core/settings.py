"""Core settings definitions."""

from __future__ import annotations

import json
from pkgutil import resolve_name

from apptk.application.current import get_app
from apptk.enums import EditingMode
from apptk.filters.app import buffer_has_focus, is_read_only
from apptk.filters.environment import in_mplex
from apptk.output.color_depth import ColorDepth
from euporie.core import __version__
from euporie.core.app.current import available_apps
from euporie.core.config._setting import Setting
from euporie.core.filters import tab_type_has_focus
from pygments.styles import STYLE_MAP as pygments_styles
from upath import UPath

# App

app = Setting(
    name="app",
    flags=["app"],
    type_=str,
    transform=resolve_name,
    help_="The application to launch",
    choices=available_apps,
    description="""
        The name of the application to launch.
    """,
)

# Version

version = Setting(
    name="version",
    default=False,
    flags=["--version", "-V"],
    action="version",
    hidden=True,
    version=f"%(prog)s {__version__}",
    help_="Show the version number and exit",
    description="""
        If set, euporie will print the current version number of the application
        and exit. All other configuration options will be ignored.

        .. note::

           This cannot be set in the configuration file or via an environment
           variable
    """,
)

# Logging

log_file = Setting(
    name="log_file",
    flags=["--log-file"],
    nargs="?",
    default="",
    type_=str,
    title="the log file path",
    help_="File path for logs",
    description="""
        When set to a file path, the log output will be written to the given path.
        If no value is given output will be sent to the standard output.
    """,
)

log_level = Setting(
    name="log_level",
    type_=str,
    default="warning",
    title="the log level",
    help_="Set the log level",
    choices=["debug", "info", "warning", "error", "critical"],
    description="""
        When set, logging events at the given level are emitted.
    """,
)

log_level_stdout = Setting(
    name="log_level_stdout",
    hidden=True,
    type_=str,
    default="critical",
    title="the log level at which to log to standard output",
    help_="Set the log level printed to standard out",
    choices=["debug", "info", "warning", "error", "critical"],
    description="""
        When set, logging events at the given level are printed to the standard
        output.
    """,
)

log_config = Setting(
    name="log_config",
    flags=["--log-config"],
    type_=json.loads,
    default={},
    schema={
        "type": "object",
    },
    title="additional logging configuration",
    help_="Additional logging configuration",
    description="""
        A JSON string specifying additional logging configuration.
    """,
)

# Files

files = Setting(
    name="files",
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

backup_on_save = Setting(
    name="backup_on_save",
    flags=["--backup-on-save"],
    type_=bool,
    help_="Create backups before saving files",
    default=False,
    description="""
        Determines whether a backup file should be created before saving a file.

        If set to ``True``, the original file will be copied to a new file with the
        same name but prefixed with ``.`` and suffixed with ``.bak`` before writing
        the updated contents.
    """,
)

# Editor

edit_mode = Setting(
    name="edit_mode",
    flags=["--edit-mode"],
    type_=EditingMode,
    choices={
        "micro": EditingMode.MICRO,
        "emacs": EditingMode.EMACS,
        "vi": EditingMode.VI,
        "helix": EditingMode.HELIX,
    },
    schema={"type": "string"},
    title="Editor key bindings",
    help_="Key-binding mode for text editing",
    default="micro",
    description="""
        Key binding style to use when editing cells.
    """,
)

tab_size = Setting(
    name="tab_size",
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

formatters = Setting(
    name="formatters",
    flags=["--formatters"],
    type_=json.loads,
    help_="List of external code formatters",
    default=[],
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

line_numbers = Setting(
    name="line_numbers",
    flags=["--line-numbers"],
    type_=bool,
    help_="Show or hide line numbers",
    default=True,
    description="""
        Whether line numbers are shown by default.
    """,
    hooks=[lambda x: get_app().refresh()],
    keys=["l"],
    filter=~buffer_has_focus | (buffer_has_focus & is_read_only),
)

relative_line_numbers = Setting(
    name="relative_line_numbers",
    type_=bool,
    help_="Use relative line numbers",
    default=False,
    description="""
        When set to ``True``, line numbers will be displayed relative to the
        current cursor line.
    """,
    hooks=[lambda x: get_app().refresh()],
)

autoformat = Setting(
    name="autoformat",
    flags=["--autoformat"],
    type_=bool,
    help_="Automatically re-format code cells when run",
    default=False,
    description="""
        Whether to automatically reformat code cells before they are run.
    """,
)

autocomplete = Setting(
    name="autocomplete",
    flags=["--autocomplete"],
    type_=bool,
    help_="Provide completions suggestions automatically",
    default=False,
    description="""
        Whether to automatically suggestion completions while typing in code cells.
    """,
)

autosuggest = Setting(
    name="autosuggest",
    flags=["--autosuggest"],
    type_=str,
    choices=["smart", "simple", "none"],
    help_="Provide line completion suggestions",
    default="smart",
    description="""
        Whether to automatically suggestion line content while typing in code cells.
    """,
)

autoinspect = Setting(
    name="autoinspect",
    flags=["--autoinspect"],
    type_=bool,
    help_="Display contextual help automatically",
    default=False,
    description="""
        Whether to automatically display contextual help when navigating through
        code cells.
    """,
)

external_editor = Setting(
    name="external_editor",
    flags=["--external-editor"],
    type_=str,
    help_="Set the external editor to use.",
    default=None,
    description="""
        A command to run when editing cells externally. The following strings in
        the command will be replaced with values which locate the cell being
        edited:

        * ``{top}``
        * ``{left}``
        * ``{bottom}``
        * ``{right}``
        * ``{width}``
        * ``{height}``

        This is useful if you run euporie inside a tmux session, and wish to launch
        your editor in a pop-up pane. This can be achieved by setting this parameter
        to something like the following:

        .. code-block::

           "tmux display-popup -x {left} -y {bottom} -w {width} -h {height} -B -E micro"

    """,
)

clipboard = Setting(
    name="clipboard",
    flags=["--clipboard"],
    choices={
        "external": "apptk.clipboard.pyperclip:PyperclipClipboard",
        "internal": "apptk.clipboard.in_memory:InMemoryClipboard",
        "terminal": "apptk.clipboard.osc52:Osc52Clipboard",
    },
    type_=str,
    transform=resolve_name,
    default="external",
    help_="The preferred clipboard access method",
    description="""
        The clipboard access method to use.
        - ``external``: Data is saved to the system clipboard using OS native
          tooling.
        - ``internal``: Clipboard data is only stored and usable inside euporie -
          it is not saved to the system clipboard.
        - ``terminal``: uses OSC52 escape sequences to retrieve and set the
          clipboard contents. Requires your terminal emulator to support OSC52.
          Works over SSH.

    """,
)

key_bindings = Setting(
    name="key_bindings",
    flags=["--key-bindings"],
    type_=json.loads,
    help_="Additional key binding definitions",
    default={},
    schema={
        "type": "object",
    },
    description="""
        A mapping of component names to mappings of command name to key-binding
        lists.
    """,
)

set_cursor_shape = Setting(
    name="set_cursor_shape",
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

cursor_blink = Setting(
    name="cursor_blink",
    flags=["--cursor-blink"],
    type_=bool,
    default=False,
    help_="Whether to blink the cursor",
    description="""
        When set to True, the cursor will blink.
    """,
)

enable_language_servers = Setting(
    name="enable_language_servers",
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

language_servers = Setting(
    name="language_servers",
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

# Terminal

terminal_polling_interval = Setting(
    name="terminal_polling_interval",
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

color_depth = Setting(
    name="color_depth",
    flags=["--color-depth"],
    type_=int,
    choices={
        1: ColorDepth.DEPTH_1_BIT,
        4: ColorDepth.DEPTH_4_BIT,
        8: ColorDepth.DEPTH_8_BIT,
        24: ColorDepth.DEPTH_24_BIT,
    },
    default=None,
    help_="The color depth to use",
    description="""
        The number of bits to use to represent colors displayable on the screen.
        If set to None, the supported color depth of the terminal will be detected
        automatically.
    """,
)

multiplexer_passthrough = Setting(
    name="multiplexer_passthrough",
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

graphics = Setting(
    name="graphics",
    flags=["--graphics"],
    choices={
        "auto": None,
        "sixel": "apptk.layout.graphics:SixelGraphicControl",
        "kitty": "apptk.layout.graphics:KittyGraphicControl",
        "kitty-unicode": "apptk.layout.graphics:KittyUnicodeGraphicControl",
        "iterm": "apptk.layout.graphics:ItermGraphicControl",
        "none": "apptk.layout.graphics:DisabledGraphicControl",
    },
    type_=str,
    transform=resolve_name,
    default="auto",
    help_="The preferred graphics protocol",
    description="""
        The graphics protocol to use, if supported by the terminal.
        If set to ``none``, terminal graphics will not be used.
        If set to ``auto``, euporie will detect the best protocol to use
        automatically.
    """,
)

force_graphics = Setting(
    name="force_graphics",
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

# Appearance

syntax_highlighting = Setting(
    name="syntax_highlighting",
    flags=["--syntax-highlighting"],
    type_=bool,
    help_="Syntax highlighting",
    default=True,
    description="""
        Enable or disable syntax highlighting in code input fields.
    """,
)

syntax_theme = Setting(
    name="syntax_theme",
    flags=["--syntax-theme"],
    type_=str,
    help_="Syntax highlighting theme",
    default="euporie",
    schema={
        "enum": ["euporie", *pygments_styles.keys()],
    },
    description="""
        The name of the pygments style to use for syntax highlighting.
    """,
)

color_scheme = Setting(
    name="color_scheme",
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

custom_background_color = Setting(
    name="custom_background_color",
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

custom_foreground_color = Setting(
    name="custom_foreground_color",
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

accent_color = Setting(
    name="accent_color",
    flags=["--accent-color"],
    type_=str,
    help_="Accent color to use in the app",
    default="ansiblue",
    description="""
        The hex code of a color to use for the accent color in the application.
    """,
)

custom_styles = Setting(
    name="custom_styles",
    flags=["--custom-styles"],
    type_=json.loads,
    default={},
    schema={
        "type": "object",
    },
    help_="Additional style settings",
    description="""
        A JSON object mapping style names to prompt-toolkit style values.

        The style keys used in euporie can be found in
        :py:func:`euporie.core.style.build_style`.

        e.g.:

        .. code-block:: json

           { "cell input prompt":"fg:purple", "cell output prompt": "fg:green" }

    """,
)

show_status_bar = Setting(
    name="show_status_bar",
    flags=["--show-status-bar"],
    type_=bool,
    title="status bar",
    help_="Show the status bar",
    default=True,
    schema={
        "type": "boolean",
    },
    description="""
        Whether the status bar should be shown at the bottom of the screen.
    """,
)

show_shadows = Setting(
    name="show_shadows",
    flags=["--show-shadows"],
    type_=bool,
    help_="Show or hide shadows under menus and dialogs",
    default=True,
    description="""
        Sets whether shadows are shown under dialogs and popup-menus.
    """,
)

# Kernel

kernel_name = Setting(
    name="kernel_name",
    flags=["--kernel-name", "--kernel"],
    type_=str,
    help_="The name of the kernel to start by default",
    default="python3",
    description="""
        The name of the kernel selected automatically by the console app or in new
        notebooks. If set to an empty string, the user will be asked which kernel
        to launch.
    """,
)

record_cell_timing = Setting(
    name="record_cell_timing",
    title="cell timing recording",
    flags=["--record-cell-timing"],
    type_=bool,
    help_="Should timing data be recorded in cell metadata.",
    default=False,
    schema={
        "type": "boolean",
    },
    description="""
        When set, execution timing data will be recorded in cell metadata.
    """,
)

show_remote_inputs = Setting(
    name="show_remote_inputs",
    flags=["--show-remote-inputs"],
    type_=bool,
    help_="Display inputs sent to the kernel by other clients",
    default=True,
    description="""
        If set to `True`, all code input sent to the kernel by any client will be
        displayed.

        If set to `False`, only inputs sent to the kernel by the current instance
        of euporie will be displayed, and all other inputs will be ignored.

    """,
)

show_remote_outputs = Setting(
    name="show_remote_outputs",
    flags=["--show-remote-outputs"],
    type_=bool,
    help_="Display kernel outputs triggered by other clients",
    default=True,
    description="""
        If set to `False`, only outputs generated by code input from the current
        instance of euporie will be displayed, and all other outputs will be
        ignored.

        If set to `True`, all outputs generated by the kernel will be
        displayed.
    """,
)

warn_venv = Setting(
    name="warn_venv",
    flags=["--warn-venv"],
    type_=bool,
    default=True,
    help_="Warn when running in a virtual environment",
    description="""
        When enabled, displays a warning message when the kernel is running inside
        a virtual environment.

        This can be helpful to remind users that they are working in an isolated
        Python environment with potentially different package versions than their
        system Python installation.

        Disable this setting if you prefer not to see these warnings.
    """,
)

# Cells

wrap_cell_outputs = Setting(
    name="wrap_cell_outputs",
    title="wrap cell outputs",
    flags=["--wrap-cell-outputs"],
    type_=bool,
    help_="Wrap cell output text.",
    default=True,
    schema={"type": "boolean"},
    description="""
        Whether text-based cell outputs should be wrapped.
    """,
    filter=(
        ~buffer_has_focus
        & tab_type_has_focus("euporie.notebook.tabs.notebook:Notebook")
    )
    | ~tab_type_has_focus("euporie.notebook.tabs.notebook:Notebook"),
    keys=["W"],
)

text_output_limit = Setting(
    name="text_output_limit",
    flags=["--text-output-limit"],
    type_=int,
    help_="Limit the amount of cell text output",
    default=1_000_000,
    schema={
        "minimum": 0,
    },
    description="""
        Limit the number of text characters in interactive cell text output to
        this value. Use ``0`` to allow any amount of characters.
    """,
)

show_cell_borders = Setting(
    name="show_cell_borders",
    title="cell borders",
    flags=["--show-cell-borders"],
    type_=bool,
    help_="Show or hide cell borders.",
    default=False,
    schema={
        "type": "boolean",
    },
    description="""
        Whether cell borders should be drawn for unselected cells.
    """,
)

save_widget_state = Setting(
    name="save_widget_state",
    flags=["--save-widget-state"],
    type_=bool,
    help_="Save a notebook's widget state in the notebook metadata",
    default=True,
    description="""
        When set to ``True``, the state of any widgets in the current notebook will
        be saves in the notebook's metadata. This enables widgets to be displayed
        when the notebook is re-opened without having to re-run the notebook.
    """,
)

# File Manager

show_icons = Setting(
    name="show_icons",
    flags=["--show-icons"],
    type_=bool,
    title="Icons",
    help_="Show icons throughout the UI",
    default=False,
    schema={
        "type": "boolean",
    },
    description="""
        Whether icons should be shown throughout the UI, including menus, tabs,
        the status bar, and the file manager.

        These icons exist in the unicode private use area, and may require custom
        fonts such as ``awesome-terminal-fonts`` or ``nerdfonts`` to be installed.
    """,
    hooks=[lambda x: get_app().refresh()],
)

show_hidden_files = Setting(
    name="show_hidden_files",
    flags=["--show-hidden-files"],
    type_=bool,
    title="Hidden files",
    help_="Show hidden files in the file manager",
    default=False,
    schema={
        "type": "boolean",
    },
    description="""
        Whether files and directories starting with a dot should be shown
        in the file manager.
    """,
)

# States

recent_files = Setting(
    name="recent_files",
    group="euporie.core.app.app",
    default=[],
    flags=[],
    nargs="*",
    type_=str,
    transform=UPath,
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

max_notebook_width = Setting(
    name="max_notebook_width",
    flags=["--max-notebook-width"],
    type_=int,
    help_="Maximum width of notebooks",
    default=120,
    schema={
        "minimum": 1,
    },
    description="""
        The maximum width at which to display a notebook.
    """,
)

expand = Setting(
    name="expand",
    flags=["--expand"],
    type_=bool,
    help_="Use the full width to display notebooks",
    default=False,
    description="""
        Whether the notebook page should expand to fill the available width
    """,
    filter=~buffer_has_focus,
    keys=["w"],
)
