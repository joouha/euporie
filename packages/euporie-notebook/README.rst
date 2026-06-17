################
euporie-notebook
################

**Edit and run Jupyter notebooks in the terminal - the flagship euporie app.**

.. image:: https://placehold.co/1200x400/1e1e1e/cccccc.png?text=euporie-notebook+%E2%80%94+screenshot+placeholder
   :alt: euporie-notebook screenshot placeholder
   :align: center

.. content_start

``euporie-notebook`` is a full-featured TUI for editing and executing Jupyter
notebooks entirely from the terminal. It is part of the
`euporie <https://github.com/joouha/euporie>`_ suite and is built on
`euporie-core <../euporie-core>`_.

----

********
Features
********

* **Full notebook editing**: create, edit, run and save ``.ipynb`` notebooks
* **Code, Markdown and raw cells** with syntax highlighting and inline rendering
* **Tabbed, dockable interface** for working with multiple notebooks at once
* **Side bar** with file browser, table of contents, mini-map and variable
  explorer
* **Rich output rendering**: images, Markdown, LaTeX, HTML, tables and PDFs
* **Interactive ``ipywidgets``** support
* **Code intelligence**: auto-completion, suggestions, formatting,
  inspection and bracket pairing
* **Kernel management**: switch, restart and interrupt kernels
* **External editor integration** via ``$EDITOR``
* **Find and replace** across the notebook
* **Cell-level undo/redo**
* **Multiple colour schemes and syntax themes** (light, dark, white, black,
  inverse, custom)
* **Vim, Emacs and Micro-style** key bindings, plus a discoverable command
  palette

*******
Install
*******

.. code-block:: console

   $ uv tool install euporie-notebook
   $ # OR
   $ pipx install euporie-notebook
   $ # OR
   $ python -m pip install --user euporie-notebook

Requires Python 3.10 or later.

*****
Usage
*****

Open a notebook directly:

.. code-block:: console

   $ euporie-notebook notebook.ipynb

Or launch the app and open a notebook from the file menu (``Ctrl+O``):

.. code-block:: console

   $ euporie-notebook

************
Key bindings
************

A small selection of common bindings:

=====================  =========================================
Key                    Action
=====================  =========================================
``Ctrl+N``             New notebook
``Ctrl+O``             Open notebook
``Ctrl+S``             Save notebook
``Ctrl+W``             Close notebook
``Ctrl+Space``         Command palette
``Enter``              Edit cell
``Ctrl+Enter``         Run cell
``a`` / ``b``          Add cell above / below
``y`` / ``m`` / ``r``  Change cell type to code / markdown / raw
``j`` / ``k``          Navigate cells (or arrow keys)
``00``                 Restart kernel
=====================  =========================================

For the full list of shortcuts, open **Help → Keyboard Shortcuts** from the
menu bar inside the app, or press ``Ctrl+Space`` to browse every command in
the command palette.

.. getting_started_end

*************
Documentation
*************

* App documentation: https://euporie.readthedocs.io/en/latest/packages/notebook.html
* Project documentation: https://euporie.readthedocs.io/
* Source code: https://github.com/joouha/euporie

********
See also
********

* `euporie-console <../euporie-console>`_ - interactive Jupyter console
* `euporie-preview <../euporie-preview>`_ - non-interactive notebook renderer
* `euporie-hub <../euporie-hub>`_ - multi-user SSH server for euporie apps

*******
License
*******

Distributed under the terms of the MIT license. See the
`LICENSE <https://github.com/joouha/euporie/blob/main/LICENSE>`_ file in the
project root for details.
