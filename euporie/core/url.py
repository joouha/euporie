"""Responsible for loading data from urls."""

import base64
import binascii
import logging
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse, urlunparse
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
    # "tuple[str, str|None, bytes]":
    log.debug("Loading data from url `%s`", url)
    data = None

    if base is not None:
        url = urljoin(str(base), str(url))

    parsed_url = urlparse(str(url))

    # If not scheme given, assume it is a local file
    if not parsed_url.scheme:
        parsed_url = parsed_url._replace(scheme="file")
        url = urlunparse(parsed_url)

    elif parsed_url.scheme == "data":
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
            response = urlopen(request, timeout=4)
            data = response.read()  # noqa S310

        except Exception:
            log.debug("Failed to load `%s`", url)

        else:
            url = response.url
            # TODO - Get mime type from response

    return data
    # return url, mime, data
