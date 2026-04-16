import re

from .application import Application
from .formatted_text import ANSI, HTML
from .shortcuts import PromptSession, choice, print_formatted_text, prompt

pep440 = re.compile(
    r"^([1-9]\d*!)?(0|[1-9]\d*)(\.(0|[1-9]\d*))*((a|b|rc)(0|[1-9]\d*)?)?(\.post(0|[1-9]\d*))?(\.dev(0|[1-9]\d*)?)?$",
    re.UNICODE,
)
VERSION = tuple(int(v.rstrip("abrc")) for v in __version__.split(".")[:3])

__all__ = [
    "ANSI",
    "HTML",
    "VERSION",
    "Application",
    "PromptSession",
    "__version__",
    "choice",
    "print_formatted_text",
    "prompt",
]
