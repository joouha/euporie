"""Responsible for loading data from urls."""

from __future__ import annotations

import logging
import sys
from contextlib import contextmanager, suppress
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

_PATH_INIT_TAKES_ARGS = sys.version_info >= (3, 12)

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path
    from typing import IO, Any


log = logging.getLogger(__name__)


def safe_write(
    path: Path,
    *,
    mode: str = "w",
    create_backup: bool = False,
) -> Generator[IO, None, None]:
    """Write to a file atomically using a temporary file and rename.

    Writes to a temporary file alongside the target, then atomically renames
    it into place. Optionally creates a numbered backup of the original file
    via hard link before replacing it.

    Args:
        path: The target file path.
        mode: File open mode ("w" for text, "wb" for binary).
        create_backup: Whether to create a numbered backup of the original.

    Yields:
        A file object to write to.

    Raises:
        BaseException: Re-raises any exception from the writing block after cleanup.
    """
    tmp_path = path.with_name(path.name + ".tmp")
    succeeded = False
    fp = tmp_path.open(mode)
    try:
        yield fp
        succeeded = True
    finally:
        fp.close()
        if not succeeded:
            with suppress(FileNotFoundError):
                tmp_path.unlink()
        else:
            if create_backup:
                count = 0
                while True:
                    backup = path.with_name(f"{path.name}.bak.{count}")
                    if not backup.exists():
                        break
                    count += 1
                with suppress(FileNotFoundError):
                    backup.hardlink_to(path)
            tmp_path.rename(path)


safe_write = contextmanager(safe_write)


# Define custom universal_pathlib path implementations


def LazyUPath(*args: Any, **kwargs: Any) -> Path:
    """Lazily import and construct a :class:`upath.UPath`."""
    from upath import UPath

    return UPath(*args, **kwargs)


class UntitledPath(PurePosixPath):
    """A pure path for untitled files, as needed for LSP servers.

    These are virtual paths that never exist on disk. The ``untitled:`` URI
    scheme is preserved so LSP servers can identify unsaved documents.
    An :meth:`exists` method is provided (returning ``False``) so instances
    can be used interchangeably with concrete :class:`~pathlib.Path` objects
    in code that checks for path existence.
    """

    _scheme = "untitled"

    @classmethod
    def _strip_scheme(cls, args: tuple[object, ...]) -> tuple[object, ...]:
        """Strip the ``untitled:`` scheme prefix from path arguments."""
        cleaned: list[object] = []
        for arg in args:
            text = str(arg)
            if text.startswith(f"{cls._scheme}:"):
                text = text[len(cls._scheme) + 1 :]
            cleaned.append(text)
        return tuple(cleaned)

    def __new__(cls, *args: object, **kwargs: object) -> UntitledPath:
        """Create a new untitled path, stripping any ``untitled:`` scheme prefix."""
        return super().__new__(cls, *cls._strip_scheme(args), **kwargs)

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the path, stripping any ``untitled:`` scheme prefix."""
        if _PATH_INIT_TAKES_ARGS:
            super().__init__(*self._strip_scheme(args), **kwargs)
        else:
            super().__init__()

    def as_uri(self) -> str:
        """Return the path as an ``untitled:`` URI."""
        return f"{self._scheme}:{self.as_posix()}"

    def exists(self, *args: Any, **kwargs: Any) -> bool:
        """Untitled files are unsaved and never exist on disk."""
        return False

    def read_text(self, *args: Any, **kwargs: Any) -> str:
        """Untitled files have no on-disk content, so cannot be read."""
        raise NotImplementedError("Cannot read an untitled file")

    def read_bytes(self, *args: Any, **kwargs: Any) -> bytes:
        """Untitled files have no on-disk content, so cannot be read."""
        raise NotImplementedError("Cannot read an untitled file")
