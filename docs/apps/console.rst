###############
Euporie Console
###############

Euporie console is a terminal frontend for Jupyter kernels, allowing code to be executed interactively and rich output to be displayed.


.. video:: https://user-images.githubusercontent.com/12154190/185399185-55af7414-26ce-403d-b47f-7dda4d74f053.webm
   :width: 100%

|

Euporie console makes use of terminal graphics capabilities to display images, and will render markdown, LaTeX, and :py:mod:`ipywidgets`.

The command palette can be summoned with :kbd:`Ctrl+Space`, which provides access to settings and various operations from within the console.


**********
User Guide
**********

Multi-line editing
==================

The console will check the current input for completeness when the cursor is at the end of the input and :kbd:`Enter` is pressed. If the input is determined to be incomplete, a new line will be inserted. Otherwise, the input will be executed.

If two blank lines are entered at the end of the input, the input will be executed.

A new-line can be inserted without checking the input for completeness using :kbd:`Shift+Enter`.

The input can be executed immediately using :kbd:`Ctrl+Enter` (providing your terminal :ref:`suports this key-binding <pages/keybindings:running cells>`; you can also use :kbd:`Ctrl+e`).

Save console session as a notebook
==================================

Running the ``save-as`` command from the command palette will prompt you to save the input and output history of the current console session as a Jupyter notebook file.

Convert console session to a notebook
=====================================

Running the ``convert-to-notebook`` command from the command palette will transform the input and output history of the current console session into a euporie notebook, and open it with :doc:`Euporie Notebook <notebook>`, reusing the existing kernel connection.

----

**********************
Command Line Interface
**********************

.. include:: ../_inc/cli_flags.rst
   :start-after: .. _cli-euporie-console-start:
   :end-before: .. _cli-euporie-console-end:
