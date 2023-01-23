################
Euporie Notebook
################

In euporie's notebooks editor, you can interactively edit and run Jupyter noteboks from the comfort of your terminal.

Euporie supports most of the features of Jupyter Notebooks, so users of Jupyter should find it intuitive to use.

**********
User Guide
**********

Creating a New Notebook
=======================

To create a new notebook from the command line, launch euporie with the desired new notebook file path as an argument:

.. code-block:: console

   $ euporie-notebook ./my-new-notebook.ipynb

To create a new notebook from within the TUI editor, select :menuselection:`File --> New` in the menus, or press the :kbd:`Ctrl+N` keyboard shortcut.

.. video:: https://user-images.githubusercontent.com/12154190/183309071-7ba7ce34-47c7-44a6-9aea-7528e6991cc6.webm
   :width: 100%

|

Editing a Cell
==============

The currently selected cell can be edited by pressing :kbd:`Enter`, which will enter :term:`Edit Mode`. This focuses the cell's input text area, and allows you to edit the cell's content.

To exit :term:`Edit Mode`, you can press the :kbd:`Esc` key when you are done editing, or you can run the cell.

.. video:: https://user-images.githubusercontent.com/12154190/183309631-b5aeb44a-1f49-4cba-b9d7-54943bfea838.webm
   :width: 100%

|

Running a Cell
==============

To run the currently selected cell, you can press :kbd:`Ctrl+Enter` (providing your terminal :ref:`suports this key-binding <pages/keybindings:running cells>`; you can also use :kbd:`Ctrl+e`).

Alternatively, you can select :menuselection:`Run --> Run selected cells` in the menu.

.. video:: https://user-images.githubusercontent.com/12154190/183309637-878df143-c23d-43cf-9f03-5bec258284f6.webm
   :width: 100%

|

Opening an Existing Notebook
============================

To open a notebook from the command line, launch euporie with the notebook file path as an argument:

.. code-block:: console

   $ euporie-notebook ./my-notebook.ipynb

To open a notebook from within the TUI editor, select :menuselection:`File --> Open` in the menus, or press the :kbd:`Ctrl+O` keyboard shortcut. Enter the path of the notebook you wish to open into the file open dialog and press :guilabel:`OK`.

.. video:: https://user-images.githubusercontent.com/12154190/183309635-d905f5c6-bf00-46b1-bdb3-1ad00cc2368e.webm
   :width: 100%

|

Adding a new cell
=================

You can press :kbd:`b` to add a new cell below the currently selected cell. You can also press :kbd:`a` to add a new cell above the currently selected cell.

.. video:: https://user-images.githubusercontent.com/12154190/183309065-200115f5-851f-4a01-bb8c-e7072c3d8d4e.webm
   :width: 100%

|


Navigating the Notebook
=======================

When a notebook is open, the currently selected cell is highlighted with a blue border. The selected cell can be changed using the :kbd:`Up` and :kbd:`Down` arrow keys (or :kbd:`j` and :kbd:`k`). Selecting a cell which is not currently visible will automatically scroll it into view.

You can select the first or last cell the the :kbd:`Home` or :kbd:`End` keys.

The notebook can be scrolled up and down one line at a time using the :kbd:`[` and :kbd:`]` keys respectively. Use the :kbd:`{` and :kbd:`}` keys to scroll up or down by 5 lines. You can also scroll the notebook with the mouse wheel, or by clicking on the notebook's scroll bar.


.. video:: https://user-images.githubusercontent.com/12154190/183309070-84b2622d-6cf6-426a-b253-a97ef2bfa3cd.webm
   :width: 100%

|

Saving a Notebook
=================


To save a notebook, press :kbd:`Ctrl+S` or navigate to :menuselection:`File --> Save Notebook` in the menus.

.. video:: https://user-images.githubusercontent.com/12154190/183309075-8fc59ece-2aa5-4a80-b976-06ff0f9fd70f.webm
   :width: 100%

|

Closing a Notebook
==================

To save a notebook, press :kbd:`Ctrl+W` or navigate to :menuselection:`File --> Close File Notebook` in the menus.

.. video:: https://user-images.githubusercontent.com/12154190/183294494-6445d5a9-fa12-406d-a621-96244e01ce48.webm
   :width: 100%

|

Changing a Cell's Type
======================

To change the currently selected cells to:

* **code cells**, press :kbd:`y`;
* **markdown cells**, press :kbd:`m`;
* **raw cells**, press :kbd:`r`.

.. video:: https://user-images.githubusercontent.com/12154190/183309066-ff54ef27-f34b-4f65-a1ba-4b144f9d9ab5.webm
   :width: 100%

|

Restarting the Kernel
=====================

To restart the kernel, navigate to :menuselection:`Kernel --> Restart kernel` in the menus and select :guilabel:`Yes` in the confirmation dialog.

Alternatively, press the :kbd:`0 0` keyboard shortcut.

.. video:: https://user-images.githubusercontent.com/12154190/183309073-5a86b5df-43c7-43ff-a5e9-bddcbdff67aa.webm
   :width: 100%

|

Changing the Kernel
===================

To change a notebook's kernel, navigate to :menuselection:`Kernel --> Change kernel` in the menus.

.. video:: https://user-images.githubusercontent.com/12154190/183309067-272ef87d-b8e6-42bf-b7a5-72f834abcc15.webm
   :width: 100%

|

Setting the Color Scheme
========================

To change the color scheme, navigate to :menuselection:`Settings --> Color Scheme` in the menus, then select the color scheme name you want to use.

.. video:: https://user-images.githubusercontent.com/12154190/183309446-9df4c6f7-290e-434f-a286-7198df4f2ba8.webm
   :width: 100%

|

To configure the custom color scheme, use the :option:`custom_foreground_color` and  :option:`custom_background_color` configuration options.

Setting the Syntax Theme
========================

To change the syntax theme, navigate to :menuselection:`Settings --> Syntax Theme` in the menus, then select the syntax theme you want to use.

.. video:: https://user-images.githubusercontent.com/12154190/183313233-7f26f1e4-a3fe-4a71-9587-eb55a5ac7430.webm
   :width: 100%

|

Using the Command Palette
=========================

Practically every action in euporie (including all of those listed above) can be performed through the :term:`command palette`, which can be summoned using :kbd:`Ctrl+Space`. You can type in the input box to search for a command, use the arrow keys to select a command from the list, and press :kbd:`Enter` to run the selected command.

.. video:: https://user-images.githubusercontent.com/12154190/183313430-abf73ea5-0f36-4823-a6b9-ad1d47b8ec3f.webm
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
