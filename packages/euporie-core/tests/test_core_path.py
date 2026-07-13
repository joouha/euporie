"""Test module for euporie.core.path."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from euporie.core.path import UntitledPath, safe_write

if TYPE_CHECKING:
    from pathlib import Path as PathType


def test_safe_write_creates_file(tmp_path: PathType) -> None:
    """Writing atomically creates the target file with the given content."""
    target = tmp_path / "out.txt"
    with safe_write(target) as fp:
        fp.write("hello")
    assert target.read_text() == "hello"
    assert not (tmp_path / "out.txt.tmp").exists()


def test_safe_write_removes_tmp_on_error(tmp_path: PathType) -> None:
    """A failed write cleans up the temporary file and leaves no target."""
    target = tmp_path / "out.txt"

    def _write() -> None:
        with safe_write(target) as fp:
            fp.write("partial")
            raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        _write()
    assert not target.exists()
    assert not (tmp_path / "out.txt.tmp").exists()


def test_safe_write_creates_backup(tmp_path: PathType) -> None:
    """Writing with a backup preserves the original contents."""
    target = tmp_path / "out.txt"
    target.write_text("original")
    with safe_write(target, create_backup=True) as fp:
        fp.write("updated")
    assert target.read_text() == "updated"
    assert (tmp_path / "out.txt.bak.0").read_text() == "original"


def test_safe_write_increments_backup(tmp_path: PathType) -> None:
    """An existing backup number is skipped."""
    target = tmp_path / "out.txt"
    target.write_text("original")
    (tmp_path / "out.txt.bak.0").write_text("old backup")
    with safe_write(target, create_backup=True) as fp:
        fp.write("updated")
    assert (tmp_path / "out.txt.bak.0").read_text() == "old backup"
    assert (tmp_path / "out.txt.bak.1").read_text() == "original"


def test_safe_write_binary(tmp_path: PathType) -> None:
    """Binary mode writes bytes correctly."""
    target = tmp_path / "out.bin"
    with safe_write(target, mode="wb") as fp:
        fp.write(b"\x00\x01\x02")
    assert target.read_bytes() == b"\x00\x01\x02"


def test_untitled_path_does_not_exist() -> None:
    """An untitled path never exists on disk."""
    path = UntitledPath("untitled:/foo")
    assert path.exists() is False


def test_untitled_path_strips_scheme() -> None:
    """The ``untitled:`` scheme prefix is stripped from the path."""
    path = UntitledPath("untitled:/foo")
    assert path.as_posix() == "/foo"


def test_untitled_path_as_uri() -> None:
    """Untitled paths round-trip through the ``untitled:`` URI scheme."""
    path = UntitledPath("untitled:/foo")
    assert path.as_uri() == "untitled:/foo"
