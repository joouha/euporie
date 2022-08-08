#########
Changelog
#########

Notable changes to this project will be documented in this file.

********
Upcoming
********

Added
=====

- Allow changing color depth on the fly
- Key-bindings can now be edited in the configuration file
- Queue inputs which are run before kernel starts, and run them once the kernel has started
- Add ability to convert from console to notebook
- Set initial vi mode to navigation
- Add euporie console application
- Add "Save As..." command
- Allow opening file from remote file systems (e.g. ``http:``, ``hdfs:``, ``gs:``, ``s3:``, etc.)
- Add ability to undo deleting cells
- Add support for ipywidgets
- Allow changing app accent color
- Allow connecting to existing kernels with :option:`kernel_connection_file` config option

Changed
=======

- Cells are now displayed as soon as they are rendered in ``preview``
- Added the ``--save`` option in ``preview``, which saves the notebook if ``--run`` is used
- Apps are now individually configurable
- The ``edit`` app is not called ``notebook``
- The preferred method of launching apps is now using the ``euporie-*`` commands
- The style of the applications and widgets has been refresh
- Allow creating new notebooks without first passing a file path
- Use :py:mod:`fastjsonschema` to parse configuration more quickly
- Reduce memory usage by allowing the garbage collector to remove deleted cells and graphics
- Make clicking to select a cell pass the click event to the cell

Fixed
=====

- Clicking on a cell to focus no longer results in a selection if the notebooks has to be scrolled
- Fix issue with hyperlinks taking over the screen
- Fix bug which prevented mouse scrolling in some circumstances
- Fix ``--version`` command line flag

----

*********************
v1.6.2 - (2022-05-09)
*********************

Changed
=======

- Display multiple cursors in vi multi-cursor mode

*********************
v1.6.1 - (2022-05-08)
*********************

Changed
=======

- Allow ``file:`` scheme links in markdown

Fixed
=====

- Enable entering vi navigation mode
- Change "go to matching bracket" command key-binding in micro mode to :kbd:`Alt+(` / :kbd:`Alt+)`, so as not to conflict with the "find-next" command

----

*********************
v1.6.0 - (2022-04-26)
*********************

Added
=====

- Add dialog explaining if no kernels are found
- Allow changing tabs by scrolling on them
- Add "Custom" color scheme, allowing foreground and background colours to be configured
- Add "Black" and "White" color schemes
- Add a tab bar, and tab stacking / tiling
- Detect terminal colors inside :command:`tmux`

Changed
=======

- Fix bug where markdown was not rendered on some installs
- Update documentation
- Remove input flush timeout after escape key
- Use sub-command in the command line interface
- Styling changes
- Do not colour cell input box background if terminal background color is not detected
- Improve cell stdin focus logic

Fixed
=====

- Force cell input to be re-lexed when changing cell type
- Prevent OSC-8 link mis-detection bug by adding link IDs
- Fix regression making cell selection in long notebooks very slow

----

*********************
v1.5.0 - (2022-04-19)
*********************

Added
=====

- Allow extending selection by word using :kbd:`Alt+Shift+Left` / :kbd:`Alt+Shift+Right`
- Add euporie hub: a multi-client SSH server serving euporie
- Add search toolbar (searches cell input in edit mode)
- Use `prompt_toolkit` to format logging output
- Allow scrolling cell outputs with :kbd:`left` and :kbd`right` in command mode
- Theme more elements based on current terminal theme

Changed
=======

- Optimize imports, reducing import times by ~50%
- Improve fix for missing first empty cells in ``html2text`` markdown tables

Fixed
=====

- Restore graphics in tmux functionality
- Allow entering edit mode by clicking on cell input
- Expand ``~`` in log file path
- Prevent IPython import race condition when IPython is installed
- Prevent down key moving to next cell if the cursor is on the last line of a cell when the completion menu is open
- Enable euporie to run on Window again
- Prevent an underscore being printed when the app is launched
- Only send terminal queries if the terminal supports it

----

*********************
v1.4.3 - (2022-03-30)
*********************

Added
=====

- Notebook will scroll so the cursor is always visible when in edit mode
- Add ability to copy cell output
- Allow colour-depth to be manually configured
- Allow scroll bar visibility to be toggled

Fixed
=====

- Ensure dumping notebooks works when stdin is not a TTY (this allows euporie to be used to preview notebooks in ranger)
- Prevent exception when navigating to an empty cell in edit mode
- Prevent wide tables from wrapping with :py:mod:`html2text` renderer

----

*********************
v1.4.2 - (2022-03-28)
*********************

Added
=====

- Respond to kernel requests to clear cell outputs
- Used colored output with elinks HTML renderer

Fixed
=====

- Fix parsing of html tables with empty first cells by :py:mod:`html2text`
- Fixed toggling comments if a line consists of a single right-stripped comment

Changed
=======

- Parse environment variables a Python literals, so setting a binary variable to ``"False"`` no longer evaluates to :py:const:`True`

----

*********************
v1.4.1 - (2022-03-26)
*********************

=====
Fixed
=====

- Exception raised when attempting to strip an empty formatted text string which occasionally caused issues when rendering markdown

----

*********************
v1.4.0 - (2022-03-26)
*********************

Added
=====

- Add :py:mod:`html2text` as a HTML renderer
- Add new markdown parser based on :py:mod:`markdown_it`
- Highlight matching brackets and add command (:kbd:`Ctrl+g`) to jump between matching brackets
- Add shortcuts :kbd:`Alt+Up` and :kbd:`Alt+Down` to move cells
- Show notebook mode in status-bar
- Allow moving cursor between cells from first / last line
- Allow extended a notebooks' cell selection with the mouse (:kbd:`Shift + Click` or :kbd:`Ctrl + Click`)
- Add ability to extend cell selection to top or bottom of notebook

Changed
=======

- Make cell edit mode persistent between cells

Fixed
=====

- Only send terminal query escape codes if output is a TTY - this prevents disrupted output when dumping or paging notebooks
- Fix word selection in case toggle command
- Images now resized if terminal font size changes
- Fixed maultiple bugs with external image converters
- Fix editing cells in external editor

----

*********************
v1.3.1 - (2022-03-24)
*********************

Fixed
=====

- Prevent :py:mod:`ssort` clearing cells with only comments

*********************
v1.3.1 - (2022-03-20)
*********************

Fixed
=====

- Fix notebook dumping regression

----

*********************
v1.3.0 - (2022-03-19)
*********************

Added
=====

- Added ability to select multiple notebook cells
- Added ability to merge multiple cells
- Added ability to split cells
- Added commands to move cells up and down

Changed
=======

- Expanded run, cut, copy, paste commands to work with multiple cells
- Changing cell type affects all selected cells
- Formatting cells formats all selected code cells

Fixed
=====

- Fix recursion bug when editing a cell when multiple cells are selected

----

*********************
v1.2.2 - (2022-03-17)
*********************

Fixed
=====

- Fix zero-division error if scrolling a window with less content than its height

----

*********************
v1.2.1 - (2022-03-17)
*********************

Added
=====

- Make terminal colour polling timeout configurable
- Add ability to focus and scroll the inspection pane
- Add inspection pane key-bindings

Changed
=======

- Use improved scrollbars with mouse support (if `PR #1587 <https://github.com/prompt-toolkit/python-prompt-toolkit/pull/1587>`_ is merged)

Fixed
=====

- Ensure opening command palette does not show an error if it is opened before is has loaded
- Fixed bug where nothing would be focused after a completion if pager was opened

----

*********************
v1.2.0 - (2022-03-06)
*********************

Added
=====

- Inspection pane for showing contextual help (summon with :kbd:`Shift+Tab` in a code cell)
- Add ability to use :py:mod:`isort` and :py:mod:`ssort` when formatting code cells
- Make terminal colour change detection interval configurable

Fixed
=====

- Indent if cursor in leading whitespace rather than suggest complete
- No longer continue indenting on subsequent newlines after a colon

----

*********************
v1.1.0 - (2022-03-04)
*********************

Added
=====

- Obey the :envvar:`NO_COLOR` environment variable (`https://no-color.org/ <https://no-color.org/>`_)
- Graphic background now follows theme color not terminal color
- Add command palette (summoned with :kbd:`Ctrl+space`)
- Add experimental support for terminal graphics from within tmux
- Add support for displaying images using the `iTerm inline images protocol <https://iterm2.com/documentation-images.html>`_
- New terminal graphic rendering system to work with new scrolling method
- Allow displaying pager outputs (e.g. when using ``print??`` ipython syntax)
- Display PDF outputs
- Add option to automatically format code cells with black
- Experimental support for terminal graphics in :command:`tmux`

Changed
=======

- New notebooks scrolling method which improves scrolling performance
- New data conversion system to replace the output rendering system

Fixed
=====

- Prevent output from the kernel subprocess being printed and breaking the display
- Display tabs in ansi output correctly
- Prevent hidden cell borders show up when syntax theme is changed
- Graphics now use theme background colour rather than terminal background colour
- Fixed occasional error when uncommenting a block of text
- Prevent terminal graphics obscuring dialogs
- Run all cells now works as expected in TUI mode
- Restore clipboard functionality

----

*********************
v1.0.0 - (2020-02-03)
*********************

Added
=====

- Added documentation
- Add shortcut key (:kbd:`c-/`) to toggle line commenting
- Improved terminal feature detection
- Add ability to render LaTeX using :py:mod:`sympy`
- Add new terminal graphics system, which makes displaying using sixels / kitty graphics more reliable
- Add support for LaTex equations in markdown using flatlatex
- Markdown tables no longer expand to the full width of the display
- Show menu item descriptions in the statusbar
- Add keyboard shortcuts to the menu
- Allow status bar to be hidden
- Allow wrapping selection in quotes or brackets
- Display keyboard shortcuts on menus, and better looking menus
- Add `micro` editor style key-bindings as the default
- Add centralized command system
- Configurable cell border visibility
- Read notebook language configuration form the kernel
- Configurable colorschemes
- Support user input with ``input()``
- Support asynchronous cell output (à la :py:mod:`akernel`)
- Vastly more responsive completion & history requests
- Major code restructure
- Much improved scrollbar
- Added ability to view the logs in a tab
- Introduced the concept of "tabs" (tabs are only displayed vertially tiled for now)
- Automatic suggestions from kernel history
- Completion type annotations in the completion menu
- Added ability to automatically run notebooks with `--run` command line flag
- Allow changing background colour
- Add `chafa <https://hpjansson.org/chafa/>`_ as an image renderer

Fixed
=====

- Fix issue where clicking on cells failed to focus them
