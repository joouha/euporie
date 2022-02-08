"""Contains function which convert data to pdf format."""

from __future__ import annotations

from euporie.convert.base import register
from euporie.convert.formats.common import base64_to_bytes_py

register(
    from_="base64-pdf",
    to="pdf",
)(base64_to_bytes_py)
