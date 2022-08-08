.. _cli-euporie-start:

Usage
=====

.. code-block:: console

   $ euporie [-h] [--version] {preview,edit,hub,console,notebook}

Positional Arguments
====================

.. option:: {preview,edit,hub,console,notebook}

   The application to launch

Optional Arguments
==================

.. option:: -h, --help

   show this help message and exit

.. option:: --version, -V

   Show the version number and exit


.. _cli-euporie-end:
.. _cli-euporie-console-start:

Usage
=====

.. code-block:: console

   $ euporie-console [-h] [--version] [--kernel-connection-file str]
                          [--log-file [str]]
                          [--log-level {debug,info,warning,error,critical}]
                          [--log-config str] [--edit-mode {micro,emacs,vi}]
                          [--tab-size int] [--terminal-polling-interval int]
                          [--autoformat | --no-autoformat]
                          [--format-black | --no-format-black]
                          [--format-isort | --no-format-isort]
                          [--format-ssort | --no-format-ssort]
                          [--syntax-theme str] [--color-depth {1,4,8,24}]
                          [--tmux-graphics | --no-tmux-graphics]
                          [--color-scheme {default,inverse,light,dark,black,white,custom}]
                          [--custom-background-color str]
                          [--custom-foreground-color str] [--accent-color str]
                          [--key-bindings loads] [--default-kernel-name str]
                          [--line-numbers | --no-line-numbers]
                          [--autocomplete | --no-autocomplete]
                          [--autosuggest | --no-autosuggest]
                          [--autoinspect | --no-autoinspect]
                          [--max-stored-outputs int]
                          [--show-status-bar | --no-show-status-bar]
                          [--mouse-support | --no-mouse-support]
                          [UPath ...]

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

   Attempt to connect to an existing kernel using a JSON connection info file

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

.. option:: --key-bindings <loads>

   Additional key binding definitions

.. option:: --default-kernel-name <str>

   The name of the kernel to start by default

.. option:: --line-numbers, --no-line-numbers

   Show or hide line numbers

.. option:: --autocomplete, --no-autocomplete

   Provide completions suggestions automatically

.. option:: --autosuggest, --no-autosuggest

   Provide line completion suggestions

.. option:: --autoinspect, --no-autoinspect

   Display contextual help automatically

.. option:: --max-stored-outputs <int>

   The number of inputs / outputs to store in an in-memory notebook

.. option:: --show-status-bar, --no-show-status-bar

   Show the status bar

.. option:: --mouse-support, --no-mouse-support

   Enable or disable mouse support


.. _cli-euporie-console-end:
.. _cli-euporie-hub-start:

Usage
=====

.. code-block:: console

   $ euporie-hub [-h] [--version] [--log-file [str]]
                      [--log-level {debug,info,warning,error,critical}]
                      [--log-config str] [--edit-mode {micro,emacs,vi}]
                      [--tab-size int] [--terminal-polling-interval int]
                      [--autoformat | --no-autoformat]
                      [--format-black | --no-format-black]
                      [--format-isort | --no-format-isort]
                      [--format-ssort | --no-format-ssort] [--syntax-theme str]
                      [--color-depth {1,4,8,24}]
                      [--tmux-graphics | --no-tmux-graphics]
                      [--color-scheme {default,inverse,light,dark,black,white,custom}]
                      [--custom-background-color str]
                      [--custom-foreground-color str] [--accent-color str]
                      [--key-bindings loads] [--app {notebook,console}]
                      [--host str] [--port int] [--host-keys [UPath ...]]
                      [--client-keys [UPath ...]] [--no-auth | --no-no-auth]
                      [UPath ...]

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

.. option:: --key-bindings <loads>

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


.. _cli-euporie-hub-end:
.. _cli-euporie-notebook-start:

Usage
=====

