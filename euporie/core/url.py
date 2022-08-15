"""Responsible for loading data from urls."""

import base64
import binascii
import logging
from typing import TYPE_CHECKING
from urllib.parse import ParseResult, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from prompt_toolkit.cache import memoized

if TYPE_CHECKING:
    from typing import Optional, Union

    from upath import UPath

log = logging.getLogger(__name__)


@memoized(maxsize=128)
def load_url(
    url: "Union[UPath, str]", base: "Optional[Union[UPath, str]]" = None
) -> "Optional[bytes]":
    """Loads data from a url."""
    log.debug("Loading data from url `%s`", url)
    data = None

    if base is not None:
        url = urljoin(str(base), str(url))

    parsed_url = urlparse(str(url))

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
        request = Request(
            url, headers={"User-Agent": "euporie", "Host": parsed_url.netloc}
        )
        try:
            # The use of 'file:' scheme is intended
            data = urlopen(request, timeout=4).read()  # noqa S310
        except Exception:
            log.debug("Failed to load `%s`", url)

    return data
