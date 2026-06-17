#####
apptk
#####

**A toolkit of extensions and enhancements for** `prompt_toolkit <https://github.com/prompt-toolkit/python-prompt-toolkit>`_.

.. content_start

``apptk`` is the foundation library that powers `euporie <https://github.com/joouha/euporie>`_'s rich
terminal user interfaces. It transparently extends ``prompt_toolkit`` using
`modshim <https://pypi.org/project/modshim/>`_, so existing code which imports from ``apptk`` gets
both the original ``prompt_toolkit`` API *and* a large set of additional features layered on top.

.. code-block:: python

   # apptk re-exports everything from prompt_toolkit, plus its own additions
   from apptk.application import Application
   from apptk.layout.containers import HSplit, VSplit, Window
   from apptk.widgets.docking import DockingSplit
   from apptk.widgets.panel import Panel

----

********
Features
********

Extended rendering & styles
===========================

* Additional style attributes beyond what ``prompt_toolkit`` supports:

  * Double, curvy, dotted and dashed underlines
  * Overline and fast blink
  * Underline colours (``ul:#rrggbb``)
  * OSC 8 hyperlinks (``link:https://...``)

* Terminal graphics protocols for inline images: Sixel, iTerm and Kitty
* Drop-shadow and decorative layout helpers
* Rich CSS-style colour and named-colour utilities

Format conversion
=================

A pluggable conversion registry (``apptk.convert``) for transforming between
content types, with formats for:

* ANSI, formatted text, base-64
* HTML, Markdown, Rich
* PIL, PNG, JPEG, SVG, PDF
* Sixel and other terminal-graphics outputs

Widgets & layout
================

* ``DockingSplit`` - drag-and-drop dockable tabbed panels (see ``examples/docking_demo.py``)
* ``Panel``, ``TabBar`` and toolbar widgets
* ``FormattedTextArea`` for displaying styled, selectable, hyperlinked text
* Menu system with mouse support
* Layout caching, scroll containers and additional margins/processors

Commands & key bindings
=======================

A centralized command registry (``apptk.commands``) that unifies actions
across menus, toolbars, key bindings and the command palette:

* ``@add_cmd(...)`` decorator to register a function as a named, discoverable
  ``Command`` with a title, description, icon, group, aliases and toggled state
* Attach any number of key bindings to a command, with per-binding filters,
  eager-mode and global-vs-local scoping
* Look up registered commands by name (``get_cmd("save-file")``) for use in
  menus, toolbars or programmatic invocation
* Build a ``KeyBindings`` instance from a set of commands, or derive commands
  from existing key bindings (``commands_from_key_bindings``)
* Extended key-handling layer on top of ``prompt_toolkit``'s, including
  Micro-editor and Helix-style binding modes alongside Vi and Emacs

Editing & input
===============

* Auto-suggestion, search and completion enhancements
* OSC 52 and pyperclip clipboard backends

Other utilities
===============

* HTML and ANSI formatted-text parsers (``apptk.formatted_text.html``, ``apptk.formatted_text.ansi``)
* Markdown rendering with ``markdown-it-py`` plugins
* LaTeX rendering via ``flatlatex``
* ``universal-pathlib`` / ``fsspec`` integration for remote paths
* Pygments-based lexers and additional filters

*******
Install
*******

``apptk`` is published on PyPI:

.. code-block:: console

   $ uv pip install apptk
   $ # OR
   $ python -m pip install apptk

It requires Python 3.10 or later.

*****
Usage
*****

Because ``apptk`` shims ``prompt_toolkit``, you can use it as a drop-in
replacement and simply import from ``apptk`` instead:

.. code-block:: python

   from apptk.application import Application
   from apptk.key_binding.key_bindings import KeyBindings
   from apptk.layout.containers import HSplit, Window
   from apptk.layout.controls import FormattedTextControl
   from apptk.layout.layout import Layout

   kb = KeyBindings()

   @kb.add("c-q")
   def _(event):
       event.app.exit()

   layout = Layout(HSplit([Window(FormattedTextControl("Hello from apptk!"))]))
   Application(layout=layout, key_bindings=kb, full_screen=True).run()

Define reusable named commands with the centralized registry, attach key
bindings declaratively, and look them up later from menus, the command
palette or other code:

.. code-block:: python

   from apptk.commands import add_cmd, get_cmd

   @add_cmd(
       name="save-file",
       title="Save file",
       description="Write the current buffer to disk.",
       keys=["c-s"],
   )
   def save_file(event):
       ...

   # Trigger the command programmatically
   get_cmd("save-file").run()

See the ``examples/`` directory for runnable demos:

* ``examples/docking_demo.py`` - interactive dockable tabbed panels
* ``examples/extended_styles.py`` - showcase of extended text styles

*******
Project
*******

``apptk`` is developed as part of the euporie project. Source code, issues and
documentation live with the rest of the monorepo:

* GitHub: https://github.com/joouha/euporie
* Documentation: https://euporie.readthedocs.io/
