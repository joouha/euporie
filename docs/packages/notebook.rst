################
Euporie Notebook
################

.. include:: ../../packages/euporie-notebook/README.rst
   :start-after: .. content_start
   :end-before: .. getting_started_end

----

**********
User Guide
**********

Creating a New Notebook
=======================

To create a new notebook from the command line, launch euporie with the desired new notebook file path as an argument:

.. code-block:: console

   $ euporie-notebook ./my-new-notebook.ipynb

To create a new notebook from within the TUI editor, select :menuselection:`File --> New` in the menus, or press the :kbd:`Ctrl+N` keyboard shortcut.

.. video:: ../_static/videos/notebook.creating-a-new-notebook.webm
   :width: 100%

|

Editing a Cell
==============

The currently selected cell can be edited by pressing :kbd:`Enter`, which will enter :term:`Edit Mode`. This focuses the cell's input text area, and allows you to edit the cell's content.

To exit :term:`Edit Mode`, you can press the :kbd:`Esc` key when you are done editing, or you can run the cell.

.. video:: ../_static/videos/notebook.editing-a-cell.webm
   :width: 100%

|

Running a Cell
==============

To run the currently selected cell, you can press :kbd:`Ctrl+Enter` (providing your terminal :ref:`supports this key-binding <pages/keybindings:running cells>`; you can also use :kbd:`Ctrl+e`).

Alternatively, you can select :menuselection:`Run --> Run selected cells` in the menu.

.. video:: ../_static/videos/notebook.running-a-cell.webm
   :width: 100%

|

Opening an Existing Notebook
============================

To open a notebook from the command line, launch euporie with the notebook file path as an argument:

.. code-block:: console

   $ euporie-notebook ./my-notebook.ipynb

To open a notebook from within the TUI editor, select :menuselection:`File --> Open` in the menus, or press the :kbd:`Ctrl+O` keyboard shortcut. Enter the path of the notebook you wish to open into the file open dialog and press :guilabel:`OK`.

.. video:: ../_static/videos/notebook.opening-an-existing-notebook.webm
   :width: 100%

|

Adding a new cell
=================

You can press :kbd:`b` to add a new cell below the currently selected cell. You can also press :kbd:`a` to add a new cell above the currently selected cell.

.. video:: ../_static/videos/notebook.adding-a-new-cell.webm
   :width: 100%

|


Navigating the Notebook
=======================

When a notebook is open, the currently selected cell is highlighted with a blue border. The selected cell can be changed using the :kbd:`Up` and :kbd:`Down` arrow keys (or :kbd:`j` and :kbd:`k`). Selecting a cell which is not currently visible will automatically scroll it into view.

You can select the first or last cell the the :kbd:`Home` or :kbd:`End` keys.

The notebook can be scrolled up and down one line at a time using the :kbd:`[` and :kbd:`]` keys respectively. Use the :kbd:`{` and :kbd:`}` keys to scroll up or down by 5 lines. You can also scroll the notebook with the mouse wheel, or by clicking on the notebook's scroll bar.


.. video:: ../_static/videos/notebook.navigating-the-notebook.webm
   :width: 100%

|

Saving a Notebook
=================


To save a notebook, press :kbd:`Ctrl+S` or navigate to :menuselection:`File --> Save Notebook` in the menus.

.. video:: ../_static/videos/notebook.saving-a-notebook.webm
   :width: 100%

|

Closing a Notebook
==================

To save a notebook, press :kbd:`Ctrl+W` or navigate to :menuselection:`File --> Close File Notebook` in the menus.

.. video:: ../_static/videos/notebook.closing-a-notebook.webm
   :width: 100%

|

Changing a Cell's Type
======================

To change the currently selected cells to:

* **code cells**, press :kbd:`y`;
* **markdown cells**, press :kbd:`m`;
* **raw cells**, press :kbd:`r`.

.. video:: ../_static/videos/notebook.changing-a-cells-type.webm
   :width: 100%

|

Restarting the Kernel
=====================

To restart the kernel, navigate to :menuselection:`Kernel --> Restart kernel` in the menus and select :guilabel:`Yes` in the confirmation dialog.

Alternatively, press the :kbd:`0 0` keyboard shortcut.

.. video:: ../_static/videos/notebook.restarting-the-kernel.webm
   :width: 100%

|

Changing the Kernel
===================

To change a notebook's kernel, navigate to :menuselection:`Kernel --> Change kernel` in the menus.

.. video:: ../_static/videos/notebook.changing-the-kernel.webm
   :width: 100%

|

Setting the Color Scheme
========================

To change the color scheme, navigate to :menuselection:`Settings --> Color Scheme` in the menus, then select the color scheme name you want to use.

.. video:: ../_static/videos/notebook.changing-the-color-scheme.webm
   :width: 100%

|

To configure the custom color scheme, use the :option:`custom_foreground_color` and  :option:`custom_background_color` configuration options.

Setting the Syntax Theme
========================

To change the syntax theme, navigate to :menuselection:`Settings --> Syntax Theme` in the menus, then select the syntax theme you want to use.

.. video:: ../_static/videos/notebook.setting-the-syntax-theme.webm
   :width: 100%

|

Using the Command Palette
=========================

Practically every action in euporie (including all of those listed above) can be performed through the :term:`command palette`, which can be summoned using :kbd:`Ctrl+Space`. You can type in the input box to search for a command, use the arrow keys to select a command from the list, and press :kbd:`Enter` to run the selected command.

.. video:: ../_static/videos/notebook.using-the-command-palette.webm
   :width: 100%

|

Using the Command Bar
=====================

As an alternative to the searchable :term:`command palette`, the :term:`command bar` lets you type a command by name from a modal, single-line input at the bottom of the screen, inspired by the vim and helix command line. Summon it with :kbd:`:` or :kbd:`Alt+:`, type a command name (tab-completion is available), and press :kbd:`Enter` to run it. Unrecognised commands are rejected, and previously entered commands are kept in a searchable history.

Prefix the input with ``!`` -- or summon the bar directly with :kbd:`Alt+!` -- to run a system shell command. Close the command bar without running anything with :kbd:`Escape` or :kbd:`Ctrl+C`.

.. video:: ../_static/videos/notebook.using-the-command-bar.webm
   :width: 100%

|

----

**********************
Command Line Interface
**********************

.. include:: ../_inc/cli_flags.rst
   :start-after: .. _cli-euporie-notebook-start:
   :end-before: .. _cli-euporie-notebook-end:

----


******************
Available Commands
******************

.. toctree::

   notebook_commands
