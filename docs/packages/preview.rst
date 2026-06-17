################
Notebook Preview
################

.. include:: ../../packages/euporie-preview/README.rst
   :start-after: .. content_start
   :end-before: .. getting_started_end

----

**********
User Guide
**********

Color Depth When Piping
=======================

By default euporie will select a color-depth to use which is suitable for the environment it is running in. This means if you are piping its output, the color depth will be set to ``1``.

If your pager supports colored output, you can manually specify the color-depth with the :option:`color_depth` configuration option:

.. code-block:: console

   $ euporie-preview --color-depth=24 notebook.ipynb | bat


Save a Notebook After Running
=============================

To save a notebook after it has been run, use the :option:`--save` flag with the :option:`--run` flag:

.. code-block:: console

   $ euporie-preview --run --save notebook.ipynb


Use as a Previewer with :program:`ranger`
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

.. code-block:: text

   ext ipynb,           has euporie-notebook,      terminal = euporie-notebook "$@"


----

**********************
Command Line Interface
**********************

.. include:: ../_inc/cli_flags.rst
   :start-after: .. _cli-euporie-preview-start:
   :end-before: .. _cli-euporie-preview-end:

----

******************
Available Commands
******************

.. toctree::

   preview_commands
