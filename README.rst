|logo|

.. |logo| image:: https://user-images.githubusercontent.com/12154190/160670889-c6fc4cd8-413d-49f0-b105-9c0e03117032.svg
   :alt: <Logo>

#######
euporie
#######

|PyPI| |RTD| |PyVer| |License| |Binder| |Stars|

.. content_start

**Euporie is a terminal app for running and editing Jupyter notebooks.**

The text-based interface is inspired by JupyterLab / Jupyter Notebook, and runs entirely in the terminal.

.. figure:: https://user-images.githubusercontent.com/12154190/165388661-44153d99-a44b-4a4a-98b8-7007158c3fa3.png
   :target: https://user-images.githubusercontent.com/12154190/165388661-44153d99-a44b-4a4a-98b8-7007158c3fa3.png

   `View more screenshots here <https://euporie.readthedocs.io/en/latest/pages/gallery.html>`_

----

*******
Install
*******

You can install euporie with `pipx <https://pipxproject.github.io/>`_ (recommended) or ``pip``:

.. code-block:: console

   $ pipx install euporie
   $ # OR
   $ python -m pip install --user euporie

You can also try euporie online `here <https://mybinder.org/v2/gh/joouha/euporie-binder/HEAD?urlpath=%2Feuporie%2F>`_.

*****
Usage
*****

Open a notebook using the ``edit`` subcommand and passing the notebook's file path as a command line argument:

.. code-block:: console

   $ euporie edit notebook.ipynb

Alternatively, launch ``euporie`` and open a notebook file by selecting "Open" from the file menu (*Ctrl+o*).

To print a notebook to the terminal, use the ``preview`` subcommand:

.. code-block:: console

   $ euporie preview notebook.ipynb

To view a notebook in the system pager, use the ``--page`` flag:

.. code-block:: console

   $ euporie preview --page notebook.ipynb

For more information about the available subcommands and command line flags, run:

.. code-block:: console

   $ euporie --help


*************
Documentation
*************

View the online documentation at: `https://euporie.readthedocs.io/ <https://euporie.readthedocs.io/>`_

The code is available on GitHub at: `https://github.com/joouha/euporie <https://github.com/joouha/euporie>`_

********
Features
********

* Edit and run notebooks in the terminal
* Jupyter widgets support
* Displays rich cell outputs, including markdown, tables, images, LaTeX, HTML, SVG, & PDF
* Print formatted notebooks to the terminal or pager
* Open multiple notebooks and display them stacked or tiled
* Code completion
* Line completions from history
* Contextual help
* Automatic code formatting
* Highly configurable


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
