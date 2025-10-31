"""Responsible for loading data from urls."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiohttp.client_reqrep import ClientResponse
from fsspec.implementations.http import HTTPFileSystem as FsHTTPFileSystem
from fsspec.implementations.http import get_client

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Callable
    from typing import Any

    import aiohttp


log = logging.getLogger(__name__)


class NoRaiseClientResponse(ClientResponse):
    """An ``aiohttp`` client response which does not raise on >=400 status responses."""

    @property
    def ok(self) -> bool:
        """Returns ``True`` if ``status`` is probably renderable."""
        return self.status not in {405}


class HTTPFileSystem(FsHTTPFileSystem):
    """A HTTP filesystem implementation which does not raise on errors."""

    def __init__(
        self,
        simple_links: bool = True,
        block_size: int | None = None,
        same_scheme: bool = True,
        size_policy: None = None,
        cache_type: str = "bytes",
        cache_options: dict[str, Any] | None = None,
        asynchronous: bool = False,
        loop: asyncio.AbstractEventLoop | None = None,
        client_kwargs: dict[str, Any] | None = None,
        get_client: Callable[..., aiohttp.ClientSession] = get_client,
        encoded: bool = False,
        **storage_options: Any,
    ) -> None:
        """Defaults to using :py:mod:`NoRaiseClientResponse` for responses."""
        client_kwargs = {
            "response_class": NoRaiseClientResponse,
            **(client_kwargs or {}),
        }
        super().__init__(
            simple_links=simple_links,
            block_size=block_size,
            same_scheme=same_scheme,
            size_policy=size_policy,
            cache_type=cache_type,
            cache_options=cache_options,
            asynchronous=asynchronous,
            loop=loop,
            client_kwargs=client_kwargs,
            get_client=get_client,
            encoded=encoded,
            **storage_options,
        )

    def _raise_not_found_for_status(self, response: ClientResponse, url: str) -> None:
        """Do not raise an exception for 404 errors."""
        response.raise_for_status()
