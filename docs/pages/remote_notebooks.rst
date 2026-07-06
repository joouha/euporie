##########################
Remote and cloud notebooks
##########################

Euporie can open notebooks from a wide variety of remote locations, not just the local filesystem. Internally it uses `universal-pathlib <https://universal-pathlib.readthedocs.io/en/latest/>`_ on top of :doc:`fsspec <fsspec:index>`, which means any filesystem that fsspec supports works as a notebook location.

**************
Opening by URL
**************

Pass a URL on the command line to open it directly:

.. code-block:: console

   $ euporie-notebook https://example.com/notebooks/example.ipynb
   $ euporie-preview https://example.com/notebooks/example.ipynb

You can also paste a URL into the :guilabel:`Open file dialog` (:kbd:`Ctrl+O`).

*************
Cloud storage
*************

For cloud storage you'll need the corresponding :doc:`fsspec <fsspec:index>` plugin installed.
Common ones:

* **S3** - install :mod:`s3fs` and use :file:`s3://bucket/key.ipynb`
* **Google Cloud Storage** - install :mod:`gcsfs` and use :file:`gs://bucket/key.ipynb`
* **Azure Blob Storage** - install :class:`adlfs <adlfs.AzureBlobFileSystem>` and use :file:`az://container/key.ipynb`
* **GitHub** - install :class:`fsspec <fsspec.spec.AbstractFileSystem>` (built-in plugin) and use :file:`github://user:repo@branch/path.ipynb`

Authentication uses the standard environment variables for each provider (e.g. :envvar:`AWS_PROFILE` / :envvar:`AWS_ACCESS_KEY_ID` for S3).

************
SSH and SFTP
************

You can open notebooks over SSH/SFTP - install :doc:`paramiko <paramiko:index>`-backed :doc:`fsspec <fsspec:index>` support and use :file:`ssh://user@host/path/to/notebook.ipynb` or :file:`sftp://` URLs.

******************************
HTTP, HTTPS and zipped sources
******************************

Plain :file:`http://` and :file:`https://` URLs work read-only. :file:`zip://` URLs let you open a notebook stored inside a zip file (which can itself live on any other supported filesystem - e.g. :file:`zip://example.ipynb::s3://bucket/notebooks.zip`).

***
Hub
***

If you want multiple users to share access to remote notebooks via SSH, :doc:`euporie-hub <../../packages/hub>` is a SSH server that hosts euporie :term:`apps <App>`. Users connect with a regular SSH client and get an interactive notebook editor with no extra software required on the client.

See the :doc:`hub user guide <../../packages/hub>` for setup details.
