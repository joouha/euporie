###########
Euporie Hub
###########

Euporie Hub allows a group of users to share the power of euporie over a multi-user SSH server, akin to JupyterHub.

It is launched by running :command:`euporie` with the :option:`hub` subcommand:

.. code-block:: console

   $ euporie hub

**********
User Guide
**********

Euporie hub requires a set of SSH host keys to run, which can be generated as follows:

.. code-block:: console

   $ ssh-keygen -t ed25519 -f ssh_host_ed25519_key

Euporie hub can then be run as follows, specifying the host and client key locations:

.. code-block:: console

   $ euporie-hub --host-keys ssh_host_ed25519_key --client-keys ~/.ssh/authorized_keys

You should now be able to log on using one of the SSH keys which appear in your :file:`authorized_keys` file.

----

**********************
Command Line Interface
**********************

.. include:: ../_inc/cli_flags.rst
   :start-after: .. _cli-euporie-hub-start:
   :end-before: .. _cli-euporie-hub-end:
