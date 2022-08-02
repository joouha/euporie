###############
Notebook Editor
###############

In euporie's notebooks editor, you can interactively edit and run Jupyter noteboks from the comfort of your terminal.

Euporie supports most of the features of Jupyter Notebooks, so users of Jupyter should find it intuitive to use.

**********
User Guide
**********

Creating a New Notebook
=======================

To create a new notebook from the command line, launch euporie with the desired new notebook file path as an argument:

.. code-block:: console

   $ euporie edit ./my-new-notebook.ipynb

To create a new notebook from within the TUI editor, select :menuselection:`File --> New` in the menus, or press the :kbd:`Ctrl+N` keyboard shortcut. Enter the file path of the new notebook into the file new file dialog and press :guilabel:`OK`.

The file will be created when the notebooks is first saved.

.. figure:: https://user-images.githubusercontent.com/12154190/165352985-b8e6218f-6b2f-4625-8017-c295bb557748.png

Opening an Existing Notebook
============================

To open a notebook from the command line, launch euporie with the notebook file path as an argument:

.. code-block:: console

   $ euporie edit ./my-notebook.ipynb

To open a notebook from within the TUI editor, select :menuselection:`File --> Open` in the menus, or press the :kbd:`Ctrl+O` keyboard shortcut. Enter the path of the notebook you wish to open into the file open dialog and press :guilabel:`OK`.

.. figure:: https://user-images.githubusercontent.com/12154190/165352987-3b07e683-41c9-4569-9a4b-5b35c3ce3504.png

Adding a new cell
=================

You can press :kbd:`b` to add a new cell below the currently selected cell. You can also press :kbd:`a` to add a new cell above the currently selected cell.

.. figure:: https://user-images.githubusercontent.com/12154190/165352954-5df3162d-1942-4ad8-9f57-63a290201a15.png

Navigating the Notebook
=======================

When a notebook is open, the currently selected cell is highlighted with a blue border. The selected cell can be changed using the :kbd:`Up` and :kbd:`Down` arrow keys (or :kbd:`j` and :kbd:`k`). Selecting a cell which is not currently visible will automatically scroll it into view.

You can select the first or last cell the the :kbd:`Home` or :kbd:`End` keys.

The notebook can be scrolled up and down one line at a time using the :kbd:`[` and :kbd:`]` keys respectively. Use the :kbd:`{` and :kbd:`}` keys to scroll up or down by 5 lines. You can also scroll the notebook with the mouse wheel, or by clicking on the notebook's scroll bar.

.. figure:: https://user-images.githubusercontent.com/12154190/165352979-dd079c4e-7232-41ef-8189-4b680ef2acde.png

Editing a Cell
==============

The currently selected cell can be edited by pressing :kbd:`Enter`, which will enter :term:`Edit Mode`. This focuses the cell's input text area, and allows you to edit the cell's content.

To exit :term:`Edit Mode`, you can press the :kbd:`Esc` key when you are done editing, or you can run the cell.

.. figure:: https://user-images.githubusercontent.com/12154190/165352976-bd93e375-ada8-46e0-b37d-186a7fdbd4fd.png

Running a Cell
==============

To run the currently selected cell, you can press :kbd:`Ctrl+Enter` (providing your terminal :ref:`suports this key-binding <pages/keybindings:running cells>`; you can also use :kbd:`Ctrl+e`).

Alternatively, you can select :menuselection:`Run --> Run selected cells` in the menu.

.. figure:: https://user-images.githubusercontent.com/12154190/165352992-09f6428f-1877-4d13-a802-5927ba70d127.png

Changing a Cell's Type
======================

To change the currently selected cells to:

* **code cells**, press :kbd:`y`;
* **markdown cells**, press :kbd:`m`;
* **raw cells**, press :kbd:`r`.

.. figure:: https://user-images.githubusercontent.com/12154190/165352997-aa7f70cb-965b-4837-80b1-b8a48be08623.png

Restarting the Kernel
=====================

To restart the kernel, navigate to :menuselection:`Kernel --> Restart kernel` in the menus and select :guilabel:`Yes` in the confirmation dialog.

Alternatively, press the :kbd:`0 0` keyboard shortcut.

.. figure:: https://user-images.githubusercontent.com/12154190/165352990-3be81a04-360e-4393-83bd-c9af8818a26e.png

Changing the Kernel
===================

To change a notebook's kernel, navigate to :menuselection:`Kernel --> Change kernel` in the menus.

.. figure:: https://user-images.githubusercontent.com/12154190/165352962-2497248c-6eed-42fd-8cc4-d9a8606aa5c9.png

Setting the Color Scheme
========================

To change the color scheme, navigate to :menuselection:`Settings --> Color Scheme` in the menus, then select the color scheme name you want to use.

.. figure:: https://user-images.githubusercontent.com/12154190/165352964-75ee6a83-4fe0-4e57-b33b-2aba222c3ea3.png

To configure the custom color scheme, use the :option:`custom_foreground_color` and  :option:`custom_background_color` configuration options.

Setting the Syntax Theme
========================

To change the syntax theme, navigate to :menuselection:`Settings --> Syntax Theme` in the menus, then select the syntax theme you want to use.

.. figure:: https://user-images.githubusercontent.com/12154190/165352994-ec30f461-060d-4a65-8dfa-1e0659454f91.png

Using the Command Palette
=========================

Practically every action in euporie (including all of those listed above) can be performed through the :term:`command palette`, which can be summoned using :kbd:`Ctrl+Space`. You can type in the input box to search for a command, use the arrow keys to select a command from the list, and press :kbd:`Enter` to run the selected command.

.. figure:: https://user-images.githubusercontent.com/12154190/165352968-e6758691-5b31-4cd0-94c3-6bc094e4e001.png
