.. option:: version

:flags: :option:`--version` or :option:`-V`

:default: ``False``
:type: :keyword:`boolean`
:description: Show the version number and exit

   If set, euporie will print the current version number of the application and exit.
   All other configuration options will be ignored.

   .. note::
   This cannot be set in the configuration file or via an environment variable


.. option:: kernel_connection_file

:flags: :option:`--kernel-connection-file`

:environment variable: :envvar:`EUPORIE_KERNEL_CONNECTION_FILE`
:default: ``''``
:type: :keyword:`string`
:description: Attempt to connect to an existing kernel using a JSON connection info file.

   Load connection info from JSON dict. This allows euporie to connect to
   existing kernels.


.. option:: default_kernel_name

:flags: :option:`--default-kernel-name`

:environment variable: :envvar:`EUPORIE_DEFAULT_KERNEL_NAME`
:default: ``'python3'``
:type: :keyword:`string`
:description: The name of the kernel to start by default.

   The name of the kernel selected automatically by the console app or in new
   notebooks. If set to an empty string, the user will be asked which kernel
   to launch.


.. option:: files


:environment variable: :envvar:`EUPORIE_FILES`
:default: ``[]``
:type: :keyword:`array`
:description: List of file names to open

   A list of file paths to open when euporie is launched.


.. option:: log_file

:flags: :option:`--log-file`

:environment variable: :envvar:`EUPORIE_LOG_FILE`
:default: ``''``
:type: :keyword:`string`
:description: File path for logs

   When set to a file path, the log output will be written to the given path.
   If no value is given output will be sent to the standard output.


.. option:: log_level

:flags: :option:`--log-level`

:environment variable: :envvar:`EUPORIE_LOG_LEVEL`
:default: ``''``
:type: :keyword:`string`
:options: [``'debug'``, ``'info'``, ``'warning'``, ``'error'``, ``'critical'``]
:description: Set the log level

   When set, logging events at the given level are emitted.


.. option:: log_config

:flags: :option:`--log-config`

:environment variable: :envvar:`EUPORIE_LOG_CONFIG`
:type: :keyword:`string`
:description: Additional logging configuration

   A JSON string specifying additional logging configuration.


.. option:: edit_mode

:flags: :option:`--edit-mode`

:environment variable: :envvar:`EUPORIE_EDIT_MODE`
:default: ``'micro'``
:type: :keyword:`string`
:options: [``'micro'``, ``'emacs'``, ``'vi'``]
:description: Key-binding mode for text editing

   Key binding style to use when editing cells.


.. option:: tab_size

:flags: :option:`--tab-size`

:environment variable: :envvar:`EUPORIE_TAB_SIZE`
:default: ``4``
:type: :keyword:`integer`
:description: Spaces per indentation level

   The number of spaces to use per indentation level. Should be set to 4.


.. option:: terminal_polling_interval

:flags: :option:`--terminal-polling-interval`

:environment variable: :envvar:`EUPORIE_TERMINAL_POLLING_INTERVAL`
:default: ``0``
:type: :keyword:`integer`
:description: Time between terminal colour queries

   Determine how frequently the terminal should be polled for changes to the
   background / foreground colours. Set to zero to disable terminal polling.


.. option:: autoformat

:flags: :option:`--autoformat`

:environment variable: :envvar:`EUPORIE_AUTOFORMAT`
:default: ``False``
:type: :keyword:`boolean`
:description: Automatically re-format code cells when run

   Whether to automatically reformat code cells before they are run.


.. option:: format_black

:flags: :option:`--format-black`

:environment variable: :envvar:`EUPORIE_FORMAT_BLACK`
:default: ``False``
:type: :keyword:`boolean`
:description: Use black when re-formatting code cells

   Whether to use :py:mod:`black` when reformatting code cells.


.. option:: format_isort

:flags: :option:`--format-isort`

:environment variable: :envvar:`EUPORIE_FORMAT_ISORT`
:default: ``False``
:type: :keyword:`boolean`
:description: Use isort when re-formatting code cells

   Whether to use :py:mod:`isort` when reformatting code cells.


.. option:: format_ssort

