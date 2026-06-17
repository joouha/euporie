###############
Release process
###############

Euporie uses unified versioning where all packages share the same version
number. The version lives in the ``VERSION`` file at the repository root and
is read by every ``pyproject.toml`` via hatchling's dynamic versioning.

This page summarises the steps for releasing a new version. The tooling
itself lives in ``scripts/release.py`` and ``scripts/publish.py``.

*******************
Preparing a release
*******************

1. Ensure all changes are committed and the repository is clean.

2. Run the release script to bump the version and compile the changelog:

   .. code-block:: console

      # Release the current dev version (removes the -dev suffix)
      $ python scripts/release.py release release

      # Bump to a new minor / patch / major version
      $ python scripts/release.py release minor
      $ python scripts/release.py release patch
      $ python scripts/release.py release major

3. Review the generated changes:

   .. code-block:: console

      $ git show

4. Push the release commit:

   .. code-block:: console

      $ git push

***********
Publishing
***********

Once the release commit is on ``main``, publish to PyPI:

.. code-block:: console

   $ python scripts/publish.py

This script will:

1. Verify prerequisites (``uv`` installed)
2. Check the version number is valid (no dev/rc/alpha/beta suffix)
3. Verify the git repository state (on ``main``, clean, up-to-date)
4. Check that the version tag does not already exist
5. Build all packages in dependency order
6. Run ``twine check`` on every built package
7. Create and push the git tag
8. Upload all packages to PyPI

************
Post-release
************

After publishing, bump the version to the next development version:

.. code-block:: console

   $ python scripts/release.py post-release
   $ git push

This updates the ``VERSION`` file to the next patch version with a ``-dev``
suffix.

**********************
Changelog management
**********************

Euporie uses `towncrier <https://towncrier.readthedocs.io/>`_ to manage the
changelog. Instead of editing ``CHANGELOG.rst`` directly, contributors add
small "news fragment" files under ``changelog/`` which are compiled into the
changelog at release time.

When you make a change worth recording in the changelog, add a file named
``<issue-or-pr-number>.<type>``:

* ``<n>.added`` - new features
* ``<n>.changed`` - changes to existing functionality
* ``<n>.fixed`` - bug fixes
* ``<n>.removed`` - removed features

Each file should contain a single line describing the change. If there is
no associated issue or PR number, use a short descriptive name instead
(e.g. ``docs-release.added``).
