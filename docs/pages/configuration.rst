#############
Configuration
#############

*******************
Configuring Euporie
*******************

Euporie has a ranger of configurable options which affect euporie's bahaviour and appearance.

Options are validated at application startup, so if an option is set to an invalid value, it will be ignored.

The options can be set in three different ways:

Command Line Arguments
======================

Euporie can be configured by passing flags (and sometimes values) on the command line when euporie is launched. The flags for each configuration option and the allowed values are listed in :ref:`configuration-options`.

.. code-block:: console

   $ euporie --color-scheme=light --no-show-cell-borders --expand notebook.ipynb

Options set on the command line will override those set via an environment variable, in the configuration file, and the default values.

Environment Variables
=====================

Euporie can be configured by setting environment variables. Each option can be set by assigning a value to an environment variable with uppercase option name, prefixed with ``EUPORIE_``.

.. code-block:: console

   $ EUPORIE_COLOR_SCHEME=light EUPORIE_SHOW_CELL_BORDERS= EUPORIE_EXPAND=True euporie notebook.ipynb

Setting boolean values to an empty string will cause them to evaluate to :py:keyword:`False`.

Options set in via an environment variable will override those set in the configuration file and the default values.

Configuration File
==================

Euporie can be configured using a JSON configuration file. The file takes the form of *key: value* pairs, where the key is one of the options listed in :ref:`configuration-options`

.. warning::
   The configuration file is read when euporie is launched, and modifying options from the :menuselection:`Settings` menu in euporie will cause the configuration file to be updated. Thus, any changes made to the configuration file while euporie is running may be lost, so this is not reccomended.

Example
   .. code-block:: JSON

      {
        "color_scheme": "light",
        "syntax_theme": "native",
        "show_cell_borders": false,
        "expand": true
      }

File Location
   The location of Euporie's configuration file depends on your operating system:

   +-------------+-------------------------------------------------------------+
   | **Linux**   | :file:`$XDG_CONFIG_HOME/euporie/config.json`                |
   +-------------+-------------------------------------------------------------+
   | **Mac OS**  | :file:`~/Library/Application Support/<euporie>/config.json` |
   +-------------+-------------------------------------------------------------+
   | **Windows** | :file:`%APPDATA%\\Local\\euporie\\config.json`              |
   +-------------+-------------------------------------------------------------+

If the file cannot be parsed as valid JSON, the file will be ignored.

Options set in the configuration file will override the default values.

----

.. _configuration-options:

*********************
Configuration Options
*********************

All available configuration options are listed below:

.. _configuration-options-start:
.. option:: log_file

:flags: :option:`--log-file`
:environment variable: :envvar:`EUPORIE_LOG_FILE`
:default: ``''``
:type: :keyword:`string`
:description: File path for logs

   When set to a file path, the log output will be written to the given path.
   If no value is given output will be sent to the standard output.

.. option:: debug

:flags: :option:`--debug`
:environment variable: :envvar:`EUPORIE_DEBUG`
:default: ``False``
:type: :keyword:`boolean`
:description: Include debug output in logs

   When set, logging events at the debug level are emmitted.

.. option:: dump

:flags: :option:`--dump`
:environment variable: :envvar:`EUPORIE_DUMP`
:default: ``False``
:type: :keyword:`boolean`
:description: Output formatted file to display or file

   When set, the formatted output will be written to the the output file path
   given by `dump_file` (standard output by default).

.. option:: dump_file

:flags: :option:`--dump-file`
:environment variable: :envvar:`EUPORIE_DUMP_FILE`
:type: :keyword:`string`
:description: Output path when dumping file

   When set to a file path, the formatted output will be written to the
   given path. If no value is given (or the default "-" is passed) output
   will be printed to standard output.

.. option:: page

:flags: :option:`--page`
:environment variable: :envvar:`EUPORIE_PAGE`
:default: ``False``
:type: :keyword:`boolean`
:description: Pass output to pager

   Whether to pipe output to the system pager when using ``--dump``.

.. option:: run

:flags: :option:`--run`
:environment variable: :envvar:`EUPORIE_RUN`
:default: ``False``
:type: :keyword:`boolean`
:description: Run the notebook when loaded

   If set, notebooks will be run automatically when opened, or if dumping
   output, notebooks will be run before being output.

.. option:: tmux_graphics

:flags: :option:`--tmux-graphics`
:environment variable: :envvar:`EUPORIE_TMUX_GRAPHICS`
:default: ``False``
:type: :keyword:`boolean`
:description: Enable terminal graphics in tmux (experimental)

   If set, terminal graphics will be used if :program:`tmux` is running by
   performing terminal escape sequence pass-through. You must restart euporie for
   this to take effect.

   .. warning::

      Terminal graphics in :program:`tmux` is experimental, and is not guaranteed
      to work. Use at your own risk!

.. option:: edit_mode

:flags: :option:`--edit-mode`
:environment variable: :envvar:`EUPORIE_EDIT_MODE`
:default: ``'micro'``
:type: :keyword:`string`
:options: [``'micro'``, ``'emacs'``, ``'vi'``]
:description: Key-binding mode for text editing

   Key binding mode to use when editing cells.

.. option:: tab_size

:flags: :option:`--tab-size`
:environment variable: :envvar:`EUPORIE_TAB_SIZE`
:default: ``4``
:type: :keyword:`integer`
:description: Spaces per indentation level

   The number of spaces to use per indentation level. Should be set to 4.

