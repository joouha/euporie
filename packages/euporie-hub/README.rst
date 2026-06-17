###########
euporie-hub
###########

**A multi-user SSH server for hosting euporie apps.**

.. image:: https://placehold.co/1200x400/1e1e1e/cccccc.png?text=euporie-hub+%E2%80%94+screenshot+placeholder
   :alt: euporie-hub screenshot placeholder
   :align: center

.. content_start

``euporie-hub`` is an SSH server that hosts euporie apps for remote, multi-user
access. Connect over plain SSH to launch ``euporie-notebook``,
``euporie-console`` or any other euporie app - no extra client required. It is
part of the `euporie <https://github.com/joouha/euporie>`_ suite and is built
on `euporie-core <../euporie-core>`_.

----

********
Features
********

* **SSH-native**: clients connect with the SSH client they already have
* **Hosts any euporie app**: ``notebook``, ``console`` etc.
* **Multi-user**: multiple users can connect simultaneously
* **Public-key authentication** via standard ``authorized_keys`` files
* **Built on ``asyncssh``** for an asyncio-native, dependency-light deployment

*******
Install
*******

.. code-block:: console

   $ uv tool install euporie-hub
   $ # OR
   $ pipx install euporie-hub
   $ # OR
   $ python -m pip install --user euporie-hub

Requires Python 3.10 or later.

*****
Setup
*****

Generate an SSH host key for the server:

.. code-block:: console

   $ ssh-keygen -t ed25519 -f ssh_host_ed25519_key

Then start the hub, telling it which app to serve and where to find the host
keys and authorised client keys:

.. code-block:: console

   $ euporie-hub notebook \
       --port 8022 \
       --host-keys ssh_host_ed25519_key \
       --client-keys ~/.ssh/authorized_keys

Clients can now connect with any SSH client:

.. code-block:: console

   $ ssh -p 8022 user@hostname

.. warning::

   You can disable authentication with ``--no-auth`` for local testing, but
   **do not** run an unauthenticated hub on a public network.

.. getting_started_end

*************
Documentation
*************

* App documentation: https://euporie.readthedocs.io/en/latest/packages/hub.html
* Project documentation: https://euporie.readthedocs.io/
* Source code: https://github.com/joouha/euporie

********
See also
********

* `euporie-notebook <../euporie-notebook>`_ - full TUI notebook editor
* `euporie-console <../euporie-console>`_ - interactive Jupyter console
* `euporie-preview <../euporie-preview>`_ - non-interactive notebook renderer

*******
License
*******

Distributed under the terms of the MIT license. See the
`LICENSE <https://github.com/joouha/euporie/blob/main/LICENSE>`_ file in the
project root for details.
