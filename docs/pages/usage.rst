#####
Usage
#####

To open a notebook, launch euporie with the notebook file's path as an argument:

.. code-block:: console

   $ euporie ./my-notebook.ipynb

Additional command line flags are described when running ``euporie --help``, the output of which is copied below:

.. _usage-start:
.. code-block::

  usage: euporie [-h] [--log-file [str]] [--debug | --no-debug]
                 [--dump | --no-dump] [--dump-file [Path]] [--page | --no-page]
                 [--run | --no-run] [--tmux-graphics | --no-tmux-graphics]
                 [--edit-mode {micro,emacs,vi}] [--tab-size int]
                 [--run-after-external-edit bool]
                 [--autoformat | --no-autoformat]
                 [--autocomplete | --no-autocomplete]
                 [--autosuggest | --no-autosuggest] [--expand | --no-expand]
                 [--max-notebook-width int]
                 [--show-status-bar | --no-show-status-bar]
                 [--color-scheme {default,inverse,light,dark}]
                 [--background-pattern {0,1,2,3,4,5}]
                 [--background-character str] [--background-color str]
                 [--show-cell-borders | --no-show-cell-borders]
                 [--line-numbers | --no-line-numbers] [--syntax-theme str]
                 [--verion]
                 [Path ...]

  A TUI editor for Jupyter notebooks

  positional arguments:
    Path                  List of file names to open

  options:
    -h, --help            show this help message and exit
    --log-file [str]      File path for logs
    --debug, --no-debug   Include debug output in logs
    --dump, --no-dump     Output formatted file to display or file
    --dump-file [Path]    Output path when dumping file
    --page, --no-page     Pass output to pager
    --run, --no-run       Run the notebook when loaded
    --tmux-graphics, --no-tmux-graphics
                          Enable terminal graphics in tmux (experimental)
    --edit-mode {micro,emacs,vi}
                          Key-binding mode for text editing
    --tab-size int        Spaces per indentation level
    --run-after-external-edit bool
                          Run cells after editing externally
    --autoformat, --no-autoformat
                          Automatically re-format code cells when run
    --autocomplete, --no-autocomplete
                          Provide completions suggestions automatically
    --autosuggest, --no-autosuggest
                          Provide line completion suggestions
    --expand, --no-expand
                          Use the full width to display notebooks
    --max-notebook-width int
                          Maximum width of notebooks
    --show-status-bar, --no-show-status-bar
                          Show the status bar
    --color-scheme {default,inverse,light,dark}
                          The color scheme to use
    --background-pattern {0,1,2,3,4,5}, --bg-pattern {0,1,2,3,4,5}
                          The background pattern to use
    --background-character str, --bg-char str
                          Character for background pattern
    --background-color str, --bg-color str
                          Color for background pattern
    --show-cell-borders, --no-show-cell-borders
                          Show or hide cell borders.
    --line-numbers, --no-line-numbers
                          Show or hide line numbers
    --syntax-theme str    Syntax higlighting theme
    --verion, -V          Show the version number and exit

  © 2022, Josiah Outram Halstead

.. _usage-end:
