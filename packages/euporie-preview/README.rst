###############
euporie-preview
###############

**Render Jupyter notebooks to the terminal - non-interactively.**

.. image:: https://placehold.co/1200x400/1e1e1e/cccccc.png?text=euporie-preview+%E2%80%94+screenshot+placeholder
   :alt: euporie-preview screenshot placeholder
   :align: center

.. content_start

``euporie-preview`` is a non-interactive notebook renderer that writes a
formatted view of an ``.ipynb`` file to the terminal (or to a file). It is
ideal for quick previews, file-manager integrations and CI pipelines, and is
part of the `euporie <https://github.com/joouha/euporie>`_ suite, built on
`euporie-core <../euporie-core>`_.

----

********
Features
********

* **Static rendering** of notebooks to stdout, a pager or a file
* **Rich output**: images, Markdown, LaTeX, HTML, tables and PDFs
* **Optional execution**: run a notebook before previewing, and optionally
  save the executed result
* **Cell range selection**: preview only a subset of cells
* **Multiple notebooks** in one invocation, with optional filename headers
* **Pager integration**: pipe output through ``less``, ``bat`` or any other
  pager
* **Configurable colour depth** for piping into other tools
* **File-manager friendly**: works as a previewer in tools like ``ranger``

*******
Install
*******

.. code-block:: console

   $ uv tool install euporie-preview
   $ # OR
   $ pipx install euporie-preview
   $ # OR
   $ python -m pip install --user euporie-preview

Requires Python 3.10 or later.

*****
Usage
*****

Preview a notebook directly to the terminal:

.. code-block:: console

   $ euporie-preview notebook.ipynb

Open the preview in your system pager:

.. code-block:: console

   $ euporie-preview --page notebook.ipynb

Pipe to ``bat`` with 24-bit colour:

.. code-block:: console

   $ euporie-preview --color-depth=24 notebook.ipynb | bat

Run the notebook before previewing, and save the executed result:

.. code-block:: console

   $ euporie-preview --run --save notebook.ipynb

Preview a specific range of cells:

.. code-block:: console

   $ euporie-preview --cell-start=3 --cell-stop=6 notebook.ipynb

.. getting_started_end

*************
Documentation
*************

* App documentation: https://euporie.readthedocs.io/en/latest/packages/preview.html
* Project documentation: https://euporie.readthedocs.io/
* Source code: https://github.com/joouha/euporie

********
See also
********

* `euporie-notebook <../euporie-notebook>`_ - full TUI notebook editor
* `euporie-console <../euporie-console>`_ - interactive Jupyter console
* `euporie-hub <../euporie-hub>`_ - multi-user SSH server for euporie apps

*******
License
*******

Distributed under the terms of the MIT license. See the
`LICENSE <https://github.com/joouha/euporie/blob/main/LICENSE>`_ file in the
project root for details.
