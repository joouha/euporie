############
Key Bindings
############

*************
Editing Modes
*************

The key-bindings used when editing a cell are determined by the :option:`edit_mode` configuration variable. This can be set to ``micro``, ``emacs`` or ``vim`` to use key-bindings in the style of the respective text editor.

.. note:: The ``vim`` and ``emacs`` key-bindings are defined by the :py:module:`prompt_toolkit` package and are largely untested, so your results may vary!

*************
Running Cells
*************

Cells can be run using :kbd:`Ctrl+Enter`, or :kbd:`Shift+Enter` to run and selct the next cell, as is the case in `JupyterLab <https://jupyter.org/>`_.

However, most terminals do not distinguish between :kbd:`Enter`, :kbd:`Ctrl+Enter` & :kbd:`Shift+Enter` by default, meaning that you have to use alternative key-bindings in euporie to run cells.

Fortunately it is possible to configure many terminals such that these key-bindings can be used, as outlined below.

.. note::
   There are two commonly used formats of escape sequecnes which can be used to distinguish these key-bindings: **FK-27** and **CSI-u**. The instuctions below implement the CSI-u style, but euporie will recognise either.

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

Add the following to your :file:`$HOME/.config/kitty/kitty.conf file:

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

You can define the key-binding in your :file:`$HOME/`.config/alacritty/alacritty.yml` file as follows:

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
Default Key bindings Reference
******************************

The following lists outline the default key-bindings used in euporie:

.. _keybinding-definitions-start:
Application
===========

+-------------------------+--------------------------------------------------------------------------+
| Keys                    | Command                                                                  |
+=========================+==========================================================================+
| :kbd:`Ctrl+n`           | Create a new file.                                                       |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+o`           | Open a file.                                                             |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+w`           | Close the current file.                                                  |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+q`           | Quit euporie.                                                            |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+Pagedown`    | Switch to the next tab.                                                  |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+Pageup`      | Switch to the previous tab.                                              |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Tab`              | Focus the next control.                                                  |
|                         |                                                                          |
| :kbd:`Ctrl+i`           |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Shift+Tab`        | Focus the previous control.                                              |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`l`                | Toggle the visibility of line numbers.                                   |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`w`                | Toggle whether cells should extend across the full width of the screen.  |
+-------------------------+--------------------------------------------------------------------------+

Notebook
========

+-------------------------+--------------------------------------------------------------------------+
| Keys                    | Command                                                                  |
+=========================+==========================================================================+
| :kbd:`Ctrl+s`           | Save the current notebook.                                               |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`a`                | Add a new cell above the current.                                        |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`b`                | Add a new cell below the current.                                        |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`D, D`             | Delete the current cell.                                                 |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`x`                | Cut the current cell.                                                    |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`c`                | Copy the current cell.                                                   |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`v`                | Paste the last copied cell.                                              |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`I, I`             | Interrupt the notebook's kernel.                                         |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`0, 0`             | Restart the notebook's kernel.                                           |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`[`                | Scroll the page up a line.                                               |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`]`                | Scroll the page down a line.                                             |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`{`                | Scroll the page up 5 lines.                                              |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`}`                | Scroll the page down 5 lines.                                            |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Home`             | Select the first cell in the notebook.                                   |
|                         |                                                                          |
| :kbd:`Ctrl+Up`          |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Pageup`           | Go up 5 cells.                                                           |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Up`               | Go up one cell.                                                          |
|                         |                                                                          |
| :kbd:`k`                |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Down`             | Select the next cell.                                                    |
|                         |                                                                          |
| :kbd:`j`                |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Pagedown`         | Go down 5 cells.                                                         |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`End`              | Select the last cell in the notebook.                                    |
|                         |                                                                          |
| :kbd:`Ctrl+Down`        |                                                                          |
+-------------------------+--------------------------------------------------------------------------+

Cell
====

