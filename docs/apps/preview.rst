################
Notebook Preview
################

Euporie can be used to render notebooks in the terminal, which is useful for quickly previewing notebook files.

For more information about the command line options available for the :option:`preview` sub-command, see the command line reference for the :ref:`preview-subcommand`.

**********
User Guide
**********

Preview a Notebook in the Terminal
==================================

To print a notebook to the terminal, run:

.. code-block:: console

   $ euporie-preview notebook.ipynb


Preview a Notebook in the System Pager
======================================

To view a notebook in the system pager, run:

.. code-block:: console

   $ euporie-preview --page notebook.ipynb

You can also pipe the output to the pager of your choice:

.. code-block:: console

   $ euporie-preview --color-depth=24 notebook.ipynb | bat

.. note::

   By default euporie will select a color-depth to use which is suitable for the environment it is running in. This means if you are piping its output, the color depth will be set to ``1``.
   If your pager supports colored output, you can manually specify the color-depth with the :option:`color_depth` configuration option.


Run a Notebook Before Previewing
================================

To run a notebook before the preview is generated, use the :option:`--run` flag:

.. code-block:: console

   $ euporie-preview --run notebook.ipynb


Preview a subset of cells
=========================

To show a subset of the cells in the notebook, the :option:`--cell-start` and :option:`--cell-end` flags can be used:

.. code-block:: console

   $ euporie-preview --cell-start=3 --cell-end=6 notebook.ipynb


Save a Notebook After Running
=============================

To save a notebook after it has been run, use the :option:`--save` flag with the :option:`--run` flag:

.. code-block:: console

   $ euporie-preview --run --save notebook.ipynb


Use as a previewer with :program:`ranger`
=========================================

Euporie can be used to preview notebook files in terminal file managers like :program:`ranger`.

To configure :program:`ranger` for this, add the following to the ``handle_extension`` function in your :file:`scope.sh` file:

.. code-block:: bash
   :emphasize-lines: 8-10

   # ...

   handle_extension() {
       case "${FILE_EXTENSION_LOWER}" in

           # ...

           ## Notebook
           ipynb)
               euporie-preview --color-depth=8 "${FILE_PATH}" && exit 4
       esac
   }

   # ...

You can also add the following line to your :file:`rifle.conf` file if you want notebook files to open in euporie:

.. code-block:: conf

   ext ipynb,           has euporie-notebook,      terminal = euporie-notebook "$@"


----

**********************
Command Line Interface
**********************

.. include:: ../_inc/cli_flags.rst
   :start-after: .. _cli-euporie-hub-start:
   :end-before: .. _cli-euporie-hub-end:
