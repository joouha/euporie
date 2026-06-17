############
euporie-core
############

**Shared core library for the euporie suite of terminal Jupyter applications.**

.. image:: https://placehold.co/1200x400/1e1e1e/cccccc.png?text=euporie-core+%E2%80%94+screenshot+placeholder
   :alt: euporie-core screenshot placeholder
   :align: center

.. content_start

``euporie-core`` is the foundation library shared by every euporie application
(`euporie-notebook <../euporie-notebook>`_, `euporie-console <../euporie-console>`_,
`euporie-preview <../euporie-preview>`_ and `euporie-hub <../euporie-hub>`_).
It is built on top of `apptk <../apptk>`_ and provides the application
framework, Jupyter kernel integration, notebook handling and rich-output
rendering used throughout the suite.

This package does not ship a command-line application of its own - it is a
library intended to be consumed by the other euporie packages or by third-party
tooling that wants to embed euporie components.

----

********
Features
********

* **Application framework**: ``BaseApp`` class providing the common application
  loop, configuration, key bindings and command palette
* **Jupyter kernel client**: kernel discovery, lifecycle management and
  message handling via ``jupyter-client``
* **Notebook handling**: read/write ``.ipynb`` files and Jupytext-compatible
  formats via ``nbformat`` and ``jupytext``
* **Rich kernel output rendering**: markdown, LaTeX, HTML, SVG, PDF, tables,
  and images (Sixel / iTerm / Kitty terminal graphics)
* **Jupyter widgets**: interactive ``ipywidgets`` rendered in the terminal
* **Language Server Protocol client**: completion, diagnostics and formatting
* **Configuration system**: settings driven by CLI flags, config files
  (``pyproject.toml``-style) and environment variables
* **Filesystem abstraction**: ``fsspec`` / ``universal-pathlib`` integration
  for local, HTTP and in-memory paths
* **Color schemes & syntax themes**: light, dark, inverse and custom palettes
  with terminal colour detection
* **Reusable widgets**: dialogs, menus, toolbars, pagers, search bars and
  cell-output containers

*******
Install
*******

``euporie-core`` is published on PyPI:

.. code-block:: console

   $ uv pip install euporie-core
   $ # OR
   $ python -m pip install euporie-core

It requires Python 3.10 or later.

In most cases you should install one of the end-user applications instead,
which will pull in ``euporie-core`` automatically:

.. code-block:: console

   $ uv tool install euporie

*****
Usage
*****

``euporie-core`` is a library. A minimal application built on top of it looks
like:

.. code-block:: python

   from euporie.core.app.base import BaseApp

   class MyApp(BaseApp):
       name = "my-app"

   if __name__ == "__main__":
       MyApp.launch()

Refer to the source of the other ``euporie-*`` packages for more complete
examples of how to build apps on this framework.

*************
Documentation
*************

* Project documentation: https://euporie.readthedocs.io/
* Source code: https://github.com/joouha/euporie

*******
License
*******

Distributed under the terms of the MIT license. See the
`LICENSE <https://github.com/joouha/euporie/blob/main/LICENSE>`_ file in the
project root for details.
