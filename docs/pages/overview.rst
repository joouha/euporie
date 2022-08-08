########
Overview
########

Euporie consists of four applications, each providing different functionality:


:doc:`Euporie Notebook <../apps/notebook>`
   This is an interactive TUI Jupyter Notebook editor, which runs in the terminal and allows you to view, edit and run Jupyter Notebooks. It makes full use of Jupyter's `rich output system <https://ipython.readthedocs.io/en/stable/interactive/plotting.html#rich-outputs>`, and is able to render a range of media in the terminal.

:doc:`Euporie Console <../apps/preview>`
   This is a terminal frontend for kernels using the Jupyter protocol, which makes use of euporie's rich display system for kernel output. It is capable for displaying interactive widgets using :py:mod:`ipywidgets`. You can convert the history of a console session to a notebook.

:doc:`Euporie Preview <../apps/preview>`
   This allows you to preview notebooks in the terminal without opening them in the editor. The rendered notebook output can be printed to the standard output, piped to a pager, or saved to a file. You can also run notebooks before rendering them.

:doc:`Euporie Hub <../apps/hub>`
   This allows you to run euporie as a multi-user SSH server, meaning that multiple users can share a server's resources. Each connected user is presented with the euporie editor interface, and can use it to open, run and edit notebooks.

----



**********************
Command Line Interface
**********************

In addition to being launched directly, each application in eurporie can be launched by passing its name as an argument to the :command:`euporie` command.

.. include:: ../_inc/cli_flags.rst
   :start-after: .. _cli-euporie-start:
   :end-before: .. _cli-euporie-end:
