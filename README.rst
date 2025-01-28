|logo|

.. |logo| image:: https://user-images.githubusercontent.com/12154190/160670889-c6fc4cd8-413d-49f0-b105-9c0e03117032.svg
   :alt: <Logo>

#######
euporie
#######

|PyPI| |RTD| |PyVer| |License| |Binder| |Stars|

.. content_start

**Euporie is a terminal based interactive computing environment for Jupyter.**

Euporie's apps allow you to interact with Jupyter kernels, and run Jupyter notebooks - entirely from the terminal.

If you're working with Jupyter notebooks in a terminal only environment, like an SSH server or a container, or just prefer working in the terminal, then euporie is the tool for you!

.. list-table::
   :align: center
   :widths: 25 25 25 25
   :class: text-center

   * - `Console <https://euporie.readthedocs.io/en/latest/apps/console.html>`_
     - `Notebook <https://euporie.readthedocs.io/en/latest/apps/notebook.html>`_
     - `Preview <https://euporie.readthedocs.io/en/latest/apps/preview.html>`_
     - `Hub <https://euporie.readthedocs.io/en/latest/apps/hub.html>`_

.. image:: https://github.com/joouha/euporie/assets/12154190/c8ea6e23-11bb-4ffc-a9e5-111f788c51ae
   :target: https://github.com/joouha/euporie/assets/12154190/c8ea6e23-11bb-4ffc-a9e5-111f788c51ae

`View more screenshots here <https://euporie.readthedocs.io/en/latest/pages/gallery.html>`_

----

*******
Install
*******

You can install euporie with `uv <https://docs.astral.sh/uv/>`_  (recommended), or with `pipx <https://pipxproject.github.io/>`_ or ``pip``):

.. code-block:: console

   $ uv tool install euporie
   $ # OR
   $ pipx install euporie
   $ # OR
   $ python -m pip install --user euporie

You can also try euporie online `here <https://mybinder.org/v2/gh/joouha/euporie-binder/HEAD?urlpath=%2Feuporie%2F>`_.

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

*****
Usage
*****

**Notebooks**

   You can edit a notebook using ``euporie-notebook``, and passing the notebook's file path or URI as a command line argument:

   .. code-block:: console

      $ euporie-notebook notebook.ipynb

   Alternatively, launch ``euporie-notebooks`` and open a notebook file by selecting "Open" from the file menu (``Ctrl+O``).

**Console**

   To connect to a Jupyter kernel and run code interactively in a console session, you can run

   .. code-block:: console

      $ euporie-console

   (You can press ``Ctrl+C`` to open the command palette in ``euporie-console``).

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

*************
Compatibility
*************

Euporie requires Python 3.8 or later. It works on Linux, Windows and MacOS



.. |PyPI| image:: https://img.shields.io/pypi/v/euporie.svg
    :target: https://pypi.python.org/project/euporie/
    :alt: Latest Version

.. |RTD| image:: https://readthedocs.org/projects/euporie/badge/
    :target: https://euporie.readthedocs.io/en/latest/
    :alt: Documentation

.. |PyVer| image:: https://img.shields.io/pypi/pyversions/euporie
    :target: https://pypi.python.org/project/euporie/
    :alt: Supported Python versions

.. |Binder| image:: https://mybinder.org/badge_logo.svg
   :target: https://mybinder.org/v2/gh/joouha/euporie-binder/HEAD?urlpath=%2Feuporie%2F
   :alt: Launch with Binder

.. |License| image:: https://img.shields.io/github/license/joouha/euporie.svg
    :target: https://github.com/joouha/euporie/blob/main/LICENSE
    :alt: View license

.. |Stars| image:: https://img.shields.io/github/stars/joouha/euporie
    :target: https://github.com/joouha/euporie/stargazers
    :alt: ⭐
