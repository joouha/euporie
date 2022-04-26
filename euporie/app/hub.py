"""Run euporie as a multi-client SSH server."""

import logging
from asyncio import get_event_loop
from typing import TYPE_CHECKING

try:
    import asyncssh  # type: ignore
except ModuleNotFoundError as err:
    raise ModuleNotFoundError(
        "Euporie hub requires the the `asyncssh` python package\n"
        'Install euporie hub with: "pip install euporie[hub]"'
    ) from err

from prompt_toolkit.contrib.ssh import PromptToolkitSSHSession

from euporie.app.edit import EditApp
from euporie.config import config
from euporie.log import setup_logs

if TYPE_CHECKING:
    from typing import Awaitable, Callable

log = logging.getLogger(__name__)


class EuporieSSHServer(asyncssh.SSHServer):  # type: ignore
    """An SSH server which runs a :class:`prompt_toolkit.application.Application`.

    Authentication is configuratble.

    """

    def __init__(
        self, interact: "Callable[[PromptToolkitSSHSession], Awaitable[None]]"
    ) -> None:
        """Sets the interaction function for the SSH session."""
        self.interact = interact

    def begin_auth(self, username: str) -> bool:
        """Perform authentication in the SSH server."""
        if config.no_auth:
            # No authentication.
            return False
        return super().begin_auth(username)

    def session_requested(self) -> "PromptToolkitSSHSession":
        """Return an SSH session."""
        return PromptToolkitSSHSession(self.interact)


class HubApp(EditApp):
    """An app which runs as a multi-user SSH server."""

    @classmethod
    async def interact(cls, ssh_session: "PromptToolkitSSHSession") -> None:
        """Function to run the app asynchronously for the SSH server."""
        await cls().run_async()

    @classmethod
    def launch(cls) -> "None":
        """Launch the HubApp SSH server."""
        # Configure logging to include `asyncssh`'s log output
        # Log to stdout by default in the hub app
        config.defaults["log_file"] = "-"
        setup_logs(
            {
                "handlers": {
                    "stdout": {
                        "share_stream": False,
                        "level": "DEBUG" if config.debug else "INFO",
                    }
                },
                "loggers": {
                    "asyncssh": {
                        "handlers": ["stdout"],
                        "level": "DEBUG" if config.debug else "INFO",
                    }
                },
            }
        )

        if config.no_auth:
            log.warning(
                "This server has been configured without SSH authentication, "
                "meaning anyone can connect"
            )

        # Run the HubApp in an SSH server
        loop = get_event_loop()
        loop.run_until_complete(
            asyncssh.create_server(
                lambda: EuporieSSHServer(interact=cls.interact),
                host=config.host,
                port=config.port,
                server_host_keys=config.host_keys,
                authorized_client_keys=config.client_keys,
            )
        )
        log.info("Running euporie hub on port %s", config.port)
        loop.run_forever()