:flags: :option:`--format-ssort`

:environment variable: :envvar:`EUPORIE_FORMAT_SSORT`
:default: ``False``
:type: :keyword:`boolean`
:description: Use ssort when re-formatting code cells

   Whether to use :py:mod:`ssort` when reformatting code cells.


.. option:: syntax_theme

:flags: :option:`--syntax-theme`

:environment variable: :envvar:`EUPORIE_SYNTAX_THEME`
:default: ``'default'``
:type: :keyword:`string`
:description: Syntax highlighting theme

   The name of the pygments style to use for syntax highlighting.


.. option:: color_depth

:flags: :option:`--color-depth`

:environment variable: :envvar:`EUPORIE_COLOR_DEPTH`
:type: :keyword:`integer`
:options: [``1``, ``4``, ``8``, ``24``]
:description: The color depth to use

   The number of bits to use to represent colors displayable on the screen.
   If set to None, the supported color depth of the terminal will be detected
   automatically.


.. option:: tmux_graphics

:flags: :option:`--tmux-graphics`

:environment variable: :envvar:`EUPORIE_TMUX_GRAPHICS`
:default: ``False``
:type: :keyword:`boolean`
:description: Enable terminal graphics in tmux (experimental)

   If set, terminal graphics will be used if :program:`tmux` is running by
   performing terminal escape sequence pass-through. You must restart euporie
   forthis to take effect.

   .. warning::
      Terminal graphics in :program:`tmux` is experimental, and is not
      guaranteed to work. Use at your own risk!


.. option:: color_scheme

:flags: :option:`--color-scheme`

:environment variable: :envvar:`EUPORIE_COLOR_SCHEME`
:default: ``'default'``
:type: :keyword:`string`
:options: [``'default'``, ``'inverse'``, ``'light'``, ``'dark'``, ``'black'``, ``'white'``, ``'custom'``]
:description: The color scheme to use

   The color scheme to use: `auto` means euporie will try to use your
   terminal's color scheme, `light` means black text on a white background,
   and `dark` means white text on a black background.


.. option:: custom_background_color

:flags: :option:`--custom-background-color` or :option:`--custom-bg-color` or :option:`--bg`

:environment variable: :envvar:`EUPORIE_CUSTOM_BACKGROUND_COLOR`
:default: ``''``
:type: :keyword:`string`
:description: Background color for "Custom" color theme

   The hex code of the color to use for the background in the "Custom" color
   scheme.


.. option:: custom_foreground_color

:flags: :option:`--custom-foreground-color` or :option:`--custom-fg-color` or :option:`--fg`

:environment variable: :envvar:`EUPORIE_CUSTOM_FOREGROUND_COLOR`
:default: ``''``
:type: :keyword:`string`
:description: Background color for "Custom" color theme

   The hex code of the color to use for the foreground in the "Custom" color
   scheme.


.. option:: accent_color

:flags: :option:`--accent-color`

:environment variable: :envvar:`EUPORIE_ACCENT_COLOR`
:default: ``'ansiblue'``
:type: :keyword:`string`
:description: Accent color to use in the app

   The hex code of a color to use for the accent color in the application.


.. option:: line_numbers

:flags: :option:`--line-numbers`

:environment variable: :envvar:`EUPORIE_LINE_NUMBERS`
:default: ``True``
:type: :keyword:`boolean`
:description: Show or hide line numbers

   Whether line numbers are shown by default.


.. option:: autocomplete

:flags: :option:`--autocomplete`

:environment variable: :envvar:`EUPORIE_AUTOCOMPLETE`
:default: ``False``
:type: :keyword:`boolean`
:description: Provide completions suggestions automatically

   Whether to automatically suggestion completions while typing in code cells.


.. option:: autosuggest

:flags: :option:`--autosuggest`

:environment variable: :envvar:`EUPORIE_AUTOSUGGEST`
:default: ``True``
:type: :keyword:`boolean`
:description: Provide line completion suggestions

   Whether to automatically suggestion line content while typing in code cells.


.. option:: autoinspect

:flags: :option:`--autoinspect`

