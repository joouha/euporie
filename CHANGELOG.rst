#########
Changelog
#########

All notable changes to this project will be documented in this file.

******************
1.1.1 - 2022-03-06
******************

Added
=====

- Inspection pane for showing contextual help (summon with :kbd:`Shift+Tab` in a code cell)
- Add ability to use :py:mod:`isort` and :py:mod:`ssort` when formatting code cells

Fixed
=====

- Indent if cursor in leading whitespace rather than suggest complete
- No longer continue indenting on subsequent newlines after a colon

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
