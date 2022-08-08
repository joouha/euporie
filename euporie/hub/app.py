"""Run euporie as a multi-client SSH server."""

from __future__ import annotations

import logging
from asyncio import get_event_loop
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

try:
    import asyncssh
except ModuleNotFoundError as err:
    raise ModuleNotFoundError(
        "Euporie hub requires the the `asyncssh` python package\n"
        'Install euporie hub with: "pip install euporie[hub]"'
    ) from err

from prompt_toolkit.contrib.ssh import PromptToolkitSSHSession
from upath import UPath

from euporie.core.app import BaseApp
from euporie.core.config import add_setting
from euporie.core.log import setup_logs

if TYPE_CHECKING:
    from typing import Type

log = logging.getLogger(__name__)


class EuporieSSHServer(asyncssh.SSHServer):  # type: ignore
    """Launch euporie hub, which serves a euporie app over SSH.

    Launches euporie hub, a multi-client SSH server running euporie, which
    allows multiple users to connect and run instances of a euporie app.

    """

    def __init__(self, app_cls: "Type[BaseApp]") -> None:
        """Sets the interaction function for the SSH session."""
        self.app_cls = app_cls

    def begin_auth(self, username: str) -> bool:
        """Perform authentication in the SSH server."""
        if self.app_cls.config.no_auth:
            # No authentication.
            return False
        return super().begin_auth(username)

    def session_requested(self) -> "PromptToolkitSSHSession":
        """Return an SSH session."""
        return PromptToolkitSSHSession(self.app_cls.interact)


class HubApp(BaseApp):
    """Hub App.

    An app which runs as a multi-user SSH server.

    This app never actually gets run, but is used to run another app in an SSH server.
    """

    @classmethod
    def launch(cls) -> "None":
        """Launch the HubApp SSH server."""
        # Configure some setting defaults
        cls.config.settings["log_file"].value = "-"
        cls.config.settings[
            "log_config"
        ].value = '{"loggers": {"asyncssh": {"handlers":["stdout"], "level": "DEBUG"}}}'

        # Load the app's configuration
        cls.config.load(cls)
        # Configure the logs
        setup_logs(cls.config)

        if cls.config.no_auth:
            log.warning(
                "This server has been configured without SSH authentication, "
                "meaning anyone can connect"
            )

        # Import the hubbed app
        if entry_point := {
            entry.name: entry for entry in entry_points()["euporie.apps"]
        }.get(cls.config.app):
            app_cls = entry_point.load()
        else:
            raise ValueError("Application `%s` not found", cls.config.app)

        # Run the HubApp in an SSH server
        loop = get_event_loop()
        loop.run_until_complete(
            asyncssh.create_server(
                lambda: EuporieSSHServer(app_cls=app_cls),
                host=cls.config.host,
                port=cls.config.port,
                server_host_keys=cls.config.host_keys,
                authorized_client_keys=cls.config.client_keys,
            )
        )
        log.info("Running euporie hub on port %s", cls.config.port)
        loop.run_forever()

    # ################################### Settings ####################################

    add_setting(
        name="app",
        flags=["--app"],
        default="notebook",
        type_=str,
        choices=["notebook", "console"],
        help_="App to run under euporie hub",
        description="""
            Determine which euporie app should be launched under euporie hub.
        """,
    )

    add_setting(
        name="host",
        flags=["--host"],
        type_=str,
        help_="The host address to bind to",
        default="",
        description="""
            This determines the host address the euporie hub SSH server will bind to.
        """,
    )

    add_setting(
        name="port",
        flags=["--port"],
        type_=int,
        help_="The port for the ssh server to use",
        default=8022,
        schema_={
            "minimum": 1,
            "maximum": 65535,
        },
        description="""
            This determines which port euporie will listen on for connections to
            euporie hub.
        """,
    )

    add_setting(
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

    add_setting(
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

    add_setting(
        name="no_auth",
        flags=["--no-auth"],
        type_=bool,
        help_="Allow unauthenticated access to euporie hub",
        default=False,
        description="""
            When set, users will be able to access euporie hub without authentication.

            .. warning::

               This option is dangerous, as arbitrary code can be executed through
               euporie apps.
        """,
    )
