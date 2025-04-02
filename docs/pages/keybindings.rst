############
Key Bindings
############

*************
Editing Modes
*************

The key-bindings used when editing a cell or in the console are determined by the :option:`edit_mode` configuration variable. This can be set to ``micro``, ``emacs`` or ``vi`` to use key-bindings in the style of the respective text editor.

*******************
Custom Key Bindings
*******************

Key bindings can be customized by setting the :option:`key_bindings` configuration parameter.

This parameter takes the form of a mapping, where they keys are references to modes or components to which a set of key-bindings apply, and the values are mapping of command names to lists of keys.

Key bindings set in the configuration will entirely over-ride the default binding, so if you want to add an additional binding for a command while retaining the default, you will need to include the default binding in the configuration.

Below is an example :ref:`pages/configuration:configuration file` showing how the key-bindings can be set:

.. code-block:: javascript
   :emphasize-lines: 5-10

   {
     "notebook": {
       "autoformat": false,
       "expand": true,
       "key_bindings": {
         "euporie.notebook.app.NotebookApp": {
           "quit": ["c-q", "c-p"],
           "new-notebook": []
         }
       },
     }
   }

This example sets two key-bindings in the :doc:`Notebook <../apps/notebook>` app for the :command:`quit` command: :kbd:`Ctrl+Q` and :kbd:`Ctrl+P`. It also unsets any key-bindings for the :command:`new-notebook` command.

Custom key-binding configuration can also be passed on the command line in the form of a JSON string:

.. code-block:: console

   $ euporie-notebook --key-bindings='{"euporie.notebook.app.NotebookApp": {"new-notebook": [],"quit": ["c-q", "c-p"]}}'

Valid component names include:

* ``euporie.core.app.BaseApp``
* ``euporie.core.widgets.pager.Pager``
* ``euporie.core.widgets.inputs.KernelInput``
* ``euporie.core.key_binding.bindings.micro.EditMod``
* ``euporie.notebook.app.NotebookApp``
* ``euporie.notebook.tabs.notebook.Notebook``
* ``euporie.console.app.ConsoleApp``
* ``euporie.console.tabs.console.Console``
* ``euporie.preview.app.PreviewApp``

Most command names are listed in `Default Key Bindings Reference`_.


*************
Running Cells
*************

Cells can be run using :kbd:`Ctrl+Enter`, or :kbd:`Shift+Enter` to run and select the next cell, as is the case in `JupyterLab <https://jupyter.org/>`_.

However, most terminals do not distinguish between :kbd:`Enter`, :kbd:`Ctrl+Enter` & :kbd:`Shift+Enter` by default, meaning that you have to use alternative key-bindings in euporie to run cells.

Fortunately it is possible to configure many terminals such that these key-bindings can be used, as outlined below.

.. note::
   There are two commonly used formats of escape sequences which can be used to distinguish these key-bindings: **FK-27** and **CSI-u**. The instructions below implement the CSI-u style, but euporie will recognise either.

WezTerm
=======

Update your :file:`$HOME/.config/wezterm/wezterm.lua` file to include the following:

.. code-block:: lua

    local wezterm = require 'wezterm';

    return {
      -- ...

      keys = {
        {key="Enter", mods="CTRL", action=wezterm.action{SendString="\x1b[13;5u"}},
        {key="Enter", mods="SHIFT", action=wezterm.action{SendString="\x1b[13;2u"}},
      },
    }

Kitty
=====

Add the following to your :file:`$HOME/.config/kitty/kitty.conf` file:

.. code-block::

   map ctrl+enter send_text normal,application \x1b[13;5u
   map shift+enter send_text normal,application \x1b[13;2u


Foot
====

Foot supports XTerm's `K27 format <https://invisible-island.net/xterm/modified-keys.html>`_, so does not require any additional configuration.

XTerm
=====

You can add the following lines to your :file:`$HOME/.Xresources` file, which enables **CSI-u** escape sequences.

.. code-block::

   *vt100.modifyOtherKeys: 1
   *vt100.formatOtherKeys: 1


Windows Terminal
================

You can add the key-bindings to your :file:`settings.json` file:

.. code-block:: javascript

   {
     // ...

     "keybindings":
     [
       { "command": { "action": "sendInput", "input": "\u001b[13;5u" }, "keys": "ctrl+enter" },
       { "command": { "action": "sendInput", "input": "\u001b[13;2u" }, "keys": "shift+enter" }
     ]
   }


Alacritty
=========

You can define the key-binding in your :file:`$HOME/.config/alacritty/alacritty.yml` file as follows:

.. code-block:: yaml

    key_bindings:
      - { key: Return, mods: Control, chars: "\x1b[13;5u" }
      - { key: Return, mods: Shift,   chars: "\x1b[13;2u" }

Konsole
=======

In the menu, navigate to :menuselection:`Settings --> Edit Current Profile`, then select :menuselection:`Keyboard --> Edit`.

Change the existing entry for `Return+Shift` to `Return+Shift+Ctrl` (or whatever you prefer), then add the following entries:

+-----------------+-----------+
| Key combination | Output    |
+=================+===========+
| Return+Ctrl     | E\[13;5u  |
+-----------------+-----------+
| Return+Shift    | \E\[13;2u |
+-----------------+-----------+

******************************
Default Key Bindings Reference
******************************

The following lists outline the default key-bindings used in euporie:

.. include:: ../_inc/default_key_bindings.rst