:environment variable: :envvar:`EUPORIE_AUTOINSPECT`
:default: ``False``
:type: :keyword:`boolean`
:description: Display contextual help automatically

   Whether to automatically display contextual help when navigating through code cells.


.. option:: show_status_bar

:flags: :option:`--show-status-bar`

:environment variable: :envvar:`EUPORIE_SHOW_STATUS_BAR`
:default: ``True``
:type: :keyword:`boolean`
:description: Show the status bar

   Whether the status bar should be shown at the bottom of the screen.


.. option:: app

:flags: :option:`--app`

:environment variable: :envvar:`EUPORIE_APP`
:default: ``'notebook'``
:type: :keyword:`string`
:options: [``'notebook'``, ``'console'``]
:description: App to run under euporie hub

   Determine which euporie app should be launched under euporie hub.


.. option:: host

:flags: :option:`--host`

:environment variable: :envvar:`EUPORIE_HOST`
:default: ``''``
:type: :keyword:`string`
:description: The host address to bind to

   This determines the host address the euporie hub SSH server will bind to.


.. option:: port

:flags: :option:`--port`

:environment variable: :envvar:`EUPORIE_PORT`
:default: ``8022``
:type: :keyword:`integer`
:description: The port for the ssh server to use

   This determines which port euporie will listen on for connections to
   euporie hub.


.. option:: host_keys

:flags: :option:`--host-keys`

:environment variable: :envvar:`EUPORIE_HOST_KEYS`
:default: ``['/etc/ssh/ssh_host_ecdsa_key']``
:type: :keyword:`array`
:description: Host keys to use for the SSH server

   One or more SSH host key files to use for the euporie hub SSH server.


.. option:: client_keys

:flags: :option:`--client-keys`

:environment variable: :envvar:`EUPORIE_CLIENT_KEYS`
:default: ``['~/.ssh/authorized_keys']``
:type: :keyword:`array`
:description: Client public keys authorized to connect

   One or more OpenSSH-style :file:`authorized_keys` files, containing
   public keys for authorized clients.


.. option:: no_auth

:flags: :option:`--no-auth`

:environment variable: :envvar:`EUPORIE_NO_AUTH`
:default: ``False``
:type: :keyword:`boolean`
:description: Allow unauthenticated access to euporie hub

   When set, users will be able to access euporie hub without authentication.

   .. warning::
      This option is dangerous, as arbitrary code can be executed through


.. option:: show_cell_borders

:flags: :option:`--show-cell-borders`

:environment variable: :envvar:`EUPORIE_SHOW_CELL_BORDERS`
:default: ``False``
:type: :keyword:`boolean`
:description: Show or hide cell borders.

   Whether cell borders should be drawn for unselected cells.


.. option:: save_widget_state

:flags: :option:`--save-widget-state`

:environment variable: :envvar:`EUPORIE_SAVE_WIDGET_STATE`
:default: ``True``
:type: :keyword:`boolean`
:description: Save a notebook's widget state in the notebook metadata

   When set to ``True``, the state of any widgets in the current notebook will
   be saves in the notebook's metadata. This enables widgets to be displayed
   when the notebook is re-opened without having to re-run the notebook.


.. option:: max_notebook_width

:flags: :option:`--max-notebook-width`

:environment variable: :envvar:`EUPORIE_MAX_NOTEBOOK_WIDTH`
:default: ``120``
:type: :keyword:`integer`
:description: Maximum width of notebooks

   The maximum width at which to display a notebook.


.. option:: expand

:flags: :option:`--expand`

:environment variable: :envvar:`EUPORIE_EXPAND`
:default: ``False``
:type: :keyword:`boolean`
:description: Use the full width to display notebooks

   Whether the notebook page should expand to fill the available width


.. option:: show_scroll_bar

:flags: :option:`--show-scroll-bar`

:environment variable: :envvar:`EUPORIE_SHOW_SCROLL_BAR`
:default: ``True``
:type: :keyword:`boolean`
:description: Show the scroll bar

   Whether the scroll bar should be shown on the right of the screen.


.. option:: tab_mode

:flags: :option:`--tab-mode`

