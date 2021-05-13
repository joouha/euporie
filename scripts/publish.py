# -*- coding: utf-8 -*-
from pathlib import Path

from poetry_publish.publish import poetry_publish

import euporie


def publish():
    poetry_publish(
        package_root=Path(euporie.__file__).parent.parent,
        version=euporie.__version__,
    )


if __name__ == "__main__":
    publish()