.. option:: run_after_external_edit

:flags: :option:`--run-after-external-edit`
:environment variable: :envvar:`EUPORIE_RUN_AFTER_EXTERNAL_EDIT`
:default: ``False``
:type: :keyword:`boolean`
:description: Run cells after editing externally

   Whether to execute a cell immediately after editing in `$EDITOR`.

.. option:: format_black

:flags: :option:`--format-black`
:environment variable: :envvar:`EUPORIE_FORMAT_BLACK`
:default: ``True``
:type: :keyword:`boolean`
:description: Use black when re-formatting code cells

   Whether to use :py:mod:`black` when reformatting code cells.

.. option:: format_isort

:flags: :option:`--format-isort`
:environment variable: :envvar:`EUPORIE_FORMAT_ISORT`
:default: ``True``
:type: :keyword:`boolean`
:description: Use isort when re-formatting code cells

   Whether to use :py:mod:`isort` when reformatting code cells.

.. option:: format_ssort

:flags: :option:`--format-ssort`
:environment variable: :envvar:`EUPORIE_FORMAT_SSORT`
:default: ``True``
:type: :keyword:`boolean`
:description: Use ssort when re-formatting code cells

   Whether to use :py:mod:`ssort` when reformatting code cells.

.. option:: autoformat

:flags: :option:`--autoformat`
:environment variable: :envvar:`EUPORIE_AUTOFORMAT`
:default: ``False``
:type: :keyword:`boolean`
:description: Automatically re-format code cells when run

   Whether to automatically reformat code cells before they are run.

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

.. option:: expand

:flags: :option:`--expand`
:environment variable: :envvar:`EUPORIE_EXPAND`
:default: ``False``
:type: :keyword:`boolean`
:description: Use the full width to display notebooks

   Whether the notebook page should expand to fill the available width

.. option:: max_notebook_width

:flags: :option:`--max-notebook-width`
:environment variable: :envvar:`EUPORIE_MAX_NOTEBOOK_WIDTH`
:default: ``120``
:type: :keyword:`integer`
:description: Maximum width of notebooks

   The maximum width at which to display a notebook.

.. option:: show_status_bar

:flags: :option:`--show-status-bar`
:environment variable: :envvar:`EUPORIE_SHOW_STATUS_BAR`
:default: ``True``
:type: :keyword:`boolean`
:description: Show the status bar

   Whether the status bar should be shown at the bottom of the screen.

.. option:: color_scheme

:flags: :option:`--color-scheme`
:environment variable: :envvar:`EUPORIE_COLOR_SCHEME`
:default: ``'default'``
:type: :keyword:`string`
:options: [``'default'``, ``'inverse'``, ``'light'``, ``'dark'``]
:description: The color scheme to use

   The color scheme to use: `auto` means euporie will try to use your
   terminal's color scheme, `light` means black text on a white background,
   and `dark` means white text on a black background.

.. option:: background_pattern

:flags: :option:`--background-pattern` or :option:`--bg-pattern`
:environment variable: :envvar:`EUPORIE_BACKGROUND_PATTERN`
:default: ``2``
:type: :keyword:`integer`
:options: [``0``, ``1``, ``2``, ``3``, ``4``, ``5``]
:description: The background pattern to use

   The background pattern to use when the notebook is narrower than the
   availble width. Zero mean no pattern is used.

.. option:: background_character

:flags: :option:`--background-character` or :option:`--bg-char`
:environment variable: :envvar:`EUPORIE_BACKGROUND_CHARACTER`
:default: ``'·'``
:type: :keyword:`string`
:description: Character for background pattern

   The character to use when drawing the background pattern.

   Reccomended characters include: "·", "⬤", "╳", "╱", "╲", "░", "▒", "▓", "▞", "╬"

.. option:: background_color

:flags: :option:`--background-color` or :option:`--bg-color`
:environment variable: :envvar:`EUPORIE_BACKGROUND_COLOR`
:default: ``''``
:type: :keyword:`string`
:description: Color for background pattern

   The color to use for the background pattern.

.. option:: show_cell_borders

:flags: :option:`--show-cell-borders`
:environment variable: :envvar:`EUPORIE_SHOW_CELL_BORDERS`
:default: ``False``
:type: :keyword:`boolean`
:description: Show or hide cell borders.

   Whether cell borders should be drawn for unselected cells.

.. option:: line_numbers

:flags: :option:`--line-numbers`
:environment variable: :envvar:`EUPORIE_LINE_NUMBERS`
:default: ``True``
:type: :keyword:`boolean`
:description: Show or hide line numbers

   Whether line numbers are shown by default.

.. option:: syntax_theme

:flags: :option:`--syntax-theme`
:environment variable: :envvar:`EUPORIE_SYNTAX_THEME`
:default: ``'default'``
:type: :keyword:`string`
:description: Syntax higlighting theme

   The name of the pygments style to use for syntax highlighting.

.. option:: files

:environment variable: :envvar:`EUPORIE_FILES`
:type: :keyword:`array`
:description: List of file names to open

   A list of file paths to open when euporie is launched.

.. option:: version

:flags: :option:`--verion` or :option:`-V`
:description: Show the version number and exit

   If set, euporie will print the current version number of the application and exit.
   All other configuration options will be ignored.

   .. note::
      This cannot be set in the configuration file or via an environment variable

.. _configuration-options-end:
