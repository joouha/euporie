############
Architecture
############

This page describes how the euporie code-base is organised, and how the
packages depend on each other.

************
Monorepo
************

Euporie is developed as a `uv <https://docs.astral.sh/uv/>`_ workspace
mono-repo. The repository contains a top-level ``euporie`` metapackage that
provides the ``euporie`` launcher, plus a number of independent packages
under ``packages/``:

.. code-block:: text

   euporie/
   ├── packages/
   │   ├── apptk/                 # prompt_toolkit extensions
   │   ├── euporie-core/          # shared application framework
   │   ├── euporie-console/       # interactive REPL app
   │   ├── euporie-notebook/      # notebook editor app
   │   ├── euporie-preview/       # non-interactive preview app
   │   └── euporie-hub/           # SSH server hosting the apps
   └── src/euporie/launch/        # the `euporie` launcher entry-point

All packages share the same version number, which is read from the root
``VERSION`` file via hatchling's dynamic versioning.

*****************
Package layering
*****************

The packages form a layered dependency graph:

.. code-block:: text

                       ┌────────────────┐
                       │     apptk      │   prompt_toolkit + extensions
                       └───────▲────────┘
                               │
                       ┌───────┴────────┐
                       │  euporie-core  │   app framework, kernel client,
                       │                │   rich rendering, widgets
                       └───────▲────────┘
                               │
   ┌──────┬──────────┬─────────┼─────────┬───────────────┐
   │      │          │         │         │               │
   │ ┌────┴─────┐ ┌──┴────┐ ┌──┴───┐ ┌───┴───┐ ┌─────────┴─────┐
   │ │ console  │ │ note. │ │ prev.│ │  hub  │ │ (third-party  │
   │ └──────────┘ └───────┘ └──────┘ └───────┘ │  apps you     │
   │                                           │  build)       │
   │                                           └───────────────┘
   │                       ┌──────────────┐
   └──────────────────────►│   euporie    │   launcher
                           └──────────────┘

* **apptk** extends ``prompt_toolkit`` using
  `modshim <https://pypi.org/project/modshim/>`_ - importing ``apptk.foo``
  re-exports ``prompt_toolkit.foo`` plus euporie-specific extensions.
* **euporie-core** consumes ``apptk`` and provides the abstract :class:`BaseApp`
  class, kernel client, configuration system, command registry, rich-output
  rendering and a library of reusable widgets.
* **euporie-console**, **euporie-notebook**, **euporie-preview** and
  **euporie-hub** each subclass :class:`BaseApp` (or, for the hub, host other
  apps).
* The top-level **euporie** package contains only the launcher, which dispatches
  to the appropriate sub-app based on its first command-line argument.

*****************
Source layout
*****************

Within each package, the layout follows a consistent pattern:

.. code-block:: text

   packages/<pkg>/
   ├── pyproject.toml      # package metadata
   ├── README.rst          # PyPI/GitHub overview (also pulled into the docs)
   ├── src/<pkg>/
   │   ├── __init__.py
   │   ├── app.py          # the App subclass for end-user packages
   │   ├── ...
   └── tests/              # package-specific tests

The ``euporie.core`` namespace is shared across the application packages -
``euporie.notebook``, ``euporie.console``, etc. each live under the same
``euporie`` namespace package as ``euporie.core``.

*****************
Configuration
*****************

The configuration system lives in ``euporie.core.config`` and is shared by
every app. Settings are declared as :class:`Setting` instances on each
sub-system (e.g. ``preview_settings.cell_stop``), and a single merged
``Config`` object is exposed on the running app. See the
:doc:`../pages/configuration` page for the user-facing view.

*************************
Commands and key bindings
*************************

Actions are registered with the ``apptk.commands`` registry using the
``@add_cmd`` decorator. Every menu entry, toolbar button, key binding and
command-palette entry references the same underlying :class:`Command`
object. See :doc:`../pages/keybindings` for the user-facing description and
``apptk.commands`` for the API.

*****************
Versioning
*****************

All packages share a single version. The version is stored in the root
``VERSION`` file, and each ``pyproject.toml`` reads it through hatchling's
dynamic versioning. The :doc:`release` script bumps the version, regenerates
the changelog and tags the release.