:environment variable: :envvar:`EUPORIE_TAB_MODE`
:default: ``'stack'``
:type: :keyword:`string`
:options: [``'stack'``, ``'tile_horizontally'``, ``'tile_vertically'``]
:description: The method used to display multiple tabs

   Determines how multiple tabs are displayed when more than one tab is open.
   * ``stack`` displays one tab at a time with a tab-bar
   * ``tile_horizontally`` displays tabs side-by-side
   * ``tile_vertically`` displays tabs one-atop-the-next


.. option:: always_show_tab_bar

:flags: :option:`--always-show-tab-bar`

:environment variable: :envvar:`EUPORIE_ALWAYS_SHOW_TAB_BAR`
:default: ``False``
:type: :keyword:`boolean`
:description: Always show the tab bar

   When set, the tab bar will always be shown - otherwise the tab bar is only
   shown when multiple tabs are open.


.. option:: background_pattern

:flags: :option:`--background-pattern` or :option:`--bg-pattern`

:environment variable: :envvar:`EUPORIE_BACKGROUND_PATTERN`
:default: ``2``
:type: :keyword:`integer`
:options: [``0``, ``1``, ``2``, ``3``, ``4``, ``5``]
:description: The background pattern to use

   The background pattern to use when the notebook is narrower than the
   available width. Zero mean no pattern is used.


.. option:: background_character

:flags: :option:`--background-character` or :option:`--bg-char`

:environment variable: :envvar:`EUPORIE_BACKGROUND_CHARACTER`
:default: ``'·'``
:type: :keyword:`string`
:description: Character for background pattern

   The character to use when drawing the background pattern.

   Recommended characters include: "·", "⬤", "╳", "╱", "╲", "░", "▒", "▓", "▞", "╬"


.. option:: run_after_external_edit

:flags: :option:`--run-after-external-edit`

:environment variable: :envvar:`EUPORIE_RUN_AFTER_EXTERNAL_EDIT`
:default: ``False``
:type: :keyword:`boolean`
:description: Run cells after editing externally

   Whether to execute a cell immediately after editing in `$EDITOR`.


.. option:: run

:flags: :option:`--run`

:environment variable: :envvar:`EUPORIE_RUN`
:default: ``False``
:type: :keyword:`boolean`
:description: Run the notebook files when loaded

   If set, notebooks will be run automatically when opened, or if previewing a
   file, the notebooks will be run before being output.


.. option:: save

:flags: :option:`--save`

:environment variable: :envvar:`EUPORIE_SAVE`
:default: ``False``
:type: :keyword:`boolean`
:description: Save the notebook after running it

   If set, notebooks will be saved after they have been run. This setting only
   has any affect if the :option:`run` setting is active.


.. option:: show_filenames

:flags: :option:`--show-filenames`

:environment variable: :envvar:`EUPORIE_SHOW_FILENAMES`
:default: ``False``
:type: :keyword:`boolean`
:description: Show the notebook filenames when previewing multiple notebooks

   If set, the notebook filenames will be printed above each notebook's output
   when multiple notebooks are being previewed.


.. option:: cell_start

:flags: :option:`--cell-start`

:environment variable: :envvar:`EUPORIE_CELL_START`
:type: :keyword:`integer`
:description: The first cell to include in the preview

   When set, only cells after the given cell index will be shown.


.. option:: cell_stop

:flags: :option:`--cell-stop`

:environment variable: :envvar:`EUPORIE_CELL_STOP`
:type: :keyword:`integer`
:description: The last cell to include in the preview

   When set, only cells before the given cell index will be shown.


.. option:: output_file

:flags: :option:`--output-file`

:environment variable: :envvar:`EUPORIE_OUTPUT_FILE`
:default: ``'-'``
:type: :keyword:`string`
:description: Output path when previewing file

   When set to a file path, the formatted output will be written to the
   given path. If no value is given (or the default "-" is passed) output
   will be printed to standard output.


.. option:: page

:flags: :option:`--page`

:environment variable: :envvar:`EUPORIE_PAGE`
:default: ``False``
:type: :keyword:`boolean`
:description: Pass output to pager

   Whether to pipe output to the system pager when previewing a notebook.
