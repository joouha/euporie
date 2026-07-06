"""Application toolkit extending :py:mod:`prompt_toolkit` via module shimming.

:py:mod:`apptk` provides an enhanced, drop-in replacement namespace for
:py:mod:`prompt_toolkit`. It uses `modshim <https://pypi.org/project/modshim/>`_ to
overlay the ``apptk`` package onto :py:mod:`prompt_toolkit`, combining the original
library's functionality with Euporie's extensions and overrides.

The key benefit of this approach is that the original :py:mod:`prompt_toolkit` library
can be extended without modifying its source. Any module, class, or function not
explicitly overridden in :py:mod:`apptk` falls through to the corresponding
:py:mod:`prompt_toolkit` implementation, while overridden members transparently take
precedence.

"""

from typing import Any

from modshim import shim


def __getattr__(name: str) -> Any:
    """Lazily load the package version from metadata on first access."""
    if name == "__version__":
        from importlib.metadata import version

        return version("apptk")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


shim("prompt_toolkit", extras=["ptterm"])
