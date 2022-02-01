#########
Changelog
#########

********
Upcoming
********

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
- Added ability to automatically run notebooks with `--run` commmand line flag
- Allow changing background colour
- Add `chafa <https://hpjansson.org/chafa/>`_ as an image renderer
- Fix issue where clicking on cells failed to focus them