+-------------------------+--------------------------------------------------------------------------+
| Keys                    | Command                                                                  |
+=========================+==========================================================================+
| :kbd:`e`                | Edit cell in $EDITOR.                                                    |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+Enter`       | Run or render the current cell.                                          |
|                         |                                                                          |
| :kbd:`Ctrl+e`           |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Shift+Enter`      | Run or render the current cell and select the next cell.                 |
|                         |                                                                          |
| :kbd:`Ctrl+r`           |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Alt+Ctrl+m`       | Run or render the current cell and insert a new cell below.              |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Enter`            | Enter cell edit mode.                                                    |
|                         |                                                                          |
| :kbd:`Ctrl+m`           |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Escape`           | Exit cell edit mode.                                                     |
|                         |                                                                          |
| :kbd:`Alt+Escape`       |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`m`                | Change cell type to markdown.                                            |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`y`                | Change cell type to code.                                                |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`r`                | Change cell type to raw.                                                 |
+-------------------------+--------------------------------------------------------------------------+

Completions
===========

+-------------------------+--------------------------------------------------------------------------+
| Keys                    | Command                                                                  |
+=========================+==========================================================================+
| :kbd:`Right`            | Accept suggestion.                                                       |
|                         |                                                                          |
| :kbd:`Ctrl+f`           |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Alt+f`            | Fill partial suggestion.                                                 |
+-------------------------+--------------------------------------------------------------------------+

Suggestions
===========

