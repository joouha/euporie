###########
Development
###########

This document describes how to develop and release euporie.

Setting Up Development Environment
==================================

1. Clone the repository::

    git clone https://github.com/joouha/euporie.git
    cd euporie

2. Install dependencies using uv::

    uv sync

3. Install pre-commit hooks::

    uv run pre-commit install


Running Tests
=============

Run the test suite with pytest::

    uv run pytest


Code Formatting
===============

Format code using ruff::

    uv run ruff format .
    uv run ruff check --fix .


Changelog Management
====================

Euporie uses `towncrier <https://towncrier.readthedocs.io/>`_ to manage the changelog.
Instead of editing ``CHANGELOG.rst`` directly, contributors create small "news fragment"
files that are compiled into the changelog at release time.

Creating Changelog Fragments
----------------------------

When making a change that should be noted in the changelog, create a file in the
``changelog.d/`` directory. The filename should be the issue or PR number, followed
by the type of change:

- ``<number>.added`` - For new features
- ``<number>.changed`` - For changes to existing functionality
- ``<number>.fixed`` - For bug fixes
- ``<number>.removed`` - For removed features

The file should contain a single line describing the change.

Examples::

    # For a new feature (issue #123)
    echo "Add support for custom themes" > changelog.d/123.added

    # For a bug fix (PR #456)
    echo "Fix crash when opening empty notebook" > changelog.d/456.fixed

    # For a change (issue #789)
    echo "Improve startup performance by lazy-loading modules" > changelog.d/789.changed

If there is no associated issue or PR number, you can use a descriptive name::

    echo "Update documentation for new release process" > changelog.d/docs-release.added


Release Process
===============

Euporie uses unified versioning where all packages share the same version number.
The version is stored in the ``VERSION`` file at the repository root.

Preparing a Release
-------------------

1. Ensure all changes are committed and the repository is clean.

2. Run the release script to bump the version and compile the changelog::

    # To release the current dev version (removes -dev suffix)
    python scripts/release.py release release

    # To bump to a new minor version
    python scripts/release.py release minor

    # To bump to a new patch version
    python scripts/release.py release patch

    # To bump to a new major version
    python scripts/release.py release major

3. Review the changes::

    git show

4. Push the release commit::

    git push

Publishing
----------

Once the release commit is pushed, publish to PyPI::

    python scripts/publish.py

This script will:

1. Verify prerequisites (uv installed)
2. Check the version number is valid (no dev/rc/alpha/beta suffix)
3. Verify the git repository state (on main, clean, up-to-date)
4. Check the version tag doesn't already exist
5. Build all packages in dependency order
6. Run twine check on all built packages
7. Create and push the git tag
8. Upload all packages to PyPI

Post-Release
------------

After publishing, bump the version to the next development version::

    python scripts/release.py post-release
    git push

This will update the ``VERSION`` file to the next patch version with a ``-dev`` suffix.


Package Structure
=================

Euporie is organized as a monorepo with multiple packages:

- ``apptk`` - Extended prompt_toolkit functionality
- ``euporie-core`` - Core functionality shared by all apps
- ``euporie-console`` - Interactive console application
- ``euporie-notebook`` - Notebook editor application
- ``euporie-preview`` - Notebook preview/runner application
- ``euporie-hub`` - Multi-client SSH server

All packages share the same version number, which is read from the root ``VERSION`` file
using hatchling's dynamic versioning.

The root ``euporie`` package is a meta-package that depends on the main user-facing
packages (notebook, preview, console).
