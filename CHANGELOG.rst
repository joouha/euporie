#########
Changelog
#########

Notable changes to this project will be documented in this file.


********
Upcoming
********

Changed
=======

- Rename ``--tmux-graphics`` option to ``--multiplexer-passthrough``, and make it additionally work with GNU screen
- Improve ``imagemagick`` detection so it works on Debian

Added
=====

- Implement progressive rendering in webview
- Pre-render terminal graphics to speed up notebook scrolling
- Add support for ``ruff`` code formatter
- Add support for inline LaTeX math in markdown
- Add ``ziamath`` LaTeX to SVG converter
- Set scroll offset to 1 on cell inputs

Fixed
=====

- Fix ``PgUp`` and ``PgDn`` keybindings in ``ScrollingContainer``
- Fix issue with black code formatter when an unprintable character is entered
- Fix issue with image tearing when using ``chafa.py`` to render images
- Do not highlight brackets if a kernel input is not focused
- Use private color registers for sixel graphics
- Print the entirety of a scrolled input in euporie-console after running the input
- Greatly improved responsiveness when scrolling large cells
- Fix issue when moving cursor up between cells cursor, where cursor moved to second last character


*******************
v2.6.2 (2023-11-23)
*******************

Fixed
=====

- Fix terminal graphics in euporie-console


*******************
v2.6.1 (2023-11-17)
*******************

Fixed
=====

- Do not expand ipywidget HTML widgets (improves appearance of ``tqdm.notebook`` progress bars)
- Fix data update callbacks for HTML & Image ipywidgets
- Fix running multiple cells
- Prevent exception when extending cell selection to include last cell
- Prevent notebook app freezing when copying cell outputs

*******************
v2.6.0 (2023-11-13)
*******************

Added
=====

- Allow scrolling to top of first cell and bottom of last cell with :kbd:`up` and :kbd:`down` if not visible
- Display inline images in markdown and HTML using terminal graphics

Fixed
=====

- Kitty graphics now appear when using non-default color schemes
- Prevent disabled forms being focused
- Prevent rare error when closing a tab
- Prevent error dialog collapsing at small terminal sizes
- Correct error in escape code for querying terminal dimensions
- Fix cell output wrap toggle shortcut

*******************
v2.5.3 (2023-10-19)
*******************

Added
=====

- Use `justify_content` for alignment in `flex` elements in HTML renderer
- Option to use OSC52 for clipboard

Fixed
=====

- Ensure the color of drop-shadows gets updated if the color scheme is changed while the app is running

----

*******************
v2.5.2 (2023-10-14)
*******************

Fixed
=====

- Fix graphic cropping in webview
- Prevent rare error on format conversion failure

----

*******************
v2.5.1 (2023-10-13)
*******************

Fixed
=====

- Ensure extended key support is disabled at correct point in rendering process for apps running in alternate screen

----

*******************
v2.5.0 (2023-10-13)
*******************

Added
=====

- Allow wrapping cell outputs
- Add support for ``%load`` and ``%edit`` magics
- Make icons in file browser configurable
- Implement ``display: grid`` support in HTML renderer
- Add terminal graphics support to webview
- Redirect kernel output to log

Fixed
=====

- Prevent entry of typed escape sequence codes into text areas
- Reset the terminal extended key mode at exit
- Limit horizontal scrolling of display areas
- Prevent error when commenting an empty cell
- Prevent moving through history in vi navigation mode
- Launch kernels from base prefix by default unless ``ipykernel`` is installed inside euporie's environment
- Use ``.md`` filename suffix when editing markdown cells in external editor
- Improve CSI-u escape sequence detection

Changed
=======

- Perform format conversions asynchronously
- Rename ``reset-tab`` command to ``refresh-tab``

----

*******************
v2.4.3 (2023-06-07)
*******************

Fixed
=====

- Fix "Wrong color format" error when suggesting dictionary key completions

----

*******************
v2.4.2 (2023-06-05)
*******************

Changed
=======

- Add common SVG namespaces to HTML inline SVGs before conversion

Fixed
=====

- Force block graphic output from ``viu``
- Fix calling asynchronous commands (e.g. converting console session to a notebook)

----

*******************
v2.4.1 (2023-05-25)
*******************

Fixed
=====

- Fix dependency version conflict between ``platformdirs`` and ``typing-extensions``

----

