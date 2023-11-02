"""Contain functions which convert data to jpeg format."""

from __future__ import annotations

from euporie.core.convert.formats.common import base64_to_bytes_py
from euporie.core.convert.registry import register

register(
    from_="base64-jpeg",
    to="jpeg",
)(base64_to_bytes_py)
