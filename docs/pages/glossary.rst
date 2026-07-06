########
Glossary
########

.. glossary::
   :sorted:

   App
      A standalone euporie program built on top of :doc:`euporie-core
      <../packages/euporie-core>`. The shipped apps are
      :doc:`Notebook <../packages/notebook>`, :doc:`Console <../packages/console>`,
      :doc:`Preview <../packages/preview>` and :doc:`Hub <../packages/hub>`.

   Cell
      A single unit of a Jupyter notebook. Cells can be **code**, **markdown**
      or **raw**. Code cells are executed by the notebook's kernel and can
      produce rich outputs.

   Command
      A named, discoverable action registered with the central command
      registry. Commands can be invoked from the :term:`command palette`,
      from the :term:`command bar`, from a menu, from a toolbar, by pressing
      a key binding, or programmatically.

   Command bar
      A modal, single-line input displayed at the bottom of the screen,
      inspired by the vim and helix command line. Summoned with :kbd:`:` or
      :kbd:`Alt+:`, it lets you type a :term:`command` by name and run it
      with :kbd:`Enter`. It offers tab-completion of command names,
      validation (rejecting unrecognised commands), and a persistent history.
      Prefix the input with ``!`` (or summon the bar with :kbd:`Alt+!`) to
      run a system shell command. Close it with :kbd:`Escape` or
      :kbd:`Ctrl+C`. See also the :term:`command palette`.

   Command palette
      A searchable popup that lists every available :term:`command` in the
      current context. Summoned with :kbd:`Ctrl+Space`, it lets you type a
      query, navigate matches with the arrow keys, and run the selected
      command with :kbd:`Enter`. For a keyboard-driven, type-the-name
      alternative, see the :term:`command bar`.

   Color scheme
      The set of foreground and background colors used to render the
      interface. Selected via the :confval:`color_scheme` option, with a
      ``custom`` scheme configurable via :confval:`custom_foreground_color`
      and :confval:`custom_background_color`.

   Formatter
      An external command that reformats cell source code. Code is passed
      via standard input and the formatted result read from standard output.
      Configured via the :confval:`formatters` option.

   Language server
      A background process implementing the Language Server Protocol (LSP)
      that provides features such as linting, code inspection, completion
      and formatting. Configured via the :confval:`language_servers` and
      :confval:`enable_language_servers` options.

   Terminal multiplexer
      A program such as :program:`tmux` or :program:`screen` that allows
      multiple terminal sessions to run within a single terminal window.

   Widget
      An interactive control (such as a slider, button or text box) embedded
      in a notebook's output, backed by the kernel via the Jupyter widgets
      protocol.

   Edit Mode
      The state of a cell while you are editing its contents. Entered by
      pressing :kbd:`Enter` on a selected cell and exited with :kbd:`Esc`.
      In Edit Mode, key bindings primarily control text editing rather than
      navigation between cells.

   Editor mode
      The flavour of in-cell key bindings used while editing - one of
      ``micro``, ``emacs``, ``vi`` or ``helix``. Selected via the
      :confval:`edit_mode` configuration option.

   Kernel
      A backend process that runs the code in a notebook's cells. Kernels
      communicate with euporie using the standard Jupyter messaging
      protocol. See the :doc:`kernel guide <kernels>`.

   Pager
      A scrollable popup used to display long-form output - help text,
      docstrings, traceback information and so on. Operated with the same
      keys as :program:`less`.

   Tab
      A page within an :term:`app` window. Each open notebook or console
      session is shown as a tab, and tabs can be split, reordered, and
      docked.

   Dock
      A region around the edge of an :term:`app` window where :term:`tabs
      <Tab>` can be attached. Tabs can be moved between docks (top, bottom,
      left, right or floating) by dragging their tab handle.

   TUI
      Terminal user interface - a graphical-style interface rendered using
      text characters in a terminal emulator.

   Terminal graphics
      Pixel-accurate images rendered inside a terminal using one of several
      protocols - **Sixel**, **Kitty's terminal graphics protocol**, or
      **iTerm2's inline images** protocol. See the :doc:`terminal graphics
      guide <terminal_graphics>`.