*******************
v2.4.0 (2023-05-24)
*******************

Changed
=======

- Change from `appdirs` to `platformdirs` for resolving user configuration path
- Improve changes of successful format conversion by trying all conversion routes
- Improvements to responsiveness when opening files
- Update completion menu style
- Changed name of ``hub`` configuration item ```no_auth`` to ``auth`` with inverse logic

Added
=====

- Add web viewer tab for sufing the world wide web
- Add JSON viewer tab
- Add ability to open remote files from "open" dialog
- Add ability to select file open method
- Add support for opening scripts & markdown documents as notebooks using Jupytext
- Show full file-browser file path in status-bar
- Make all scrollbars clickable
- Add ability to select an existing kernel when changing a notebook's kernel
- Add "*.desktop" files
- Select text on find-next
- Add support for saving changes to text files

Fixed
=====

- Fix pandas dataframe HTML output formatting with row multi-indices
- Prevent every ``euporie-consle`` run clearing the screen in ``Konsole``
- Replace tabs with spaces in ANSI text output
- ``SelectMultiple`` widget is now styled consistently with other widgets
- Restore terminal state on unexpected exit signal
- Prevent ``KeyError: 'log_file'`` error when launching apps via ``euporie`` app
- Prevent unknown markdown code block language causing rendering error
- Fix unexpected cropped graphics when using ``timg`` with character aspects ≠ 0.5
- Make clickable scrollbars work correctly with Window containers
- Render cells when converted to markdown
- Prevent crash when connecting to ``euporie-hub``
- Improve mime-type detection
- Make saving safer by saving to a temporary file first

----

*******************
v2.3.2 (2023-03-21)
*******************

Added
=====

- Add :kbd:`Ctrl+up` and :kbd:`Ctrl+down` as key-bindings to move through kernel history in the console
- Allow closing notebook tabs with the middle mouse button
- Notify the user if the kernel dies unexpectedly

Fixed
=====

- Re-enable display of large images in console
- Fix HTML table colspan border rendering issue
- Fix minor notebook scrolling issues
- Fix scrollbar dragging on tiled notebooks
- Prevent exception if kernel requests an unknown lexer
- Improve handling of kernel startup errors and reliability of changing kernels
- Rendering of LaTeX as terminal graphics

----

*******************
v2.3.1 (2023-02-05)
*******************

Added
=====

- Warn about unrecognised configuration options in the log

Fixed
=====

- Fix minor issue with ``chafa.py`` image renderer

*******************
v2.3.0 (2023-02-03)
*******************

Added
=====

- Add ``cahfa.py`` image renderer
- Add command to clear screen
- Add a "Restart kernel and clear all output" command
- Add commands for clearing cell outputs
- The ``scroll-up-5-lines`` and ``scroll-down-5-lines`` commands now scroll to the top or bottom of the document if less than 5 lines remain
- "Open" and "Save As" dialogs now include a file browser
- Added a side-bar, which currently shows a file browser
- Add file display tab
- Minor usability improvements to widgets
- Partially obscured images are now rendered using terminal graphics

Fixed
=====

- Change "toggle cell inputs" / "toggle cell outputs" click area to just prompt number
- Focus notebook page on click
- Add global dragging to slider widgets
- Fixed crash when merging last two cells in a notebook
- Relaxed dependency specification constraints

Changed
=======

- Major re-write of HTML renderer (there is still work to be done on rendering the contents of inline elements).

----

*******************
v2.2.1 (2022-12-09)
*******************

Added
=====

- Add a setting for graphics protocol preference

Fixed
=====

- Fix PIL import error

----

*******************
v2.2.0 (2022-12-01)
*******************

Added
=====

- Make drop-shadows configurable

Changed
=======

- Changed to hatch for package build system

Fixed
=====

- Fix automatic contextual help
- Second attempt to fix cell output left scroll issue

----

*******************
v2.1.5 (2022-12-01)
*******************

Fixed
=====

- Attempt fix for cell output left scroll issue
- Prevent ``background_tasks`` error with ``prompt_toolkit==3.0.30``
- Prevent error when adding a cell during initial render

----

*******************
v2.1.4 (2022-11-29)
*******************

Fixed
=====

- Ensure all cells are re-rendered when a notebook tab is reset

----

*******************
v2.1.3 (2022-11-29)
*******************

Added
=====

- New command to reset tabs, causing notebooks to be reloaded from the filesystem
- Improvements to the HTML renderer

Fixed
=====

- Use valid defaults for foreground and background colors for applications
- Do not collapse cell when clicking on prompt itself, only the area below
- Ensure logo is visible in the documentation
- Fix code block language detection in HTML renderer

----

*******************
v2.1.2 (2022-11-14)
*******************

Fixed
=====

- Prevent crash on Python 3.8

----

*******************
v2.1.1 (2022-10-31)
*******************

Fixed
=====

- Ensure select uses available width in kernel selection dialog
- Do not cut when deleting word in micro edit mode

----

*******************
v2.1.0 (2022-10-29)
*******************

Added
=====

- Make shadows under menus and dialogs semi-transparent
- Add ability to parse comma-separated CSS selectors to HTML parser
- Make dialogs draggable
- Allow configuring the external editor
- Add ability to inject cell position into external editor command (this allows and external editor to be run in a tmux popup)

Fixed
=====

- Significant performance improvements when rendering HTML tables
- Close file after prompting to save a new file when euporie is closed
- Fix dialog button shortcut keys
- Display error messages in file open dialog
- Fixed broken mouse events in button widgets
- Prevent ``IndexError`` when deleting a selection of cells including the last cell

----

*******************
v2.0.9 (2022-10-26)
*******************

Added
=====

- Do not show text selection when cell input is not focused
- Allow menus to be closed with :kbd:`Escape` and opened with :kbd:`F10`
- Enable cell inputs and outputs to be collapsed
- Make changing cursor shapes to showing editing mode configurable

Fixed
=====

- Fixed issue where graphics are not displayed in console but are in notebook
- Re-apply style to cell input background
- Highlight selected trailing whitespace
- Reset button selection status on any global mouse event

----

*******************
v2.0.8 (2022-10-04)
*******************

Added
=====

- Use SGR-pixel position for greater scrolling resolution when dragging scrollbar
- Clear selection in console before printing input
- Add ability to toggle top bar visibility
- Use cursor shapes to show the current input mode

Fixed
=====

- Even more graphics rendering adjustments, including enabling sixel rendering with :command:`chafa`
- Do not clear a cell's output when converting a cell to markdown

----

*******************
v2.0.7 (2022-08-31)
*******************

Fixed
=====

- Fix various graphics rendering glitches
- Disable line wrapping before probing terminal to prevent unrecognised APCs moving the cursor to the next line

----

*******************
v2.0.6 (2022-08-30)
*******************

Fixed
=====

- Prevent last cell of SIXEL images being overwritten
- Fix ubiqitous hyperlink issue
- Fix graphics detection for Konsole
- Hide kitty detection APC sequence in terminals which do not support APC codes

----

*******************
v2.0.5 (2022-08-29)
*******************

Added
=====

- Add interactive JSON cell output preview

Fixed
=====

- Sort configuration sub-menus
- Prevent crash when opening key-binding dialog
- Prevent jumping when scrolling if document is less than one page long
- Fixed issue with range sliders which caused a crash on notebook load

----

*******************
v2.0.4 (2022-08-28)
*******************

Added
=====

- Add colorful command line help text

Changed
=======

- Pre-render cells in background thread when notebook is loaded
- Make scrolling the notebook significantly less janky

Fixed
=====

- Scroll the selected cell into view when entering cell edit mode
- Prevent excessive re-rendering of cells

----

*********************
v2.0.3 - (2022-08-26)
*********************

Fixed
=====

- Handle deleted cells in cell mouse handle wrapper
- Fixed bug in ``euporie-notebook`` where cursor remains hidden when the app exits
- Fix inverted missing kernel logic

----

*********************
v2.0.2 - (2022-08-19)
*********************

Fixed
=====

- Fixed bug where rendering LaTeX in HTML would sometime fail
- Fixed bug where ipywidget float log sliders would not accept intermediate values

----

*********************
v2.0.1 - (2022-08-18)
*********************

Fixed
=====

- Fixed bug with rendering LaTeX maths in markdown cells

----

*********************
v2.0.0 - (2022-08-18)
*********************

Added
=====

- Added new HTML renderer
- Added shortcut key hints in menus and buttons
- Added a shadow under the completions menu
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

- Auto-indent text on newline inside brackets in micro editor mode
- Improve quality of copied outputs
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

----

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
