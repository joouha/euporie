|logo|

.. |logo| image:: https://user-images.githubusercontent.com/12154190/160670889-c6fc4cd8-413d-49f0-b105-9c0e03117032.svg
   :alt: <Logo>

#######
euporie
#######

|PyPI| |RTD| |License| |Stars| |TryOnline|

.. content_start

**Euporie is a terminal based interactive computing environment for Jupyter.**

Euporie's apps allow you to interact with Jupyter kernels, and run Jupyter notebooks - entirely from the terminal.

If you're working with Jupyter notebooks in a terminal only environment, like an SSH server or a container, or just prefer working in the terminal, then euporie is the tool for you!

.. image:: https://github.com/joouha/euporie/assets/12154190/c8ea6e23-11bb-4ffc-a9e5-111f788c51ae
   :target: https://github.com/joouha/euporie/assets/12154190/c8ea6e23-11bb-4ffc-a9e5-111f788c51ae

.. list-table::
   :align: center
   :widths: 25 25 25 25
   :class: text-center

   * - `Console <https://euporie.readthedocs.io/en/latest/packages/console.html>`_
     - `Notebook <https://euporie.readthedocs.io/en/latest/packages/notebook.html>`_
     - `Preview <https://euporie.readthedocs.io/en/latest/packages/preview.html>`_
     - `Hub <https://euporie.readthedocs.io/en/latest/packages/hub.html>`_

`View more screenshots here <https://euporie.readthedocs.io/en/latest/pages/gallery.html>`_

----

************
Try euporie
************

**In your terminal** - if you have `uv <https://docs.astral.sh/uv/>`_ installed,
you can run any euporie app instantly without installing it, using ``uvx``:

.. code-block:: console

   $ uvx euporie notebook            # launch the notebook editor
   $ uvx euporie notebook my.ipynb   # ...optionally with a notebook to open
   $ uvx euporie console             # interactive Jupyter console
   $ uvx euporie preview my.ipynb    # render a notebook to the terminal

**In your browser** - no installation required:
`launch the live demo <https://euporie.readthedocs.io/en/latest/_static/lite.html>`_.

If you'd rather install euporie permanently, see `Install`_ below.

----

*******
Install
*******

For day-to-day use, install euporie with `uv <https://docs.astral.sh/uv/>`_
(recommended), `pipx <https://pipxproject.github.io/>`_ or ``pip``:

.. code-block:: console

   $ uv tool install euporie
   $ # OR
   $ pipx install euporie
   $ # OR
   $ python -m pip install --user euporie

You can also run euporie without installing it - see `Try euporie`_ above.

********
Features
********

* Edit and run notebooks in the terminal
* Run code interactively in a console
* Display images using terminal graphics (sixel / iterm / kitty)
* Use Jupyter widgets interactively in the terminal
* Render rich kernel output (markdown, tables, images, LaTeX, HTML, SVG, & PDF)
* Tab-completion, line suggestions  and contextual help
* Convert a console session to a notebook
* Micro / Vim / Emacs style key-bindings

**********
Packages
**********

Euporie is structured as a collection of packages, allowing you to install only the components you need:

* `euporie <https://euporie.readthedocs.io/>`_ - Metapackage which installs all euporie apps and provides the ``euporie`` launcher command
* `euporie-core <https://euporie.readthedocs.io/en/latest/packages/euporie-core.html>`_ - Core functionality shared across all apps (config system, kernel client, LSP client, shared widgets, and rich output rendering)
* `euporie-console <https://euporie.readthedocs.io/en/latest/packages/euporie-console.html>`_ - Interactive console application
* `euporie-notebook <https://euporie.readthedocs.io/en/latest/packages/euporie-notebook.html>`_ - Notebook editing application
* `euporie-preview <https://euporie.readthedocs.io/en/latest/packages/euporie-preview.html>`_ - Notebook preview application
* `euporie-hub <https://euporie.readthedocs.io/en/latest/packages/euporie-hub.html>`_ - Multi-user SSH server for euporie apps
* `apptk <https://euporie.readthedocs.io/en/latest/packages/apptk.html>`_ - Terminal UI toolkit extending ``prompt_toolkit``, used by euporie

Installing the ``euporie`` metapackage will pull in ``euporie-console``, ``euporie-notebook``, and ``euporie-preview``. To install an individual app, install its package directly, e.g.:

.. code-block:: console

   $ uv tool install euporie-notebook

*****
Usage
*****

**Launcher**

   The ``euporie`` command acts as a launcher for the various euporie apps:

   .. code-block:: console

      $ euporie notebook notebook.ipynb
      $ euporie console
      $ euporie preview notebook.ipynb
      $ euporie hub

   If you don't want to install euporie, you can run any of these commands
   directly with ``uvx`` (e.g. ``uvx euporie notebook notebook.ipynb``) - see
   `Try euporie`_.

**Notebooks**

   You can edit a notebook using ``euporie-notebook``, and passing the notebook's file path or URI as a command line argument:

   .. code-block:: console

      $ euporie-notebook notebook.ipynb

   Alternatively, launch ``euporie-notebook`` and open a notebook file by selecting "Open" from the file menu (``Ctrl+O``).

**Console**

   To connect to a Jupyter kernel and run code interactively in a console session, you can run

   .. code-block:: console

      $ euporie-console

   (You can press ``Ctrl+Space`` to open the command palette in ``euporie-console``).

**Preview**

   To preview a notebook to the terminal, use the ``euporie-preview`` subcommand:

   .. code-block:: console

      $ euporie-preview notebook.ipynb

**Hub**

   To run euporie hub, a multi-user SSH server for euporie apps, run:

   .. code-block:: console

      $ euporie-hub --port 8022 --host-keys=ssh_host_ed25519_key --client-keys=authorized_keys

   where ``ssh_host_ed25519_key`` is the path to your host key file, and ``authorized_keys`` is a file containing SSH public keys allowed to connect.

*************
Documentation
*************

View the online documentation at: `https://euporie.readthedocs.io/ <https://euporie.readthedocs.io/>`_

The code is available on GitHub at: `https://github.com/joouha/euporie <https://github.com/joouha/euporie>`_

***********
Development
***********

Euporie is developed as a `uv <https://docs.astral.sh/uv/>`_ workspace mono-repo. The individual packages live under ``packages/``. To set up a development environment:

.. code-block:: console

   $ git clone https://github.com/joouha/euporie
   $ cd euporie
   $ uv sync

*************
Compatibility
*************

Euporie requires Python 3.10 or later. It works on Linux, Windows and MacOS



.. |PyPI| image:: https://img.shields.io/pypi/v/euporie.svg
    :target: https://pypi.python.org/project/euporie/
    :alt: Latest Version

.. |RTD| image:: https://readthedocs.org/projects/euporie/badge/
    :target: https://euporie.readthedocs.io/en/latest/
    :alt: Documentation

.. |PyVer| image:: https://img.shields.io/pypi/pyversions/euporie
    :target: https://pypi.python.org/project/euporie/
    :alt: Supported Python versions

.. |TryOnline| image:: https://img.shields.io/badge/Try%20it%20online-%E2%96%B6%20Launch%20demo-success?style=for-the-badge&logo=jupyter
   :target: https://euporie.readthedocs.io/en/latest/_static/lite.html
   :alt: Try euporie online in your browser

.. |License| image:: https://img.shields.io/github/license/joouha/euporie.svg
    :target: https://github.com/joouha/euporie/blob/main/LICENSE
    :alt: View license

.. |Stars| image:: https://img.shields.io/github/stars/joouha/euporie
    :target: https://github.com/joouha/euporie/stargazers
    :alt: ⭐
