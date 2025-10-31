"""Contain classes relating to kernel management."""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
from typing import TYPE_CHECKING

from jupyter_client import AsyncKernelManager
from jupyter_client.provisioning.local_provisioner import LocalProvisioner

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, TextIO

    from jupyter_client.connect import KernelConnectionInfo


log = logging.getLogger(__name__)


class LoggingLocalProvisioner(LocalProvisioner):  # type:ignore[misc]
    """A Jupyter kernel provisionser which logs kernel output."""

    async def launch_kernel(
        self, cmd: list[str], **kwargs: Any
    ) -> KernelConnectionInfo:
        """Launch a kernel with a command."""
        await super().launch_kernel(cmd, **kwargs)

        def log_kernel_output(pipe: TextIO, log_func: Callable) -> None:
            try:
                if pipe:
                    with pipe:
                        for line in iter(pipe.readline, ""):
                            log_func(line.rstrip())
            except StopIteration:
                pass

        if self.process is not None:
            # Start thread to listen for kernel output
            threading.Thread(
                target=log_kernel_output,
                args=(self.process.stdout, log.warning),
                daemon=True,
            ).start()

        return self.connection_info


def set_default_provisioner() -> None:
    """Set the default kernel provisioner to euporie's logging provisioner."""
    from jupyter_client.provisioning import KernelProvisionerFactory as KPF

    KPF.instance().default_provisioner_name = "logging-local-provisioner"


class EuporieKernelManager(AsyncKernelManager):
    """Kernel Manager subclass.

    ``jupyter_client`` replaces a plain ``python`` command with the current executable,
    but this is not desirable if the client is running in its own prefix (e.g. with
    ``pipx``). We work around this here.

    See https://github.com/jupyter/jupyter_client/issues/949
    """

    def format_kernel_cmd(self, extra_arguments: list[str] | None = None) -> list[str]:
        """Replace templated args (e.g. {connection_file})."""
        extra_arguments = extra_arguments or []
        assert self.kernel_spec is not None
        cmd = self.kernel_spec.argv + extra_arguments

        v_major, v_minor = sys.version_info[:2]
        if cmd and cmd[0] in {
            "python",
            f"python{v_major}",
            f"python{v_major}.{v_minor}",
        }:
            # If the command is `python` without an absolute path and euporie is
            # running in the same prefix as the kernel_spec file is located, use
            # sys.executable: otherwise fall back to the executable in the base prefix
            if (
                os.path.commonpath((sys.prefix, self.kernel_spec.resource_dir))
                == sys.prefix
            ):
                cmd[0] = sys.executable
            else:
                cmd[0] = sys._base_executable  # type: ignore [attr-defined]

        # Make sure to use the realpath for the connection_file
        # On windows, when running with the store python, the connection_file path
        # is not usable by non python kernels because the path is being rerouted when
        # inside of a store app.
        # See this bug here: https://bugs.python.org/issue41196
        ns = {
            "connection_file": os.path.realpath(self.connection_file),
            "prefix": sys.prefix,
        }

        if self.kernel_spec:
            ns["resource_dir"] = self.kernel_spec.resource_dir

        if self._launch_args:
            ns.update({str(k): str(v) for k, v in self._launch_args.items()})

        pat = re.compile(r"\{([A-Za-z0-9_]+)\}")

        def _from_ns(match: re.Match) -> str:
            """Get the key out of ns if it's there, otherwise no change."""
            return ns.get(match.group(1), match.group())

        return [pat.sub(_from_ns, arg) for arg in cmd]
