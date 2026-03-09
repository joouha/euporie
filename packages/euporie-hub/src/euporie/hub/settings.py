"""Hub app settings definitions."""

from __future__ import annotations

from euporie.core.config._setting import Setting
from upath import UPath


def _euporie_hub_app_choices() -> list[str]:
    """List known euporie-apps and their aliases."""
    from euporie.core.__main__ import available_apps
    from euporie.core.app import APP_ALIASES

    return sorted(
        {entry.name for entry in available_apps().values()} - {"launch", "hub"}
        | APP_ALIASES.keys()
    )


hub_app = Setting(
    name="hub_app",
    flags=["hub_app"],
    type_=str,
    help_="The application to launch",
    choices=_euporie_hub_app_choices,
    description="""
        The name of the application to launch.
    """,
)

host = Setting(
    name="host",
    flags=["--host"],
    type_=str,
    help_="The host address to bind to",
    default="",
    description="""
        This determines the host address the euporie hub SSH server will bind to.
    """,
)

port = Setting(
    name="port",
    flags=["--port"],
    type_=int,
    help_="The port for the ssh server to use",
    default=8022,
    schema={
        "minimum": 1,
        "maximum": 65535,
    },
    description="""
        This determines which port euporie will listen on for connections to
        euporie hub.
    """,
)

host_keys = Setting(
    name="host_keys",
    flags=["--host-keys"],
    nargs="*",
    type_=UPath,
    help_="Host keys to use for the SSH server",
    default=["/etc/ssh/ssh_host_ecdsa_key"],
    schema={
        "type": "array",
        "items": {
            "description": "SSH host key file path",
            "type": "string",
        },
    },
    description="""
        One or more SSH host key files to use for the euporie hub SSH server.
    """,
)

client_keys = Setting(
    name="client_keys",
    flags=["--client-keys"],
    nargs="*",
    type_=UPath,
    help_="Client public keys authorized to connect",
    default=["~/.ssh/authorized_keys"],
    schema={
        "type": "array",
        "items": {
            "description": "Path to file containing authorized public keys",
            "type": "string",
        },
    },
    description="""
        One or more OpenSSH-style :file:`authorized_keys` files, containing
        public keys for authorized clients.
    """,
)

auth = Setting(
    name="auth",
    flags=["--auth"],
    type_=bool,
    help_="Allow unauthenticated access to euporie hub",
    default=True,
    description="""
        When set, users will be able to access euporie hub without authentication.

        .. warning::

           This option is dangerous, as arbitrary code can be executed through
           euporie apps.
    """,
)
