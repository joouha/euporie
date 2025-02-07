############
Installation
############

Euporie is on `pypi <https://pypi.org/project/euporie/>`_, so can be installed like any other Python package.

To install euporie globally, use the following:

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

         $ pip install euporie

If you want to try the latest and potentially unstable unreleased changes, you can install euporie from git:

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
   Although euporie does not have any compiled components, some of its dependencies may require compilation as part of their build process, depending on the availability of binary wheels. If this is the case, you may need to install the relevant build dependencies for your distribution, such as `python-dev` and `gcc` or equivalent.


**********************
Try without installing
**********************

You can use :program:`uv` or :program:`pipx` to try euporie without installing it:

.. tab-set::

   .. tab-item:: uv
      :sync: uv

      .. code-block:: console

         $ uvx euporie notebook

   .. tab-item:: pipx
      :sync: pipx

      .. code-block:: console

         $ pipx run --spec 'euporie[all]' euporie notebook

You can also try euporie online here:

https://mybinder.org/v2/gh/joouha/euporie-binder/HEAD?urlpath=%2Feuporie%2F


----

**************
Jupyter Kernels
**************

Euporie uses Jupyter kernels to execute code in notebooks. If you see a "no kernels found" error when trying to run a notebook, you'll need to ensure you have the appropriate kernel installed and registered.

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

For other programming languages, you'll need to install the appropriate kernel package.

You can view a list of available kernel implementations for various programming languages `here <https://github.com/jupyter/jupyter/wiki/Jupyter-kernels>`_.

----

*********************
Optional Dependencies
*********************

Euporie supports a wide range of rendering methods in order to get your notebooks looking as nice as possible in the terminal. The following section lists the various rendering methods available, and details what needs to be installed for them to be used.

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

Sixels
------

If supported by your terminal, euporie can show graphical images in cell outputs using the Sixel graphics protocol. This requires one of the following dependencies:

* Python packages
   .. hlist::
      :columns: 3

      * :py:mod:`timg`
      * :py:mod:`teimpy`

* External applications
   .. hlist::
      :columns: 3

      * `img2sixel <https://saitoha.github.io/libsixel/#img2sixel>`_
      * `imagemagick <https://www.imagemagick.org>`_

Ansi Art
--------

If all else fails, euporie will fall back to using ansi art to display images.

* Python packages
   .. hlist::
      :columns: 3

      * :py:mod:`chafa.py`
      * :py:mod:`timg`

* External applications
   .. hlist::
      :columns: 3

      * `chafa <https://hpjansson.org/chafa/>`_
      * `timg <https://github.com/hzeller/timg>`_
      * `catimg <https://github.com/posva/catimg>`_
      * `icat <https://github.com/atextor/icat>`_
      * `tiv <https://github.com/radare/tiv>`_
      * `viu <https://github.com/atanunq/viu>`_
      * `img2unicode <https://github.com/matrach/img2unicode>`_
      * `jp2a <https://csl.name/jp2a/>`_
      * `img2txt <http://caca.zoy.org/wiki/libcaca>`_

SVG
===

Euporie can display SVG output by first rasterizing it, for which one of the following is required:

* Python packages
   .. hlist::
      :columns: 3

      * :py:mod:`cairosvg`

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

Euporie includes its own custom HTML renderer, which it uses to render HTML outputs, meaning that external programs are not longer required to display HTML.

If HTML rendering fails for some reason, euporie will fall back on one of the following for rendering HTML:

* Python packages
   .. hlist::
      :columns: 3

      * :py:mod:`mtable`

* External applications
   .. hlist::
      :columns: 3

      * `w3m <http://w3m.sourceforge.net/>`_
      * `elinks <http://elinks.or.cz/>`_
      * `lynx <https://lynx.browser.org/>`_
      * `links <http://links.twibright.com/>`_

.. note::
   :py:mod:`mtable` will only render HTML tables in cell outputs, so is useful if you are working with dataframes


LaTeX
=====

Euporie will render LaTeX in markdown and cell outputs using terminal graphics or unicode text, using any of the following if they are installed:

* Python packages
   .. hlist::
      :columns: 3

      * :py:mod:`flatlatex`
      * :py:mod:`sympy`
      * :py:mod:`pylatexenc`
      * :py:mod:`ipython`

* External applications
   .. hlist::
      :columns: 3

      * :command:`dvipng`
      * `utftex <https://github.com/bartp5/libtexprintf>`_

.. note::
   :py:mod:`flatlatex` is a dependency of euporie, so will be installed by default
