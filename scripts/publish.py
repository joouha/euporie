# -*- coding: utf-8 -*-
"""Publishes a new releases of euporie."""
from pathlib import Path

from poetry_publish.publish import poetry_publish

import euporie
from euporie.core import __version__


def publish() -> "None":
    """Publishes a new release of euporie to pypi.org."""
    poetry_publish(
        package_root=Path(euporie.__file__).parent.parent,
        version=__version__,
    )


if __name__ == "__main__":
    publish()
