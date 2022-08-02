
----

******************
:command:`euporie`
******************

Launch a euporie application.

Positional Arguments
====================

.. option:: {console,core,hub,notebook,preview}

   The application to launch

Optional Arguments
==================

.. option:: -h, --help

   show this help message and exit

.. option:: --version, -V

   Show the version number and exit



----

**************************
:command:`euporie-console`
**************************

Console app.

An interactive console which connects to Jupyter kernels and displays
rich output in the terminal.



Positional Arguments
====================

.. option:: <UPath> ...

   List of file names to open

Optional Arguments
==================

.. option:: -h, --help

   show this help message and exit

.. option:: --version, -V

   Show the version number and exit

.. option:: --kernel-connection-file <str>

   Attempt to connect to an existing kernel using a JSON connection info file.

.. option:: --default-kernel-name <str>

   The name of the kernel to start by default.

.. option:: --log-file <str>

   File path for logs

.. option:: --log-level {debug,info,warning,error,critical}

   Set the log level

.. option:: --log-config <str>

   Additional logging configuration

.. option:: --edit-mode {micro,emacs,vi}

   Key-binding mode for text editing

.. option:: --tab-size <int>

   Spaces per indentation level

.. option:: --terminal-polling-interval <int>

   Time between terminal colour queries

.. option:: --autoformat, --no-autoformat

   Automatically re-format code cells when run

.. option:: --format-black, --no-format-black

   Use black when re-formatting code cells

.. option:: --format-isort, --no-format-isort

   Use isort when re-formatting code cells

.. option:: --format-ssort, --no-format-ssort

   Use ssort when re-formatting code cells

.. option:: --syntax-theme <str>

   Syntax highlighting theme

.. option:: --color-depth {1,4,8,24}

   The color depth to use

.. option:: --tmux-graphics, --no-tmux-graphics

   Enable terminal graphics in tmux (experimental)

.. option:: --color-scheme {default,inverse,light,dark,black,white,custom}

   The color scheme to use

.. option:: --custom-background-color <str>, --custom-bg-color <str>, --bg <str>

   Background color for "Custom" color theme

.. option:: --custom-foreground-color <str>, --custom-fg-color <str>, --fg <str>

   Background color for "Custom" color theme

.. option:: --accent-color <str>

   Accent color to use in the app

.. option:: --key-bindings <dict>

   Additional key binding definitions

.. option:: --line-numbers, --no-line-numbers

   Show or hide line numbers

.. option:: --autocomplete, --no-autocomplete

   Provide completions suggestions automatically

.. option:: --autosuggest, --no-autosuggest

   Provide line completion suggestions

.. option:: --autoinspect, --no-autoinspect

   Display contextual help automatically

.. option:: --show-status-bar, --no-show-status-bar

   Show the status bar



----

**********************
:command:`euporie-hub`
**********************

Hub App.

An app which runs as a multi-user SSH server.

This app never actually gets run, but is used to run another app in an SSH server.


Positional Arguments
====================

.. option:: <UPath> ...

   List of file names to open

Optional Arguments
==================

.. option:: -h, --help

   show this help message and exit

.. option:: --version, -V

   Show the version number and exit

.. option:: --log-file <str>

   File path for logs

.. option:: --log-level {debug,info,warning,error,critical}

   Set the log level

.. option:: --log-config <str>

   Additional logging configuration

.. option:: --edit-mode {micro,emacs,vi}

   Key-binding mode for text editing

.. option:: --tab-size <int>

   Spaces per indentation level

.. option:: --terminal-polling-interval <int>

   Time between terminal colour queries

.. option:: --autoformat, --no-autoformat

   Automatically re-format code cells when run

.. option:: --format-black, --no-format-black

   Use black when re-formatting code cells

.. option:: --format-isort, --no-format-isort

   Use isort when re-formatting code cells

