###########
Euporie Hub
###########

.. include:: ../../packages/euporie-hub/README.rst
   :start-after: .. content_start
   :end-before: .. getting_started_end

----

**********
User Guide
**********

Choosing an App to Serve
========================

By default, euporie-hub launches ``euporie-notebook`` for connecting clients. You can specify a different app as the first positional argument:

.. code-block:: console

   $ euporie-hub notebook    # default - notebook editor
   $ euporie-hub console     # interactive console

Any additional flags after the app name are passed through to the hosted app:

.. code-block:: console

   $ euporie-hub notebook --color-scheme=light --syntax-theme=monokai


Configuring Authentication
==========================

Public Key Authentication
-------------------------

The recommended approach is to use public key authentication. Create an ``authorized_keys`` file containing the public keys of users who should have access:

.. code-block:: console

   $ cat ~/.ssh/id_ed25519.pub >> /path/to/authorized_keys
   $ euporie-hub --client-keys /path/to/authorized_keys

Each user connects with their corresponding private key:

.. code-block:: console

   $ ssh -p 8022 user@hostname

The username in the SSH connection is not validated by default - any username will be accepted as long as the client presents a valid key from the ``authorized_keys`` file.

Disabling Authentication
------------------------

For local testing, you can disable authentication entirely:

.. code-block:: console

   $ euporie-hub --no-auth

.. warning::

   **Never** run an unauthenticated hub on a network accessible to untrusted users. This allows anyone to execute arbitrary code on the server.


Network Configuration
=====================

Binding Address and Port
------------------------

By default, euporie-hub listens on ``localhost:8022``. To listen on all interfaces (for remote access):

.. code-block:: console

   $ euporie-hub --host 0.0.0.0 --port 8022

To use a different port:

.. code-block:: console

   $ euporie-hub --port 2222

Connecting from Clients
-----------------------

Clients connect using any standard SSH client:

.. code-block:: console

   $ ssh -p 8022 user@hostname

For convenience, users can add a host entry to their ``~/.ssh/config``:

.. code-block:: text

   Host euporie
       HostName hostname.example.com
       Port 8022
       User myuser

Then connect simply with:

.. code-block:: console

   $ ssh euporie


Managing Host Keys
==================

Host keys identify the server to connecting clients. If clients see warnings about changed host keys, it typically means either:

- The server's host key was regenerated
- A man-in-the-middle attack (unlikely but possible)

To generate a new host key:

.. code-block:: console

   $ ssh-keygen -t ed25519 -f ssh_host_ed25519_key -N ""

The ``-N ""`` flag creates a key without a passphrase, which is required for unattended server startup.

You can use multiple host keys (e.g., for different key types):

.. code-block:: console

   $ euporie-hub --host-keys ssh_host_ed25519_key --host-keys ssh_host_rsa_key


Deployment Considerations
=========================

Running as a Service
--------------------

For production deployments, run euporie-hub as a system service. Example systemd unit file:

.. code-block:: ini

   [Unit]
   Description=Euporie Hub SSH Server
   After=network.target

   [Service]
   Type=simple
   User=euporie
   ExecStart=/usr/local/bin/euporie-hub \
       --host 0.0.0.0 \
       --port 8022 \
       --host-keys /etc/euporie/ssh_host_ed25519_key \
       --client-keys /etc/euporie/authorized_keys
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target

Resource Limits
---------------

Each connected user runs their own instance of the hosted euporie app, plus any Jupyter kernels they start. Consider:

- **Memory**: Each notebook session with an active kernel can consume significant memory
- **CPU**: Code execution in kernels can be CPU-intensive
- **Disk**: Notebook files and kernel outputs consume disk space

For shared deployments, consider using container orchestration or resource limits (e.g., cgroups) to prevent individual users from exhausting system resources.

Security Recommendations
------------------------

1. **Use public key authentication** - Disable password authentication in production
2. **Restrict network access** - Use firewalls to limit which hosts can connect
3. **Run as unprivileged user** - Don't run euporie-hub as root
4. **Keep software updated** - Regularly update euporie and its dependencies
5. **Monitor logs** - Watch for unusual connection patterns or authentication failures


----

**********************
Command Line Interface
**********************

.. include:: ../_inc/cli_flags.rst
   :start-after: .. _cli-euporie-hub-start:
   :end-before: .. _cli-euporie-hub-end:

----

******************
Available Commands
******************

.. toctree::

   hub_commands
