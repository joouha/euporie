#####
Usage
#####

**********************
Command Line Interface
**********************

To open a notebook from the command line, launch euporie with the notebook file's path as an argument:

.. code-block:: console

   $ euporie ./my-notebook.ipynb

The following command line arguments are available:

Positional Arguments
====================

.. option:: <Path ...>

   A sequence of notebook file-paths to open

Options
=======

.. _usage-start:

.. option:: -h, --help

   show this help message and exit

.. option:: --version, -V

   Show the version number and exit

.. option:: --log-file <str>

   File path for logs

.. option:: --debug, --no-debug

   Include debug output in logs

.. option:: --dump, --no-dump

   Output formatted file to display or file

.. option:: --dump-file <Path>

   Output path when dumping file

.. option:: --page, --no-page

   Pass output to pager

.. option:: --run, --no-run

   Run the notebook when loaded

.. option:: --tmux-graphics, --no-tmux-graphics

   Enable terminal graphics in tmux (experimental)

.. option:: --terminal-polling-interval <int>

   Time between terminal colour queries

.. option:: --edit-mode {micro,emacs,vi}

   Key-binding mode for text editing

.. option:: --tab-size <int>

   Spaces per indentation level

.. option:: --run-after-external-edit

   Run cells after editing externally

.. option:: --format-black, --no-format-black

   Use black when re-formatting code cells

.. option:: --format-isort, --no-format-isort

   Use isort when re-formatting code cells

.. option:: --format-ssort, --no-format-ssort

   Use ssort when re-formatting code cells

.. option:: --autoformat, --no-autoformat

   Automatically re-format code cells when run

.. option:: --autocomplete, --no-autocomplete

   Provide completions suggestions automatically

.. option:: --autosuggest, --no-autosuggest

   Provide line completion suggestions

.. option:: --autoinspect, --no-autoinspect

   Display contextual help automatically

.. option:: --expand, --no-expand

   Use the full width to display notebooks

.. option:: --max-notebook-width <int>

   Maximum width of notebooks

.. option:: --show-status-bar, --no-show-status-bar

   Show the status bar

.. option:: --color-scheme {default,inverse,light,dark}

   The color scheme to use

.. option:: --background-pattern {0,1,2,3,4,5}, --bg-pattern {0,1,2,3,4,5}

   The background pattern to use

.. option:: --background-character <str>, --bg-char <str>

   Character for background pattern

.. option:: --background-color <str>, --bg-color <str>

   Color for background pattern

.. option:: --show-cell-borders, --no-show-cell-borders

   Show or hide cell borders.

.. option:: --line-numbers, --no-line-numbers

   Show or hide line numbers

.. option:: --syntax-theme <str>

   Syntax highlighting theme

.. option::

   List of file names to open
.. _usage-end:
