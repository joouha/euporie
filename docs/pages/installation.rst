############
Installation
############

Euporie is on `pypi <https://pypi.org/project/euporie/>`_, so can be installed using `pip <https://pip.pypa.io/en/stable/>`_ or `pipx <https://pipxproject.github.io/pipx/>`_. On Linux, you may need to first install `gcc-11`.

To install euporie globally, run:

.. code-block:: console

   $ pipx install euporie


To install inside a virtualenv, run:

.. code-block:: console

   $ pip install euporie

If you want to try the latest and potentially unstable unreleased changes, you can install euporie from git:

.. code-block:: console

   $ pipx install git+https://github.com/joouha/euporie.git@dev


**********************
Try without installing
**********************

You can use :program:`pipx` to try euporie before installing it:

.. code-block:: console

   $ pipx run --spec 'euporie[all]' euporie notebook

You can also try euporie online here:

https://mybinder.org/v2/gh/joouha/euporie-binder/HEAD?urlpath=%2Feuporie%2F


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

Currently only the `kitty <https://sw.kovidgoyal.net/kitty>`_ and `WezTerm <https://wezfurlong.org/wezterm/>`_ terminals support this.

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

HTML
====

Euporie will attempt to render HTML outputs. This requires one of the following:

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

Euporie will render LaTeX in markdown and cell output using unicode text, using any of the following if they are installed:

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

.. note::
   :py:mod:`flatlatex` is a dependency of euporie, so will be installed by default

.. note::
   :py:mod:`ipython` and :command:`dvipng` are both equired to display rendered LaTeX as graphics