+-------------------------+--------------------------------------------------------------------------+
| Keys                    | Command                                                                  |
+=========================+==========================================================================+
| :kbd:`Tab`              | Show the completion menu and select the next completion.                 |
|                         |                                                                          |
| :kbd:`Ctrl+i`           |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Shift+Tab`        | Show the completion menu and select the previous completion.             |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Escape`           | Cancel a completion with the escape key.                                 |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Enter`            | Cancel a completion with the escape key.                                 |
|                         |                                                                          |
| :kbd:`Ctrl+m`           |                                                                          |
+-------------------------+--------------------------------------------------------------------------+

Micro Editing Mode
==================

+-------------------------+--------------------------------------------------------------------------+
| Keys                    | Command                                                                  |
+=========================+==========================================================================+
| :kbd:`<Any>`            | Enter a key.                                                             |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Insert`           | Toggle overwrite when using micro editing mode.                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+u`           | Start recording a macro.                                                 |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+u`           | Stop recording a macro.                                                  |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+j`           | Re-execute the last keyboard macro defined.                              |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Backspace`        | Backspace.                                                               |
|                         |                                                                          |
| :kbd:`Ctrl+h`           |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+Left`        | Backward word.                                                           |
|                         |                                                                          |
| :kbd:`Alt+b`            |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+Right`       | Forward word.                                                            |
|                         |                                                                          |
| :kbd:`Alt+f`            |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+Up`          | Beginning of buffer.                                                     |
|                         |                                                                          |
| :kbd:`Ctrl+Home`        |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+Down`        | End of buffer.                                                           |
|                         |                                                                          |
| :kbd:`Ctrl+End`         |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Pagedown`         | Scroll page down.                                                        |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Pageup`           | Scroll page up.                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Left`             | Move back a character, or up a line.                                     |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Right`            | Move forward a character, or down a line.                                |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Home`             | Move the cursor to the start of the line.                                |
|                         |                                                                          |
| :kbd:`Alt+Left`         |                                                                          |
|                         |                                                                          |
| :kbd:`Alt+a`            |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`End`              | Move the cursor to the end of the line.                                  |
|                         |                                                                          |
| :kbd:`Alt+Right`        |                                                                          |
|                         |                                                                          |
| :kbd:`Alt+e`            |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Alt+{`            | Move the cursor to the start of the current paragraph.                   |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Alt+}`            | Move the cursor to the end of the current paragraph.                     |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+_`           | Comments or uncomments the current or selected lines.                    |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`"`                | Wraps the current selection with: ""                                     |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`'`                | Wraps the current selection with: ''                                     |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`\``               | Wraps the current selection with: \`\`                                   |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`(`                | Wraps the current selection with: ()                                     |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`)`                | Wraps the current selection with: ()                                     |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`}`                | Wraps the current selection with: {}                                     |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`{`                | Wraps the current selection with: {}                                     |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`]`                | Wraps the current selection with: []                                     |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`[`                | Wraps the current selection with: []                                     |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`*`                | Wraps the current selection with: **                                     |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`_`                | Wraps the current selection with: __                                     |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+d`           | Duplicate the current line.                                              |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+d`           | Duplicate the current line.                                              |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+v`           | Paste the clipboard contents, replacing any current selection.           |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+c`           | Adds the current selection to the clipboard.                             |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+x`           | Removes the current selection and adds it to the clipboard.              |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+k`           | Removes the current line adds it to the clipboard.                       |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Alt+Up`           | Move the current or selected lines up by one line.                       |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Alt+Down`         | Move the current or selected lines down by one line.                     |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Enter`            | Accept an input.                                                         |
|                         |                                                                          |
| :kbd:`Ctrl+m`           |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Enter`            | Insert a new line, replacing any selection and indenting if appropriate. |
|                         |                                                                          |
| :kbd:`Ctrl+m`           |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Tab`              | Inndent the current or selected lines.                                   |
|                         |                                                                          |
| :kbd:`Ctrl+i`           |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Shift+Tab`        | Unindent the current or selected lines.                                  |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Backspace`        | Unindent the current or selected lines.                                  |
|                         |                                                                          |
| :kbd:`Ctrl+h`           |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`F16`              | Toggle the case of the current word or selection.                        |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+z`           | Undo the last edit.                                                      |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+y`           | Redo the last edit.                                                      |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Shift+Up`         | Start a new selection.                                                   |
|                         |                                                                          |
| :kbd:`Shift+Down`       |                                                                          |
|                         |                                                                          |
| :kbd:`Shift+Right`      |                                                                          |
|                         |                                                                          |
| :kbd:`Shift+Left`       |                                                                          |
|                         |                                                                          |
| :kbd:`Alt+Shift+Left`   |                                                                          |
|                         |                                                                          |
| :kbd:`Alt+Shift+Right`  |                                                                          |
|                         |                                                                          |
| :kbd:`Ctrl+Shift+Left`  |                                                                          |
|                         |                                                                          |
| :kbd:`Ctrl+Shift+Right` |                                                                          |
|                         |                                                                          |
| :kbd:`Shift+Home`       |                                                                          |
|                         |                                                                          |
| :kbd:`Shift+End`        |                                                                          |
|                         |                                                                          |
| :kbd:`Ctrl+Shift+Home`  |                                                                          |
|                         |                                                                          |
| :kbd:`Ctrl+Shift+End`   |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Shift+Up`         | Extend the selection.                                                    |
|                         |                                                                          |
| :kbd:`Shift+Down`       |                                                                          |
|                         |                                                                          |
| :kbd:`Shift+Right`      |                                                                          |
|                         |                                                                          |
| :kbd:`Shift+Left`       |                                                                          |
|                         |                                                                          |
| :kbd:`Alt+Shift+Left`   |                                                                          |
|                         |                                                                          |
| :kbd:`Alt+Shift+Right`  |                                                                          |
|                         |                                                                          |
| :kbd:`Ctrl+Shift+Left`  |                                                                          |
|                         |                                                                          |
| :kbd:`Ctrl+Shift+Right` |                                                                          |
|                         |                                                                          |
| :kbd:`Shift+Home`       |                                                                          |
|                         |                                                                          |
| :kbd:`Shift+End`        |                                                                          |
|                         |                                                                          |
| :kbd:`Ctrl+Shift+Home`  |                                                                          |
|                         |                                                                          |
| :kbd:`Ctrl+Shift+End`   |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`<Any>`            | Replace selection by what is typed.                                      |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Backspace`        | Delete the contents of the current selection.                            |
|                         |                                                                          |
| :kbd:`Delete`           |                                                                          |
|                         |                                                                          |
| :kbd:`Ctrl+h`           |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Up`               | Cancel the selection.                                                    |
|                         |                                                                          |
| :kbd:`Down`             |                                                                          |
|                         |                                                                          |
| :kbd:`Right`            |                                                                          |
|                         |                                                                          |
| :kbd:`Left`             |                                                                          |
|                         |                                                                          |
| :kbd:`Alt+Left`         |                                                                          |
|                         |                                                                          |
| :kbd:`Alt+Right`        |                                                                          |
|                         |                                                                          |
| :kbd:`Ctrl+Left`        |                                                                          |
|                         |                                                                          |
| :kbd:`Ctrl+Right`       |                                                                          |
|                         |                                                                          |
| :kbd:`Home`             |                                                                          |
|                         |                                                                          |
| :kbd:`End`              |                                                                          |
|                         |                                                                          |
| :kbd:`Ctrl+Home`        |                                                                          |
|                         |                                                                          |
| :kbd:`Ctrl+End`         |                                                                          |
+-------------------------+--------------------------------------------------------------------------+
| :kbd:`Ctrl+a`           | Select all text.                                                         |
+-------------------------+--------------------------------------------------------------------------+
.. _keybinding-definitions-end:
