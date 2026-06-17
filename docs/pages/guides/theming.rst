#######
Theming
#######

Euporie's appearance is controlled by two independent settings:

* the :term:`colour scheme <Color scheme>` - which sets the application's overall foreground and background colours and selects an appropriate palette for menus, borders, status bars and so on, and
* the **syntax theme** - which sets the colours used for syntax-highlighting source code inside cells.

This guide describes how to switch between them and how to configure your own.

***********************
Built-in colour schemes
***********************

Built-in schemes include:

* ``default`` - terminal default (uses your terminal's foreground/background)
* ``dark`` - dark grey background with light foreground
* ``light`` - light background with dark foreground
* ``black`` - pure-black background
* ``white`` - pure-white background
* ``inverse`` - swaps the terminal's foreground and background
* ``custom`` - uses :confval:`custom_foreground_color` and :confval:`custom_background_color`

Switch from inside the :term:`app` via :menuselection:`Settings --> Color Scheme`, or set the :confval:`color_scheme` configuration option.

A custom scheme:

.. code-block:: toml

   color_scheme = "custom"
   custom_foreground_color = "#dcd7ba"
   custom_background_color = "#1f1f28"

*****************
Syntax themes
*****************

Syntax themes come from :doc:`Pygments <pygments:styles>` and include hundreds of options - try ``monokai``, ``dracula``, ``solarized-dark``, ``nord``, ``gruvbox-dark``, ``one-dark`` etc.

Switch from inside the :term:`app` via :menuselection:`Settings --> Syntax Theme`, or set :confval:`syntax_theme`.

*****************
Per-app overrides
*****************

Both options can be overridden per :term:`app`. For example, to use a light scheme in the notebook editor but a dark one in the console:

.. code-block:: toml

   color_scheme = "light"
   syntax_theme = "default"

   [console]
   color_scheme = "dark"
   syntax_theme = "dracula"

See :doc:`../configuration` for the full configuration mechanism.

**********************************
Borders, cell visuals and tab bars
**********************************

A handful of related settings control the visual density of the UI:

* :confval:`show_cell_borders` - draw a coloured border around each :term:`cell`.
* :confval:`always_show_tab_bar` - keep the :term:`tab` bar visible even when only one tab is open.
* :confval:`expand` - let cells expand to fill the available width instead of using a fixed maximum.
* :confval:`show_status_bar` - hide or show the bottom status bar.

These can be tweaked alongside the colour/syntax options to get a layout that suits you, and can also be toggled from inside the :term:`app` via the :menuselection:`Settings --> UI Elements` menu.
