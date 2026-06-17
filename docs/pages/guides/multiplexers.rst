#################################
Multiplexers and remote terminals
#################################

Terminal multiplexers (:program:`tmux`, :program:`screen`, :program:`zellij`)
and SSH connections add a layer between euporie and your terminal emulator.
That layer can interfere with terminal detection, terminal graphics,
clipboard access and unusual key bindings unless it's configured to pass
the relevant escape sequences through unchanged.

This guide collects the configuration tweaks needed to get euporie working
nicely in those environments.

***********
tmux
***********

Pass-through for graphics
=========================

tmux only supports inline graphics from version 3.4 onwards, and only when
explicitly enabled. Add the following to your ``~/.tmux.conf``:

.. code-block:: text

   set -g allow-passthrough on
   # For Sixel graphics (tmux 3.4+ compiled with --enable-sixel):
   set -ga terminal-features ',xterm*:sixel'

Then launch euporie with ``--multiplexer-passthrough`` so it knows it's
running inside tmux:

.. code-block:: console

   $ euporie-notebook --multiplexer-passthrough --graphics=kitty --force-graphics

For tmux running inside a kitty terminal, the Unicode-placeholder variant
of the kitty protocol generally works best because it survives tmux's
buffer manipulations:

.. code-block:: console

   $ euporie-notebook --graphics=kitty-unicode --force-graphics --multiplexer-passthrough

Modifier-aware enter keys
=========================

The default tmux configuration eats :kbd:`Ctrl+Enter` and
:kbd:`Shift+Enter`. To restore them, enable extended-key reporting:

.. code-block:: text

   set -s extended-keys on
   set -as terminal-features 'xterm*:extkeys'

You will then be able to use :kbd:`Ctrl+Enter` for *Run cell* as documented
in :ref:`pages/keybindings:running cells`.

***********
GNU screen
***********

Screen has limited support for terminal graphics. The most reliable approach
is to fall back to ANSI/Unicode rendering inside screen:

.. code-block:: console

   $ euporie-notebook --graphics=none

If your screen build supports it, you can ask it to forward unknown escape
sequences:

.. code-block:: text

   # ~/.screenrc
   termcapinfo xterm* 'XT'

***********
zellij
***********

zellij does not currently forward terminal-graphics protocols. Use the
ANSI fallback (``--graphics=none``) inside zellij, or open euporie in a
plain terminal pane outside the multiplexer.

***********
SSH
***********

Most modern SSH servers and clients pass terminal escape sequences
unchanged. The main caveats are:

* **Terminal size detection** sometimes fails on connect; if images are
  the wrong size, send :kbd:`Ctrl+L` to redraw or set ``COLUMNS`` /
  ``LINES`` manually before launching euporie.
* **Clipboard access** via OSC 52 only works if the SSH client and host
  both pass it through. Most modern terminals (kitty, WezTerm, iTerm2,
  Alacritty, foot) do; older builds may not.
* **Performance** of terminal graphics depends on bandwidth - a busy
  notebook can transfer a lot of data over the link.

If your SSH session has problems detecting terminal-graphics support, try:

.. code-block:: console

   $ euporie-notebook --graphics=kitty --force-graphics

***********
See also
***********

* :doc:`terminal_graphics` - details of the supported graphics protocols
* :doc:`../troubleshooting` - solutions to specific common issues
* :doc:`../../packages/hub` - hosting euporie itself as an SSH service