.. option:: --format-ssort, --no-format-ssort

   Use ssort when re-formatting code cells

.. option:: --syntax-theme <str>

   Syntax highlighting theme

.. option:: --color-depth {1,4,8,24}

   The color depth to use

.. option:: --tmux-graphics, --no-tmux-graphics

   Enable terminal graphics in tmux (experimental)

.. option:: --color-scheme {default,inverse,light,dark,black,white,custom}

   The color scheme to use

.. option:: --custom-background-color <str>, --custom-bg-color <str>, --bg <str>

   Background color for "Custom" color theme

.. option:: --custom-foreground-color <str>, --custom-fg-color <str>, --fg <str>

   Background color for "Custom" color theme

.. option:: --accent-color <str>

   Accent color to use in the app

.. option:: --key-bindings <dict>

   Additional key binding definitions

.. option:: --app {notebook,console}

   App to run under euporie hub

.. option:: --host <str>

   The host address to bind to

.. option:: --port <int>

   The port for the ssh server to use

.. option:: --host-keys <UPath> ...

   Host keys to use for the SSH server

.. option:: --client-keys <UPath> ...

   Client public keys authorized to connect

.. option:: --no-auth, --no-no-auth

   Allow unauthenticated access to euporie hub



----

***************************
:command:`euporie-notebook`
***************************

Notebook app.

Interactively edit a notebook file.

Launches the interactive TUI notebook editor, allowing you to run and edit Jupyter
notebooks in the terminal.


Positional Arguments
====================

.. option:: <UPath> ...

   List of file names to open

Optional Arguments
==================

.. option:: -h, --help

   show this help message and exit

.. option:: --version, -V

   Show the version number and exit

.. option:: --log-file <str>

   File path for logs

.. option:: --log-level {debug,info,warning,error,critical}

   Set the log level

.. option:: --log-config <str>

   Additional logging configuration

.. option:: --edit-mode {micro,emacs,vi}

   Key-binding mode for text editing

.. option:: --tab-size <int>

   Spaces per indentation level

.. option:: --terminal-polling-interval <int>

   Time between terminal colour queries

.. option:: --autoformat, --no-autoformat

   Automatically re-format code cells when run

.. option:: --format-black, --no-format-black

   Use black when re-formatting code cells

.. option:: --format-isort, --no-format-isort

   Use isort when re-formatting code cells

.. option:: --format-ssort, --no-format-ssort

   Use ssort when re-formatting code cells

.. option:: --syntax-theme <str>

   Syntax highlighting theme

.. option:: --color-depth {1,4,8,24}

   The color depth to use

.. option:: --tmux-graphics, --no-tmux-graphics

   Enable terminal graphics in tmux (experimental)

.. option:: --color-scheme {default,inverse,light,dark,black,white,custom}

   The color scheme to use

.. option:: --custom-background-color <str>, --custom-bg-color <str>, --bg <str>

   Background color for "Custom" color theme

.. option:: --custom-foreground-color <str>, --custom-fg-color <str>, --fg <str>

   Background color for "Custom" color theme

.. option:: --accent-color <str>

   Accent color to use in the app

.. option:: --key-bindings <dict>

   Additional key binding definitions

.. option:: --kernel-connection-file <str>

   Attempt to connect to an existing kernel using a JSON connection info file.

.. option:: --default-kernel-name <str>

   The name of the kernel to start by default.

.. option:: --show-status-bar, --no-show-status-bar

   Show the status bar

.. option:: --line-numbers, --no-line-numbers

   Show or hide line numbers

.. option:: --autocomplete, --no-autocomplete

   Provide completions suggestions automatically

.. option:: --autosuggest, --no-autosuggest

   Provide line completion suggestions

.. option:: --autoinspect, --no-autoinspect

   Display contextual help automatically

.. option:: --show-cell-borders, --no-show-cell-borders

   Show or hide cell borders.

