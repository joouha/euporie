.. image:: https://user-images.githubusercontent.com/12154190/159142921-77e710d8-823a-46d0-917a-8703048a43b7.svg

#######
euporie
#######

|PyPI| |RTD| |PyVer| |License| |Binder| |Stars|

.. content_start

**Euporie is a terminal app for running and editing Jupyter notebooks.**

The text-based interface is inspired by JupyterLab / Jupyter Notebook, and runs entirely in the terminal.

.. figure:: https://user-images.githubusercontent.com/12154190/160244007-cfde84ea-cddd-47f3-964a-96a10d60fb06.png
   :target: https://user-images.githubusercontent.com/12154190/160244007-cfde84ea-cddd-47f3-964a-96a10d60fb06.png

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

Open a notebook by passing the notebook's file path as a command line argument:

.. code-block:: console

   $ euporie notebook.ipynb

Alternatively, launch ``euporie`` and open a notebook file by selecting "Open" from the file menu (*Ctrl+o*).

To print a notebook to the terminal, run:

.. code-block:: console

   $ euporie --dump notebook.ipynb

To view a notebook in the system pager, run:

.. code-block:: console

   $ euporie --dump --page notebook.ipynb

For more information about the available command line flags, run:

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
* Displays rich cell outputs, including markdown, tables, images, LaTeX, HTML, SVG, & PDF
* Print formatted notebooks to the terminal or pager
* Open multiple notebooks side-by-side
* Hightly configurable
* Code completion
* Line completions from history
* Display contextual help
* Automatic code formatting

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
