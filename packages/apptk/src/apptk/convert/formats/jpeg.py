"""Contain functions which convert data to jpeg format."""

from __future__ import annotations

from apptk.convert.formats.common import base64_to_bytes_py
from apptk.convert.registry import register

register(
    from_="base64-jpeg",
    to="jpeg",
)(base64_to_bytes_py)
