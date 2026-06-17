############
Installation
############

Euporie is published on `PyPI <https://pypi.org/project/euporie/>`_ and can be installed like any other Python package. It requires Python 3.10 or later, and runs on Linux, MacOS and Windows.

*************
Quick install
*************

Install the metapackage to get the ``euporie`` launcher and the three end-user :term:`apps <App>` (``euporie-notebook``, ``euporie-console`` and ``euporie-preview``):

.. tab-set::

   .. tab-item:: uv
      :sync: uv

      .. code-block:: console

         $ uv tool install euporie

   .. tab-item:: pipx
      :sync: pipx

      .. code-block:: console

         $ pipx install euporie

   .. tab-item:: pip
      :sync: pip

      .. code-block:: console

         $ pip install --user euporie

If you want to try the latest, potentially unstable, unreleased changes, you can install euporie from git:

.. tab-set::

   .. tab-item:: uv
      :sync: uv

      .. code-block:: console

         $ uv tool install git+https://github.com/joouha/euporie.git@dev

   .. tab-item:: pipx
      :sync: pipx

      .. code-block:: console

         $ pipx install git+https://github.com/joouha/euporie.git@dev

   .. tab-item:: pip
      :sync: pip

      .. code-block:: console

         $ pip install git+https://github.com/joouha/euporie.git@dev


.. note::
   Although euporie does not have any compiled components, some of its dependencies may require compilation as part of their build process, depending on the availability of binary wheels. If this is the case, you may need to install the relevant build dependencies for your distribution, such as ``python-dev`` and ``gcc`` or equivalent.


**********************
Try without installing
**********************

In your terminal
================

If you have :program:`uv` installed, you can run any euporie :term:`app <App>` instantly without installing it, using ``uvx``:

.. code-block:: console

   $ uvx euporie notebook            # launch the notebook editor
   $ uvx euporie notebook my.ipynb   # ...optionally with a notebook to open
   $ uvx euporie console             # interactive Jupyter console
   $ uvx euporie preview my.ipynb    # render a notebook to the terminal

The same works with :program:`pipx`:

.. code-block:: console

   $ pipx run --spec 'euporie' euporie notebook

In your browser
===============

A WebAssembly build of euporie runs entirely in the browser - no installation
required.

`Launch the live demo <../_static/lite.html>`_.


****************
Individual apps
****************

You can install just the :term:`app(s) <App>` you need instead of the whole metapackage. Each app pulls in ``euporie-core`` and any other libraries it needs:

.. code-block:: console

   $ uv tool install euporie-notebook   # notebook editor only
   $ uv tool install euporie-console    # console only
   $ uv tool install euporie-preview    # preview only
   $ uv tool install euporie-hub        # multi-user SSH server

The hub is **not** included in the metapackage and must be installed explicitly.

See the :doc:`Applications <../packages/notebook>` section for detailed documentation on each app.


****************
Container image
****************

A `Containerfile <https://github.com/joouha/euporie/blob/main/Containerfile>`_ is provided in the repository. Build and run it with `podman <https://podman.io>`_ or `docker <https://docker.com>`_:

.. code-block:: console

   $ podman build -t euporie -f Containerfile .
   $ podman run --rm -it euporie


----

***************
Jupyter Kernels
***************

Euporie uses Jupyter :term:`kernels <Kernel>` to execute code in notebooks. If you see a "no kernels found" error when trying to run a notebook, you'll need to ensure you have the appropriate :term:`kernel <Kernel>` installed and registered.

For Python notebooks, install and register the IPython kernel:

.. tab-set::

   .. tab-item:: uv
      :sync: uv

      To install ``ipykernel`` in a virtual environment:

      .. code-block:: console

         $ uv pip install ipykernel
         $ uv run python -m ipykernel install --user


   .. tab-item:: pip
      :sync: pip

      To install ``ipykernel`` for the current user:

      .. code-block:: console

         $ pip install --user ipykernel
         $ python -m ipykernel install --user

For other programming languages, you'll need to install the appropriate :term:`kernel <Kernel>` package.

You can view a list of available :term:`kernel <Kernel>` implementations for various programming languages `here <https://github.com/jupyter/jupyter/wiki/Jupyter-kernels>`_.

See the :doc:`guides/kernels` guide for more details on managing and connecting to :term:`kernels <Kernel>`.

----

*********************
Optional Dependencies
*********************

Euporie supports a wide range of rendering methods in order to get your notebooks looking as nice as possible in the terminal. The following section lists the various rendering methods available, and details what needs to be installed for them to be used.

For a deeper discussion of how images are rendered in the terminal, see the :doc:`guides/terminal_graphics` guide.

Images
======

Euporie will attempt to render images in the best possible way it can.

.. note::
   :py:mod:`timg` is installed as a dependency of euporie and is used to render images as sixels or ansi art. However, euporie will preferentially use an external application if it is installed and is more performant or gives higher quality output.

The following methods will be used if they are available:

Kitty's Terminal Graphics Protocol
----------------------------------

If your terminal supports `kitty's terminal graphics protocol <https://sw.kovidgoyal.net/kitty/graphics-protocol.html>`_, euporie will use it to render images.

This is supported by `kitty <https://sw.kovidgoyal.net/kitty>`_, `WezTerm <https://wezfurlong.org/wezterm/>`_, and `Konsole <https://konsole.kde.org/>`_.

