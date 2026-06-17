################
Jupyter kernels
################

Euporie does not execute code itself - it sends code to a separate process called a **kernel** which evaluates it and sends back the results. This page explains how to install kernels, choose between them, and connect to a kernel that's already running.

.. note::

   The built-in ``local-python`` kernel is an exception: it runs code directly in a local Python interpreter within euporie's own process rather than in a separate kernel process. It requires no installation and is always available.

*******************
Installing a kernel
*******************

The default Python kernel (:py:mod:`ipykernel`) is the most common. Install it into the same Python environment that has the libraries you want to use:

.. code-block:: console

   $ pip install ipykernel
   $ python -m ipykernel install --user

The first line installs the kernel package; the second registers it with Jupyter so euporie can discover it.

You can install kernels for many other languages - R, Julia, Rust, Bash and more. The Jupyter project maintains a `list of available kernels <https://github.com/jupyter/jupyter/wiki/Jupyter-kernels>`_.

Each kernel publishes a "kernelspec" - a small JSON file describing how to launch it. Euporie discovers kernelspecs from the standard locations, the same way Jupyter Lab does.

*****************
Choosing a kernel
*****************

When you open a notebook with multiple kernels installed, euporie picks the kernel saved in the notebook's metadata if it's available. If it's not (or if there's no recorded kernel) the first available kernel is used.

To switch kernel from inside the notebook editor:

* Open the :menuselection:`Kernel` menu and select :menuselection:`Change kernel`, or
* Run :option:`change-kernel` from the command palette (:kbd:`Ctrl+Space`), or
* Click on the current kernel name in the statusbar.

The selected kernel is saved into the notebook's metadata when you save.

********************************
Connecting to an existing kernel
********************************

If you already have a kernel running (started by Jupyter Lab, ``jupyter kernel`` or ``ipykernel``), you can attach euporie to it instead of starting a new one:

.. code-block:: console

   $ euporie-console --connection-file /path/to/kernel-XXXX.json
   $ euporie-notebook --connection-file /path/to/kernel-XXXX.json my.ipynb

Connection files are usually written to :envvar:`JUPYTER_RUNTIME_DIR` (:file:`~/.local/share/jupyter/runtime` on Linux). When you start a kernel via ``jupyter kernel`` it will print the path of the connection file it created.

This is useful for:

* Sharing state with another notebook front-end while testing.
* Connecting euporie to a remote kernel via SSH port forwarding.
* Reattaching to a long-running computation after closing the front-end.

***************************
Restarting and interrupting
***************************

* :kbd:`0 0` (or :menuselection:`Kernel --> Restart kernel`) restarts the kernel, clearing its state.
* :kbd:`I I` (or :menuselection:`Kernel --> Interrupt kernel`) sends a :py:class:`KeyboardInterrupt` to the kernel - useful for cancelling a runaway computation.

**********************
Custom kernel commands
**********************

If you want a kernel that isn't already registered, write a kernelspec
file. The minimal layout is:

.. code-block:: text

   kernels/my-kernel/
   ├── kernel.json
   └── (optional) logo.png

:file:`kernel.json` looks like:

.. code-block:: json

   {
     "argv": ["python", "-m", "my_kernel", "-f", "{connection_file}"],
     "display_name": "My Kernel",
     "language": "python"
   }

Drop the :file:`my-kernel` directory under :file:`~/.local/share/jupyter/kernels/` and euporie will pick it up on next launch. See the :ref:`Jupyter kernel docs <jupyterclient:kernelspecs>` for the full schema.

*****************
Troubleshooting
*****************

If euporie shows ``No kernels found`` or cells stay stuck on ``*``:

1. Verify that :code:`jupyter kernelspec list` lists the kernel you expect.
2. If not, register the kernel: :code:`python -m ipykernel install --user` (for Python).
3. Check the kernel can start standalone: :code:`jupyter kernel` from the same environment.
4. Check euporie's debug log for kernel start-up errors: :code:`euporie-notebook --log-file=debug.log --log-level=debug`.

See :doc:`../troubleshooting` for further fixes.
