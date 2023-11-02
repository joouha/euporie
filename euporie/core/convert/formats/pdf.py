"""Contain function which convert data to pdf format."""

from __future__ import annotations

from euporie.core.convert.formats.common import base64_to_bytes_py
from euporie.core.convert.registry import register

register(
    from_="base64-pdf",
    to="pdf",
)(base64_to_bytes_py)
