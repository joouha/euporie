"""Responsible for loading data from urls."""

import base64
import binascii
import logging
from typing import TYPE_CHECKING
from urllib.parse import ParseResult, urlparse, urlunparse
from urllib.request import urlopen

from prompt_toolkit.cache import memoized

if TYPE_CHECKING:
    from typing import Optional

log = logging.getLogger(__name__)


@memoized(maxsize=128)
def load_url(url: "str") -> "Optional[bytes]":
    """Loads data from a url."""
    log.debug("Loading data from url `%s`", url)
    data = None

    parsed_url = urlparse(url)

    # If not scheme given, assume it is a local file
    if not parsed_url.scheme:
        parsed_url = ParseResult(
            scheme="file",
            netloc=parsed_url.netloc,
            path=parsed_url.path,
            params=parsed_url.params,
            query=parsed_url.query,
            fragment=parsed_url.fragment,
            *parsed_url[6:],
        )
        url = urlunparse(parsed_url)

    if parsed_url.scheme == "data":
        _mime, _, url_data = parsed_url.path.partition(";")
        data_format, _, encoded_data = url_data.partition(",")
        if data_format == "base64":
            try:
                data = base64.b64decode(encoded_data)
            except binascii.Error:
                data = None
    else:
        try:
            data = urlopen(url).read()  # noqa S310 - use of 'file:' scheme is intended
        except Exception:
            log.debug("Failed to load `%s`", url)

    return data