.. code-block:: console

   $ euporie-notebook [-h] [--version] [--log-file [str]]
                           [--log-level {debug,info,warning,error,critical}]
                           [--log-config str] [--edit-mode {micro,emacs,vi}]
                           [--tab-size int] [--terminal-polling-interval int]
                           [--autoformat | --no-autoformat]
                           [--format-black | --no-format-black]
                           [--format-isort | --no-format-isort]
                           [--format-ssort | --no-format-ssort]
                           [--syntax-theme str] [--color-depth {1,4,8,24}]
                           [--tmux-graphics | --no-tmux-graphics]
                           [--color-scheme {default,inverse,light,dark,black,white,custom}]
                           [--custom-background-color str]
                           [--custom-foreground-color str] [--accent-color str]
                           [--key-bindings loads] [--kernel-connection-file str]
                           [--default-kernel-name str]
                           [--show-status-bar | --no-show-status-bar]
                           [--line-numbers | --no-line-numbers]
                           [--autocomplete | --no-autocomplete]
                           [--autosuggest | --no-autosuggest]
                           [--autoinspect | --no-autoinspect]
                           [--show-cell-borders | --no-show-cell-borders]
                           [--record-cell-timing | --no-record-cell-timing]
                           [--save-widget-state | --no-save-widget-state]
                           [--max-notebook-width int] [--expand | --no-expand]
                           [--show-scroll-bar | --no-show-scroll-bar]
                           [--tab-mode {stack,tile_horizontally,tile_vertically}]
                           [--always-show-tab-bar | --no-always-show-tab-bar]
                           [--background-pattern {0,1,2,3,4,5}]
                           [--background-character str]
                           [--run-after-external-edit | --no-run-after-external-edit]
                           [--run | --no-run]
                           [UPath ...]

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

.. option:: --key-bindings <loads>

   Additional key binding definitions

.. option:: --kernel-connection-file <str>

   Attempt to connect to an existing kernel using a JSON connection info file

.. option:: --default-kernel-name <str>

   The name of the kernel to start by default

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


.. _cli-euporie-notebook-end:
.. _cli-euporie-preview-start:

Usage
=====

.. code-block:: console

   $ euporie-preview [-h] [--version] [--log-file [str]]
                          [--log-level {debug,info,warning,error,critical}]
                          [--log-config str] [--edit-mode {micro,emacs,vi}]
                          [--tab-size int] [--terminal-polling-interval int]
                          [--autoformat | --no-autoformat]
                          [--format-black | --no-format-black]
                          [--format-isort | --no-format-isort]
                          [--format-ssort | --no-format-ssort]
                          [--syntax-theme str] [--color-depth {1,4,8,24}]
                          [--tmux-graphics | --no-tmux-graphics]
                          [--color-scheme {default,inverse,light,dark,black,white,custom}]
                          [--custom-background-color str]
                          [--custom-foreground-color str] [--accent-color str]
                          [--key-bindings loads] [--kernel-connection-file str]
                          [--default-kernel-name str]
                          [--line-numbers | --no-line-numbers]
                          [--autocomplete | --no-autocomplete]
                          [--autosuggest | --no-autosuggest]
                          [--autoinspect | --no-autoinspect]
                          [--show-cell-borders | --no-show-cell-borders]
                          [--record-cell-timing | --no-record-cell-timing]
                          [--save-widget-state | --no-save-widget-state]
                          [--max-notebook-width int] [--expand | --no-expand]
                          [--run | --no-run] [--save | --no-save]
                          [--show-filenames | --no-show-filenames]
                          [--cell-start int] [--cell-stop int]
                          [--output-file [UPath]] [--page | --no-page]
                          [UPath ...]

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

.. option:: --key-bindings <loads>

   Additional key binding definitions

.. option:: --kernel-connection-file <str>

   Attempt to connect to an existing kernel using a JSON connection info file

.. option:: --default-kernel-name <str>

   The name of the kernel to start by default

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


.. _cli-euporie-preview-end:
