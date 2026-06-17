#############
Configuration
#############

*******************
Configuring Euporie
*******************

Euporie has a range of configurable options which affect euporie's behaviour and appearance.

Options are validated at application startup, so if an option is set to an invalid value, it will be ignored.

The options can be set in three different ways:

Command Line Arguments
======================

Euporie can be configured by passing flags (and sometimes values) on the command line when euporie is launched. The flags for each configuration option and the allowed values are listed in :ref:`configuration-options`.

.. code-block:: console

   $ euporie --color-scheme=light --no-show-cell-borders --expand notebook.ipynb

Optionals set on the command line are not persisted, and only apply to the application which is being run.

Options set on the command line will override those set via an environment variable, in the configuration file, and the default values.

Environment Variables
=====================

Euporie can be configured by setting environment variables. Each option can be set by assigning a value to an environment variable with uppercase option name, prefixed with :envvar:`EUPORIE_` for global configuration settings.

To set a configuration option for an individual app, the environment variable should additionally be prefixed with the app's name: as :envvar:`EUPORIE_NOTEBOOK_`, :envvar:`EUPORIE_CONSOLE_`, :envvar:`EUPORIE_PREVIEW_`, or :envvar:`EUPORIE_HUB_` .

The global version of each configuration option's environment variable are listed in :ref:`configuration-options`.

Example
   .. code-block:: console

      $ EUPORIE_COLOR_SCHEME=light EUPORIE_SHOW_CELL_BORDERS=False EUPORIE_EXPAND=True euporie-notebook notebook.ipynb

Setting boolean values to an empty string will cause them to evaluate to ``False``.

Options set in via an environment variable will override those set in the configuration file and the default values.

Configuration File
==================

Euporie can be configured using a `TOML <https://toml.io/>`_ configuration file. The file takes the form of *key = value* pairs, where the key is one of the options listed in :ref:`configuration-options`.

Settings can be applied to an individual application by specifying them under a table named after that application (e.g. ``[notebook]``).

.. warning::
   The configuration file is read when euporie is launched, and modifying options from the :menuselection:`Settings` menu in euporie will cause the configuration file to be updated. Thus, any changes made to the configuration file while euporie is running may be lost, so this is not recommended.

Example
   .. code-block:: TOML

      color_scheme = "light"
      syntax_theme = "native"

      [notebook]
      expand = false
      always_show_tab_bar = true
      show_cell_borders = false

      [console]
      color_scheme = "default"
      syntax_theme = "dracula"

      [preview]
      show_cell_borders = true

File Location
   The location of Euporie's configuration file depends on your operating system:

   +-------------+-------------------------------------------------------------+
   | **Linux**   | :file:`$XDG_CONFIG_HOME/euporie/config.toml`                |
   +-------------+-------------------------------------------------------------+
   | **Mac OS**  | :file:`~/Library/Application Support/euporie/config.toml`   |
   +-------------+-------------------------------------------------------------+
   | **Windows** | :file:`%APPDATA%\\Local\\euporie\\config.toml`              |
   +-------------+-------------------------------------------------------------+

If the file cannot be parsed as valid TOML, the file will be ignored.

Options set in the configuration file will override the default values.

.. note::
   Earlier versions of euporie used a JSON configuration file
   (:file:`config.json`). If a legacy :file:`config.json` file is found, its
   values will still be read, but you should migrate your settings to
   :file:`config.toml` and remove the JSON file. A warning will be logged
   while the legacy file is present.

Application State
=================

In addition to the configuration file, euporie maintains a separate **state file** for transient, app-managed data which is not intended to be edited by hand. This includes things like the list of recently opened files and command and search history.

State is stored per-application in tables named after each application, and is updated automatically by euporie as you use it.

File Location
   The location of Euporie's state file depends on your operating system:

   +-------------+-------------------------------------------------------------+
   | **Linux**   | :file:`$XDG_DATA_HOME/euporie/state.toml`                   |
   +-------------+-------------------------------------------------------------+
   | **Mac OS**  | :file:`~/Library/Application Support/euporie/state.toml`    |
   +-------------+-------------------------------------------------------------+
   | **Windows** | :file:`%APPDATA%\\Local\\euporie\\state.toml`               |
   +-------------+-------------------------------------------------------------+

You should not normally need to edit the state file manually.

----

.. _configuration-options:

*********************
Configuration Options
*********************

All available configuration options are listed below:

.. include:: ../_inc/configuration_options.rst
