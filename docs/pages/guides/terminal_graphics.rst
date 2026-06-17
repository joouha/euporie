##################
Terminal graphics
##################

One of euporie's most distinctive features is its ability to display images - plots, photos, equations, even PDFs - directly inside the terminal using :term:`terminal graphics`. This guide explains how that works, which protocols are supported, and what to do when graphics don't appear.

************************
Why are graphics tricky?
************************

Most terminals only know how to display text. To show pixel-accurate images they need an out-of-band protocol that the terminal recognises and honours. Three such protocols are widely supported, plus a couple of fallback strategies for terminals that don't support any of them.

*******************
Supported protocols
*******************

Kitty graphics protocol
=======================

The most capable protocol. Originally designed for `kitty <https://sw.kovidgoyal.net/kitty/graphics-protocol.html>`_ but also supported by `WezTerm <https://wezfurlong.org/wezterm/>`_, `Konsole <https://konsole.kde.org/>`_, `ghostty <https://ghostty.org/>`_ and others.

* Lossless transmission of arbitrary RGB(A) images.
* Cells can be reused/scrolled without repainting.
* Force with :option:`--graphics=kitty`.

A variant, :option:`--graphics=kitty-unicode`, transmits images alongside Unicode placeholder characters and is useful inside multiplexers and over SSH.

iTerm2 inline images
====================

Used by `iTerm2 <https://iterm2.com>`_ and a handful of compatible terminals. Force with :option:`--graphics=iterm`.

Sixel
=====

A much older protocol, supported (in 2024+) by xterm, mlterm, foot, WezTerm, recent versions of tmux (3.4+), Windows Terminal and more.

Force with :option:`--graphics=sixel`. Requires either the :py:mod:`timg` Python package (installed by default), :py:mod:`chafa.py`, or an external program like :program:`img2sixel` or :program:`imagemagick`. See the :ref:`sixel section <installation:sixel>` of the installation page for the exhaustive list of supported tools.

Unicode and ANSI fallbacks
==========================

For terminals that don't support any graphics protocol, euporie can still approximate images using Unicode block characters and ANSI colour codes. This is significantly lower-fidelity but still useful for plots and icons.

Force with :option:`--graphics=none`. Quality is improved if any of `chafa <https://hpjansson.org/chafa/>`_, `timg <https://github.com/hzeller/timg>`_, `viu <https://github.com/atanunq/viu>`_ or other ANSI-art tools are installed. See the :ref:`ANSI art section <installation:ansi art>` of the installation page for the exhaustive list of supported tools.

*****************
Detection
*****************

By default, euporie detects which protocol your terminal supports by sending escape-sequence queries on startup and seeing which ones the terminal acknowledges. The chosen protocol is logged at debug level (see :doc:`../troubleshooting` for how to enable a debug log).

You can override the auto-detection with the :option:`--graphics` flag, or with the :confval:`graphics` configuration option.

If a protocol is selected manually but the terminal isn't known to support it, euporie will refuse to use it - producing visible boxes/placeholders where graphics should be. To override this safety check pass :option:`--force-graphics`.

********************
Multiplexers and SSH
********************

Both :program:`tmux` and :program:`screen` (see :term:`terminal multiplexer`) can break terminal-graphics support unless they are explicitly told to forward unknown escape sequences. See the dedicated :doc:`multiplexers` guide for the configuration needed.

Over SSH, terminal size detection sometimes fails - in that case images may be sized incorrectly. Most modern terminals send a size update on connect; older ones may need :option:`--force-graphics` and a manual :envvar:`COLUMNS`/:envvar:`LINE` hint.

*****************
Other formats
*****************

Once euporie can render raster images, it composes them on top of:

* **SVG** - rasterised first via :py:mod:`cairosvg` or ImageMagick.
* **PDF** - the first page is rasterised via ImageMagick (other tools can
  produce ASCII-art previews for fallback).
* **LaTeX** - rendered to an image using :py:mod:`flatlatex`,
  :py:mod:`sympy` or :program:`dvipng`.
* **HTML** - rendered by euporie's built-in HTML engine, with text-mode
  fallback to :program:`w3m`/:program:`elinks`/:program:`lynx`.

See :doc:`../installation` for the optional dependencies needed by each format.

*****************
Troubleshooting
*****************

If graphics aren't appearing, work through this list:

1. Check that your terminal claims to support a graphics protocol (``echo "$TERM"`` and look up the terminal's docs).
2. Try forcing a specific protocol: ``euporie-notebook --graphics=kitty --force-graphics``.
3. If you're inside ``tmux`` or ``screen``, see :doc:`multiplexers`.
4. If you're over SSH, the multiplexer guide also applies.
5. Generate a debug log (``euporie-notebook --log-file=debug.log --log-level=debug``) and grep for ``graphics`` to see which protocol was selected.

The :doc:`../troubleshooting` page lists fixes for several common, specific symptoms.
