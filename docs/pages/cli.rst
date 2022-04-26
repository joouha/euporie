######################
Command Line Interface
######################

This page list all of the available command line flags for the :command:`euporie` command.

.. _cli-start:

----

**************
Global Options
**************

These options affect all subcommands.

.. note::

   They must be specified before a subcommand on the command line


Positional Arguments
====================

.. option:: {edit,preview,hub}

   The name of a subcommand to launch

Optional Arguments
==================

.. option:: -h, --help

   show this help message and exit

.. option:: --version, -V

   Show the version number and exit

.. option:: --log-file <str>

   File path for logs

.. option:: --debug, --no-debug

   Include debug output in logs


----

*************************
:option:`edit` subcommand
*************************

Launches the interactive TUI notebook editor, allowing you to run and edit
Jupyter notebooks in the terminal.

Positional Arguments
====================

.. option:: <Path> ...

   List of file names to open

Optional Arguments
==================

.. option:: -h, --help

   show this help message and exit

.. option:: --edit-mode {micro,emacs,vi}

   Key-binding mode for text editing

.. option:: --tab-size <int>

   Spaces per indentation level

.. option:: --show-cell-borders, --no-show-cell-borders

   Show or hide cell borders.

.. option:: --line-numbers, --no-line-numbers

   Show or hide line numbers

.. option:: --show-status-bar, --no-show-status-bar

   Show the status bar

.. option:: --show-scroll-bar, --no-show-scroll-bar

   Show the scroll bar

.. option:: --tab-mode {stack,tile_horizontally,tile_vertically}

   The method used to display multiple tabs

.. option:: --always-show-tab-bar, --no-always-show-tab-bar

   Always show the tab bar

.. option:: --background-pattern {0,1,2,3,4,5}, --bg-pattern {0,1,2,3,4,5}

   The background pattern to use

.. option:: --background-character <str>, --bg-char <str>

   Character for background pattern

.. option:: --terminal-polling-interval <int>

   Time between terminal colour queries

.. option:: --autocomplete, --no-autocomplete

   Provide completions suggestions automatically

.. option:: --autosuggest, --no-autosuggest

   Provide line completion suggestions

.. option:: --autoinspect, --no-autoinspect

   Display contextual help automatically

.. option:: --run-after-external-edit

   Run cells after editing externally

.. option:: --autoformat, --no-autoformat

   Automatically re-format code cells when run

.. option:: --format-black, --no-format-black

   Use black when re-formatting code cells

.. option:: --format-isort, --no-format-isort

   Use isort when re-formatting code cells

.. option:: --format-ssort, --no-format-ssort

   Use ssort when re-formatting code cells

.. option:: --run, --no-run

   Run the notebook when loaded

.. option:: --expand, --no-expand

   Use the full width to display notebooks

.. option:: --max-notebook-width <int>

   Maximum width of notebooks

.. option:: --tmux-graphics, --no-tmux-graphics

   Enable terminal graphics in tmux (experimental)

.. option:: --color-scheme {default,inverse,light,dark,black,white,custom}

   The color scheme to use

.. option:: --custom-background-color <str>, --custom-bg-color <str>, --bg <str>

   Background color for "Custom" color theme

.. option:: --custom-foreground-color <str>, --custom-fg-color <str>, --fg <str>

   Background color for "Custom" color theme

.. option:: --syntax-theme <str>

   Syntax highlighting theme

.. option:: --color-depth {1,4,8,24}

   The color depth to use


----

****************************
:option:`preview` subcommand
****************************

Outputs a formatted notebook file. The formatted output will be written to
the the output file path given by `output_file` (the standard output by
default).

Positional Arguments
====================

.. option:: <Path> ...

   List of file names to open

Optional Arguments
==================

.. option:: -h, --help

   show this help message and exit

.. option:: --output-file <Path>

   Output path when previewing file

.. option:: --page, --no-page

   Pass output to pager

.. option:: --run, --no-run

   Run the notebook when loaded

.. option:: --expand, --no-expand

   Use the full width to display notebooks

.. option:: --max-notebook-width <int>

   Maximum width of notebooks

.. option:: --tmux-graphics, --no-tmux-graphics

   Enable terminal graphics in tmux (experimental)

.. option:: --color-scheme {default,inverse,light,dark,black,white,custom}

   The color scheme to use

.. option:: --custom-background-color <str>, --custom-bg-color <str>, --bg <str>

   Background color for "Custom" color theme

.. option:: --custom-foreground-color <str>, --custom-fg-color <str>, --fg <str>

   Background color for "Custom" color theme

.. option:: --syntax-theme <str>

   Syntax highlighting theme

.. option:: --color-depth {1,4,8,24}

   The color depth to use


----

************************
:option:`hub` subcommand
************************

Launches euporie hub, a multi-client SSH server running euporie, which
launches an instance of the TUI editor for each connected user.

Positional Arguments
====================

.. option:: <Path> ...

   List of file names to open

Optional Arguments
==================

.. option:: -h, --help

   show this help message and exit

.. option:: --host <str>

   The host address to bind to

.. option:: --port <int>

   The port for the ssh server to use

.. option:: --host-keys <Path> ...

   Host keys to use for the SSH server

.. option:: --client-keys <Path> ...

   Client public keys authorized to connect

.. option:: --no-auth, --no-no-auth

   Allow unauthenticated access to euporie hub

.. _cli-end:
