#########
Changelog
#########

Notable changes to this project will be documented in this file.

********
Upcoming
********

======
Added
=====

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

- Fixed maultiple bugs with external image converters
- Fix editing cells in external editor

----

******************
1.3.1 - 2022-03-24
******************

Fixed
=====

- Prevent :py:mod:`ssort` clearing cells with only comments

******************
1.3.1 - 2022-03-20
******************

Fixed
=====

- Fix notebook dumping regression

----

******************
1.3.0 - 2022-03-19
******************

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

******************
1.2.2 - 2022-03-17
******************

Fixed
=====

- Fix zero-division error if scrolling a window with less content than its height

----

******************
1.2.1 - 2022-03-17
******************

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

******************
1.2.0 - 2022-03-06
******************

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

******************
1.1.0 - 2022-03-04
******************

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

******************
1.0.0 - 2020-02-03
******************

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
