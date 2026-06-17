###################
Language servers
###################

Euporie includes a `Language Server Protocol <https://microsoft.github.io/language-server-protocol/>`_ client, which gives you completion, diagnostics, hover information and document formatting from any standard :term:`language server`.

This guide describes how to configure a language server and what to expect when one is running.

Language server support must first be enabled by setting the :confval:`enable_language_servers` configuration option to ``true``, which can be done using the :menuselection:`Settings --> Code Tools --> Language Servers` menu.

***************
Default servers
***************

Euporie ships sensible defaults for the most common languages. If a :term:`kernel` is using a language for which a default server is configured, and the relevant server binary is on your :envvar:`PATH`, euporie will start it automatically.

The defaults can be inspected and overridden through the :confval:`language_servers` configuration option.

*****************************
Configuring a language server
*****************************

To override the defaults or add a new server, set the :confval:`language_servers` option in your config file:

.. code-block:: toml

   [language_servers.ruff]
   command = ["ruff", "server"]
   languages = ["python"]

   [language_servers.pyright]
   command = ["pyright-langserver", "--stdio"]
   languages = ["python"]

Each entry is keyed by a name (used for logs/UI) and contains:

* ``command`` - argv used to start the server.
* ``languages`` - list of language identifiers the server should activate for. These are matched against the running :term:`kernel`'s language.
* (Optional) ``settings`` - server-specific settings forwarded as the initialisation options.

If multiple servers are configured for the same language, they are all started concurrently and their results are merged.

**************
Common servers
**************

Python
======

* `ruff <https://docs.astral.sh/ruff/>`_ - the recommended option for fast linting and formatting (note: the older ``ruff-lsp`` project is deprecated; use ``ruff server`` instead).
* `pyright <https://github.com/microsoft/pyright>`_ - high-quality static type checker.
* `pylsp <https://github.com/python-lsp/python-lsp-server>`_ - a community LSP wrapping ``pylint``/``flake8``/``rope``/``yapf`` and friends.

R
=

* `languageserver <https://github.com/REditorSupport/languageserver>`_ - install via ``install.packages("languageserver")``.

Other languages
===============

Any standard LSP server works - including :program:`rust-analyzer`, :program:`typescript-language-server`, :program:`gopls` and :program:`clangd`. Just add an entry to :confval:`language_servers` pointing at the right command.

***********
Formatting
***********

If at least one configured server advertises document-formatting capability, euporie can format the current :term:`cell` on demand. Use the :option:`reformat-cells` :term:`command` from the :term:`command palette`, or whichever key binding you have it set to.

***********
Disabling
***********

To turn off LSP entirely, set the :confval:`enable_language_servers` option to ``false``:

.. code-block:: toml

   enable_language_servers = false

Or simply ensure that none of the relevant server binaries are on :envvar:`PATH`.
