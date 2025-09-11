###############
Troubleshooting
###############

This page lists solutions to issues users have reported experiencing when using euporie.

Creating debug logs
-------------------

If you encounter issues, you can create a debug log to help diagnose the problem:

.. code-block:: bash

   euporie-notebook --log-file=debug.log --log-level=debug my-notebook.ipynb

This will create a detailed log file that can help identify what's going wrong.


Kernel not starting (shows * indefinitely)
-------------------------------------------

If cells get stuck showing ``*`` and never execute:

1. Ensure you have ``ipykernel`` installed in your environment:

   .. code-block:: bash

      pip install ipykernel

2. Register your kernel so euporie can discover it:

   .. code-block:: bash

      python -m ipykernel install --user


Images not displaying in tmux
-----------------------------

Tmux only supports sixel graphics in version 3.4 and later (and must be compiled with sixel support). For older tmux versions or when using kitty graphics, you can try:

.. code-block:: bash

   euporie-console --multiplexer-passthrough --force-graphics --graphics=kitty

For tmux inside kitty terminals, you can also use unicode placeholders:

.. code-block:: bash

   euporie-notebook --graphics=kitty-unicode --force-graphics --multiplexer-passthrough

Note that graphics may not display at the correct size over SSH connections.


PDF display requirements
------------------------

To display PDFs in euporie, you need to install additional dependencies:

- For ANSI art: ``chafa``, ``timg``, or ``tiv``
- For kitty/iTerm2 graphics: ``imagemagick``
- For sixel graphics: ``imagemagick`` or ``chafa``

Note: Only the first page of multi-page PDFs is currently displayed.


Neovim terminal mode
--------------------

Graphics do not work when running euporie inside Neovim's terminal mode. This is a limitation of Neovim's terminal emulation. Use a separate terminal window or tmux pane instead.


Kitty graphics not detected
---------------------------

If euporie is not detecting kitty graphics support and falls back to ANSI art, try launching with explicit graphics settings:

.. code-block:: bash

   euporie-notebook --graphics=kitty --force-graphics


Kitty clipboard confirmation dialog
-----------------------------------

If you see a clipboard access confirmation dialog when starting euporie in kitty, this is due to kitty's security settings. You can either:

1. Approve the dialog each time
2. Modify your kitty configuration to allow clipboard access
3. Disable euporie's clipboard detection (though this may limit clipboard functionality)


High memory usage with IPython history
--------------------------------------

If euporie uses excessive memory or hangs on startup, this may be due to very long entries in your IPython history. You can:

1. Set autosuggest to "simple" mode in your configuration:

   .. code-block:: json

      {
        "autosuggest": "simple"
      }

2. Or disable autosuggest entirely:

   .. code-block:: json

      {
        "autosuggest": "none"
      }


Language Server Protocol (LSP) errors
-------------------------------------

If you're using ``ruff-lsp`` and experiencing formatting issues, note that ``ruff-lsp`` is deprecated. Update your configuration to use the built-in ruff server:

.. code-block:: json

   {
     "language_servers": {
       "ruff": {
         "command": ["ruff", "server"],
         "languages": ["python"]
       }
     }
   }


Menu/mouse not working on OSX
-----------------------------

If mouse clicks are not registering correctly in iterm2 or Terminal.app:

1. Try using keyboard shortcuts (Ctrl+key, not Alt or Cmd)
2. Click on a notebook cell first to focus it, then try clicking the menu
3. Consider using alternative terminals like WezTerm where mouse support works better


SSH connections
---------------

When using euporie over SSH:

- Terminal size detection may fail, causing images to display at incorrect sizes
- Some graphics protocols may not work properly
- Consider using ``--force-graphics`` if graphics aren't detected