You can manually select this protocol by launching euporie with the :option:`--graphics=kitty` flag.

iTerm2's Terminal Graphics Protocol
-----------------------------------

If you're using `iTerm2 <https://iterm2.com/>`_, euporie can use its proprietary graphics protocol to render images.

You can select this protocol by launching euporie with the :option:`--graphics=iterm` flag.

Sixels
------

If supported by your terminal, euporie can show graphical images in :term:`cell` outputs using the Sixel graphics protocol.

You can select this protocol by launching euporie with the :option:`--graphics=sixel` flag.

This requires one of the following dependencies:

* Python packages
   .. hlist::
      :columns: 3

      * :py:mod:`timg`
      * :py:mod:`teimpy` (requires :py:mod:`numpy`)
      * :py:mod:`chafa`

* External applications
   .. hlist::
      :columns: 3

      * `chafa <https://hpjansson.org/chafa/>`_
      * `img2sixel <https://saitoha.github.io/libsixel/#img2sixel>`_
      * `imagemagick <https://www.imagemagick.org>`_

Ansi Art
--------

If all else fails, euporie will fall back to using ansi art to display images.

You can select this protocol by launching euporie with the :option:`--graphics=none` flag.

* Python packages
   .. hlist::
      :columns: 3

      * :py:mod:`timg`
      * :py:mod:`chafa`
      * :py:mod:`img2unicode`

* External applications
   .. hlist::
      :columns: 3

      * `chafa <https://hpjansson.org/chafa/>`_
      * `timg <https://github.com/hzeller/timg>`_
      * `catimg <https://github.com/posva/catimg>`_
      * `icat <https://github.com/atextor/icat>`_
      * `tiv <https://github.com/radare/tiv>`_
      * `viu <https://github.com/atanunq/viu>`_
      * `jp2a <https://csl.name/jp2a/>`_
      * `img2txt <http://caca.zoy.org/wiki/libcaca>`_


.. warning::
   If a graphics protocol is manually selected but the terminal is not known to support it, it will not be used. To force the use of a manually selected graphic protocol, launch euporie with the :option:`--force-graphics` flag. This may lead to unexpected behaviours and broken terminal output!

SVG
===

Euporie can display SVG output by first rasterizing it, for which one of the following is required:

* Python packages
   .. hlist::
      :columns: 3

      * :py:mod:`cairosvg`
      * :py:mod:`ziamath` (for LaTeX to SVG)

* External applications
   .. hlist::
      :columns: 3

      * `imagemagick <https://www.imagemagick.org>`_

PDF
===

Euporie can display the first page of PDF files using one of the following:

* External applications
   .. hlist::
      :columns: 3

      * `imagemagick <https://www.imagemagick.org>`_
      * `chafa <https://hpjansson.org/chafa/>`_
      * `timg <https://github.com/hzeller/timg>`_
      * `tiv <https://github.com/radare/tiv>`_

.. note::
   Currently only the first page of PDF files can be displayed.

HTML
====

Euporie includes its own custom HTML renderer, which it uses to render HTML outputs, meaning that external programs are no longer required to display HTML.

If HTML rendering fails for some reason, euporie will fall back on one of the following for rendering HTML:

* Python packages
   .. hlist::
      :columns: 3

      * :py:mod:`mtable` (requires :py:mod:`html5lib`)
      * :py:mod:`html2text`

* External applications
   .. hlist::
      :columns: 3

      * `cha <https://sr.ht/~bptato/chawan/>`_ (chawan)
      * `w3m <http://w3m.sourceforge.net/>`_
      * `elinks <http://elinks.or.cz/>`_
      * `lynx <https://lynx.browser.org/>`_
      * `links <http://links.twibright.com/>`_

.. note::
   :py:mod:`mtable` will only render HTML tables in :term:`cell` outputs, so is useful if you are working with dataframes.


LaTeX
=====

Euporie will render LaTeX in markdown and :term:`cell` outputs using :term:`terminal graphics` or unicode text, using any of the following if they are installed:

* Python packages
   .. hlist::
      :columns: 3

      * :py:mod:`flatlatex`
      * :py:mod:`sympy` (requires :py:mod:`antlr4`)
      * :py:mod:`pylatexenc`
      * :py:mod:`unicodeitplus`
      * :py:mod:`unicodeit`
      * :py:mod:`matplotlib`
      * :py:mod:`ziamath`

* External applications
   .. hlist::
      :columns: 3

      * `dvipng <https://www.nongnu.org/dvipng/>`_ (with `latex <https://www.latex-project.org/>`_)
      * `pandoc <https://pandoc.org/>`_ (with `typst <https://typst.app/>`_)
      * `utftex <https://github.com/bartp5/libtexprintf>`_

.. note::
   :py:mod:`flatlatex` is a dependency of euporie, so will be installed by
   default.


Mermaid
=======

Euporie can render Mermaid diagrams to images or ASCII art using one of the following:

* External applications
   .. hlist::
      :columns: 3

      * `mmdr <https://github.com/mermaid-js/mermaid-rs>`_ (mermaid-rs)
      * `mmdc <https://github.com/mermaid-js/mermaid-cli>`_ (mermaid-cli)
      * `mermaid-ascii <https://www.npmjs.com/package/mermaid-ascii>`_
