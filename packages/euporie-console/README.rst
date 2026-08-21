###############
euporie-console
###############

**An interactive Jupyter console for the terminal, with rich output.**

.. image:: https://raw.githubusercontent.com/joouha/euporie/main/docs/_static/images/console.hero.screenshot.webp
   :alt: euporie-console screenshot
   :align: center

.. content_start

``euporie-console`` is a terminal-based Jupyter REPL that renders rich kernel output - including images, tables, Markdown, LaTeX and ``ipywidgets`` - directly in the terminal. It is part of the `euporie <https://github.com/joouha/euporie>`_ suite and is built on `euporie-core <../euporie-core>`_.

----

********
Features
********

* **Interactive REPL** against any Jupyter kernel
* **Rich output rendering**: images, Markdown, LaTeX, HTML, tables and PDFs
* **Interactive** :py:mod:`ipywidgets` in the terminal
* **Multi-line editing** with kernel-aware completeness detection
* **Tab-completion**, line suggestions and contextual help
* **Command palette** for discoverable actions
* **Connect to existing kernels** via a Jupyter connection file
* **Session export**: save the current console session as an ``.ipynb`` notebook, or hand it off to ``euporie-notebook`` to keep editing
* **History** sourced from the kernel
* **Vim, Emacs, Helix, and Micro-style** key bindings

*******
Install
*******

.. code-block:: console

   $ uv tool install euporie-console
   $ # OR
   $ pipx install euporie-console
   $ # OR
   $ python -m pip install --user euporie-console

Requires Python 3.10 or later.

*****
Usage
*****

Start a new console session with the default kernel:

.. code-block:: console

   $ euporie-console

Connect to an existing kernel using its connection file:

.. code-block:: console

   $ euporie-console --connection-file /path/to/kernel-1234.json

Press ``Ctrl+C`` to open the command palette and discover available actions.

.. getting_started_end

*************
Documentation
*************

* App documentation: https://euporie.readthedocs.io/en/latest/packages/console.html
* Project documentation: https://euporie.readthedocs.io/
* Source code: https://github.com/joouha/euporie

********
See also
********

* `euporie-notebook <../euporie-notebook>`_ - full TUI notebook editor
* `euporie-preview <../euporie-preview>`_ - non-interactive notebook renderer
* `euporie-hub <../euporie-hub>`_ - multi-user SSH server for euporie apps

*******
License
*******

Distributed under the terms of the MIT license. See the `LICENSE <https://github.com/joouha/euporie/blob/main/LICENSE>`_ file in the project root for details.
