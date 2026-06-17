########
Overview
########

Euporie is a collection of terminal applications for working with Jupyter notebooks and kernels, plus the libraries those applications are built on.

************
Applications
************

:doc:`Euporie Notebook <../packages/notebook>`
   An interactive TUI Jupyter Notebook editor that runs in the terminal and allows you to view, edit and run Jupyter Notebooks. It makes full use of Jupyter's `rich output system <https://ipython.readthedocs.io/en/stable/interactive/plotting.html#rich-outputs>`_ and is able to render a wide range of media in the terminal.

:doc:`Euporie Console <../packages/console>`
   A terminal frontend for Jupyter kernels which uses euporie's rich display system for kernel output. It is capable of displaying interactive widgets using :py:mod:`ipywidgets`. You can convert the history of a console session into a notebook.

:doc:`Euporie Preview <../packages/preview>`
   A non-interactive notebook renderer for previewing notebooks in the terminal without opening them in the editor. The rendered output can be printed to standard output, piped to a pager, or saved to a file. You can also run notebooks before rendering them.

:doc:`Euporie Hub <../packages/hub>`
   A multi-user SSH server, akin to JupyterHub, that lets multiple users share a server's resources. Each connected user is presented with the :doc:`notebook editor <../packages/notebook>` (although which application is launched is configurable) and can use it to open, run and edit notebooks.

----

*****************
Libraries
*****************

Beyond the end-user apps, euporie ships two libraries that you can use to build your own terminal applications on top of:

:doc:`euporie-core <../packages/euporie-core>`
   The shared application framework, kernel client, notebook handling and rich-output rendering used by every euporie app.

:doc:`apptk <../packages/apptk>`
   An extension/enhancement layer over :py:mod:`prompt_toolkit` that adds docking, terminal graphics, an enriched style system, a centralised command registry and more.

See :doc:`../development/extending` for an introduction to building apps on these libraries, and :doc:`../development/architecture` for the overall package layout.

----

**********************
Command Line Interface
**********************

Each application can be launched directly (:command:`euporie-notebook`, :command:`euporie-console`, :command:`euporie-preview` or :command:`euporie-hub`), or via the top-level :command:`euporie` launcher:

.. code-block:: console

   $ euporie notebook my.ipynb
   $ euporie console
   $ euporie preview my.ipynb
   $ euporie hub

A full list of command line flags follows. See :doc:`cli` for the equivalent options for each subcommand.

.. include:: ../_inc/cli_flags.rst
   :start-after: .. _cli-euporie-start:
   :end-before: .. _cli-euporie-end:
