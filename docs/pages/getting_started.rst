###############
Getting started
###############

This page walks you through installing euporie, running each of the :term:`apps <App>`, and performing a few common tasks. It should take about five minutes.

If you've never used euporie before, this is the place to start.

***************
Install euporie
***************

If you have `uv <https://docs.astral.sh/uv/>`_ installed, the quickest way to get started is:

.. code-block:: console

   $ uv tool install euporie

This pulls in :command:`euporie-notebook`, :command:`euporie-console` and :command:`euporie-preview` along with the :command:`euporie` launcher. Other install methods are documented in :doc:`installation`.

If you would rather not install euporie permanently, you can run any :term:`app <App>` without installing it using :command:`uvx`:

.. code-block:: console

   $ uvx euporie notebook

****************
A first notebook
****************

Create a new notebook:

.. code-block:: console

   $ euporie-notebook hello.ipynb

Assuming the file :file:`hello.ipynb` does not exist yet, the notebook editor will open with a single empty code :term:`cell` selected.

To **edit** the :term:`cell`, press :kbd:`Enter`. The cursor moves into the cell text area; type some Python:

.. code-block:: python

   print("Hello from euporie!")
   2 + 2

Press :kbd:`Esc` to leave :term:`edit mode`, then :kbd:`Ctrl+e` (or :kbd:`Ctrl+Enter` if your terminal supports it - see :ref:`pages/keybindings:running cells`) to run the :term:`cell`. The output appears underneath the cell.

To add another :term:`cell` **below**, press :kbd:`b`. Press :kbd:`Enter` again to edit it; try displaying an image:

.. code-block:: python

   from PIL import Image
   import urllib.request, io
   url = "https://raw.githubusercontent.com/joouha/euporie-binder/main/euporie-logo.png"
   Image.open(io.BytesIO(urllib.request.urlopen(url).read()))

Run the :term:`cell`. If your terminal supports :term:`terminal graphics` (kitty, iTerm2, WezTerm, foot, recent xterm, etc.) you'll see the image rendered inline. If not, euporie will fall back to ANSI art. See :doc:`guides/terminal_graphics` for details.

Save with :kbd:`Ctrl+S`, then close with :kbd:`Ctrl+W` (or :kbd:`Ctrl+Q` to quit the :term:`app <App>`).

***********
The console
***********

For quick experiments without saving anything to disk, launch the console:

.. code-block:: console

   $ euporie-console

Type Python expressions and press :kbd:`Enter`. Multi-line input is supported - if your input is incomplete (e.g. inside a function definition) :kbd:`Enter` will insert a new line; otherwise it will execute. Use :kbd:`Ctrl+Enter` (or :kbd:`Ctrl+e`) to force execution.

Press :kbd:`Ctrl+Space` to open the :term:`command palette` - a searchable list of every action available in the current context. Try typing ``save`` and selecting :option:`save-as` to dump the console session to a notebook file.

Press :kbd:`Ctrl+D` (or use the :option:`quit` :term:`command`) to exit.

********************
Previewing notebooks
********************

To print a notebook's contents directly to your terminal without an interactive UI:

.. code-block:: console

   $ euporie-preview hello.ipynb

This is handy for quick inspection from a shell, for piping into a :term:`pager` (``euporie-preview --page hello.ipynb``), or for using as a previewer in a file manager such as `ranger <https://github.com/ranger/ranger>`_.

You can also execute the notebook before previewing it with :option:`--run`, which makes ``euporie-preview`` useful in CI jobs that need to validate notebooks.

See the :doc:`../packages/preview` reference for the full set of preview options.

***************
What next?
***************

* :doc:`overview` - a tour of all four apps and the libraries underneath them
* :doc:`configuration` - how to persist settings via a config file or
  environment variables
* :doc:`keybindings` - default key bindings and how to customise them
* :doc:`guides/terminal_graphics` - how images are rendered in your terminal
  and how to troubleshoot when they don't appear
* :doc:`guides/kernels` - install and connect to non-Python Jupyter kernels
* :doc:`troubleshooting` - solutions to common issues
