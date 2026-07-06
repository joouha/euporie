#################################
Multiplexers and remote terminals
#################################

:term:`Terminal multiplexers <Terminal multiplexer>` (:program:`tmux`, :program:`screen`, :program:`zellij`) and SSH connections add a layer between euporie and your terminal emulator. That layer can interfere with terminal detection, :term:`terminal graphics`, clipboard access and unusual key bindings unless it's configured to pass the relevant escape sequences through unchanged.

This guide collects the configuration tweaks needed to get euporie working nicely in those environments.

****
tmux
****

Terminal graphics
=================

There are two ways to get :term:`terminal graphics` working inside :program:`tmux`. You can either use :program:`tmux`'s native Sixel support, or bypass :program:`tmux` entirely using its pass-through mechanism.

Option 1: tmux's native Sixel support
-------------------------------------

From version 3.4 onwards, :program:`tmux` can render Sixel graphics itself, provided it was compiled with the ``--enable-sixel`` option. If you are building :program:`tmux` from source, pass this flag when configuring the build:

.. code-block:: console

   $ ./configure --enable-sixel

Then advertise Sixel support to :program:`tmux` by adding the following to your :file:`~/.tmux.conf`:

.. code-block:: text

   set -ga terminal-features ',xterm*:sixel'

With this in place no special euporie configuration is required - euporie's Sixel output is rendered by :program:`tmux` like any other terminal graphics.

Option 2: pass-through
----------------------

Alternatively, :program:`tmux` can forward graphics escape sequences through to the underlying terminal unchanged. This works for the kitty and iterm2 graphics protocols as well as Sixel, and does not require a ``--enable-sixel`` build. Enable pass-through in your :file:`~/.tmux.conf`:

.. code-block:: text

   set -g allow-passthrough on

Then launch euporie with :option:`--multiplexer-passthrough` so it knows it's running inside :program:`tmux`:

.. code-block:: console

   $ euporie-notebook --multiplexer-passthrough --graphics=kitty --force-graphics

For :program:`tmux` running inside a kitty terminal, the Unicode-placeholder variant of the kitty protocol (:option:`--graphics=kitty-unicode`) generally works best because it survives :program:`tmux`'s buffer manipulations:

.. code-block:: console

   $ euporie-notebook --graphics=kitty-unicode --force-graphics --multiplexer-passthrough

Modifier-aware enter keys
=========================

The default :program:`tmux` configuration eats :kbd:`Ctrl+Enter` and
:kbd:`Shift+Enter`. To restore them, enable extended-key reporting:

.. code-block:: text

   set -s extended-keys on
   set -as terminal-features 'xterm*:extkeys'

You will then be able to use :kbd:`Ctrl+Enter` for :option:`run-selected-cells` and :kbd:`Shift+Enter` for :option:`run-cell-and-insert-below` as documented in :ref:`pages/keybindings:running cells`.

***********
GNU screen
***********

:program:`screen` has limited support for :term:`terminal graphics`. The most reliable approach is to fall back to ANSI/Unicode rendering inside :program:`screen` (:option:`--graphics=none`):

.. code-block:: console

   $ euporie-notebook --graphics=none

If your :program:`screen` build supports it, you can ask it to forward unknown escape sequences:

.. code-block:: text

   # ~/.screenrc
   termcapinfo xterm* 'XT'

When relying on this forwarding, launch euporie with :option:`--multiplexer-passthrough` so it emits graphics escape sequences in a form :program:`screen` will pass through unchanged.

******
zellij
******

:program:`zellij` supports Sixel graphics out of the box, so euporie's Sixel output is rendered without any special configuration:

.. code-block:: console

   $ euporie-notebook --graphics=sixel

:program:`zellij` does not currently forward the kitty or iterm2 graphics protocols. If your terminal does not support Sixel, use the ANSI fallback (:option:`--graphics=none`) inside :program:`zellij`, or open euporie in a plain terminal pane outside the :term:`multiplexer <Terminal multiplexer>`.

***
SSH
***

Most modern SSH servers and clients pass terminal escape sequences unchanged. The main caveats are:

* **Terminal size detection** sometimes fails on connect; if images are the wrong size, send :kbd:`Ctrl+L` to redraw or set :envvar:`COLUMNS` / :envvar:`LINES` manually before launching euporie.
* **Clipboard access** via OSC 52 only works if the SSH client and host both pass it through. Most modern terminals (kitty, WezTerm, iTerm2, Alacritty, foot) do; older builds may not.
* **Performance** of terminal graphics depends on bandwidth - a busy notebook can transfer a lot of data over the link.

If your SSH session has problems detecting :term:`terminal graphics` support, try:

.. code-block:: console

   $ euporie-notebook --graphics=kitty --force-graphics

***********
See also
***********

* :doc:`terminal_graphics` - details of the supported graphics protocols
* :doc:`troubleshooting` - solutions to specific common issues
* :doc:`../../packages/hub` - hosting euporie itself as an SSH service