.. option:: --record-cell-timing, --no-record-cell-timing

   Should timing data be recorded in cell metadata.

.. option:: --save-widget-state, --no-save-widget-state

   Save a notebook's widget state in the notebook metadata

.. option:: --max-notebook-width <int>

   Maximum width of notebooks

.. option:: --expand, --no-expand

   Use the full width to display notebooks

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

.. option:: --run-after-external-edit, --no-run-after-external-edit

   Run cells after editing externally

.. option:: --run, --no-run

   Run the notebook files when loaded



----

**************************
:command:`euporie-preview`
**************************

Preview app.

Preview notebook files in the terminal.

Outputs a formatted notebook file. The formatted output will be written to
the the output file path given by `output_file` (the standard output by
default).



Positional Arguments
====================

.. option:: <UPath> ...

   List of file names to open

Optional Arguments
==================

.. option:: -h, --help

   show this help message and exit

.. option:: --version, -V

   Show the version number and exit

.. option:: --log-file <str>

   File path for logs

.. option:: --log-level {debug,info,warning,error,critical}

   Set the log level

.. option:: --log-config <str>

   Additional logging configuration

.. option:: --edit-mode {micro,emacs,vi}

   Key-binding mode for text editing

.. option:: --tab-size <int>

   Spaces per indentation level

.. option:: --terminal-polling-interval <int>

   Time between terminal colour queries

.. option:: --autoformat, --no-autoformat

   Automatically re-format code cells when run

.. option:: --format-black, --no-format-black

   Use black when re-formatting code cells

.. option:: --format-isort, --no-format-isort

   Use isort when re-formatting code cells

.. option:: --format-ssort, --no-format-ssort

   Use ssort when re-formatting code cells

.. option:: --syntax-theme <str>

   Syntax highlighting theme

.. option:: --color-depth {1,4,8,24}

   The color depth to use

.. option:: --tmux-graphics, --no-tmux-graphics

   Enable terminal graphics in tmux (experimental)

.. option:: --color-scheme {default,inverse,light,dark,black,white,custom}

   The color scheme to use

.. option:: --custom-background-color <str>, --custom-bg-color <str>, --bg <str>

   Background color for "Custom" color theme

.. option:: --custom-foreground-color <str>, --custom-fg-color <str>, --fg <str>

   Background color for "Custom" color theme

.. option:: --accent-color <str>

   Accent color to use in the app

.. option:: --key-bindings <dict>

   Additional key binding definitions

.. option:: --kernel-connection-file <str>

   Attempt to connect to an existing kernel using a JSON connection info file.

.. option:: --default-kernel-name <str>

   The name of the kernel to start by default.

.. option:: --line-numbers, --no-line-numbers

   Show or hide line numbers

.. option:: --autocomplete, --no-autocomplete

   Provide completions suggestions automatically

.. option:: --autosuggest, --no-autosuggest

   Provide line completion suggestions

.. option:: --autoinspect, --no-autoinspect

   Display contextual help automatically

.. option:: --show-cell-borders, --no-show-cell-borders

   Show or hide cell borders.

.. option:: --record-cell-timing, --no-record-cell-timing

   Should timing data be recorded in cell metadata.

.. option:: --save-widget-state, --no-save-widget-state

   Save a notebook's widget state in the notebook metadata

.. option:: --max-notebook-width <int>

   Maximum width of notebooks

.. option:: --expand, --no-expand

   Use the full width to display notebooks

.. option:: --run, --no-run

   Run the notebook files when loaded

.. option:: --save, --no-save

   Save the notebook after running it

.. option:: --show-filenames, --no-show-filenames

   Show the notebook filenames when previewing multiple notebooks

.. option:: --cell-start <int>

   The first cell to include in the preview

.. option:: --cell-stop <int>

   The last cell to include in the preview

.. option:: --output-file <UPath>

   Output path when previewing file

.. option:: --page, --no-page

   Pass output to pager
