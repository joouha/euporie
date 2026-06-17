######################
Extending euporie
######################

This page describes how to build your own terminal applications on top of
the euporie libraries.

You have two main starting points:

* :doc:`../packages/apptk` - if you want a richer ``prompt_toolkit`` with
  extra widgets, terminal graphics, an enhanced command/key-binding registry
  and format conversion utilities, but you don't need anything Jupyter-specific.
* :doc:`../packages/euporie-core` - if you want everything ``apptk`` provides,
  *plus* a Jupyter kernel client, notebook handling, rich-output rendering,
  configuration, dialogs, menus and an ``App`` base class.

*****************
Building on apptk
*****************

``apptk`` shims ``prompt_toolkit``, so you can use it as a drop-in
replacement and import everything from ``apptk`` instead. A minimal
application looks like:

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

For a more complete example, see ``packages/apptk/examples/docking_demo.py``
which demonstrates the dockable tabbed-panel widget.

Using the command registry
==========================

The centralised command registry lets you declare reusable named actions
once and then bind them to keys, menus, toolbars or the command palette:

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

   # Run the command programmatically
   get_cmd("save-file").run()

************************
Building on euporie-core
************************

If you want a Jupyter-aware terminal app, subclass :class:`~euporie.core.app.app.BaseApp`:

.. code-block:: python

   from euporie.core.app.base import BaseApp


   class MyApp(BaseApp):
       name = "my-app"


   if __name__ == "__main__":
       MyApp.launch()

:class:`~euporie.core.app.app.BaseApp` provides:

* The application loop, terminal detection and event handling
* Command palette, menu and key-binding infrastructure
* The kernel client (start/stop/connect kernels, send messages)
* Cell-output rendering with terminal graphics, tables, LaTeX, HTML, SVG and PDF
* Configuration loaded from CLI flags, environment variables and a config file
* Dialogs, search bars, pagers and many other reusable widgets

For more complete examples of how euporie's own apps are structured, look at
the source code of :doc:`../_api/euporie/console`,
:doc:`../_api/euporie/notebook` and :doc:`../_api/euporie/preview`.

*********************
Packaging your app
*********************

If you publish a third-party app, depend on the relevant euporie package(s)
in your ``pyproject.toml``:

.. code-block:: toml

   [project]
   name = "my-app"
   dependencies = [
       "euporie-core>=2.0",
   ]

   [project.scripts]
   my-app = "my_app.app:MyApp.launch"

You should pin to the major version of ``euporie-core`` you developed
against, since the application framework may change between major releases.
