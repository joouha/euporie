"""Tests for completion functionality."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

from apptk.completion import (
    CompleteEvent,
    FuzzyWordCompleter,
    NestedCompleter,
    PathCompleter,
    WordCompleter,
    merge_completers,
)
from apptk.document import Document


@contextmanager
def chdir(directory: str) -> Generator[None, None, None]:
    """Change current working directory temporarily."""
    orig_dir = Path.cwd()
    os.chdir(directory)

    try:
        yield
    finally:
        os.chdir(orig_dir)


def write_test_files(test_dir: str, names: Iterable[Any] | None = None) -> None:
    """Write test files in the test directory using the names list."""
    names = names or range(10)
    for i in names:
        Path(test_dir, str(i)).write_bytes(b"")


def test_pathcompleter_completes_in_current_directory() -> None:
    """Test PathCompleter completes in current directory."""
    completer = PathCompleter()
    doc_text = ""
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completions = list(completer.get_completions(doc, event))
    assert len(completions) > 0


def test_pathcompleter_completes_files_in_current_directory() -> None:
    """Test PathCompleter completes files in current directory."""
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    expected = sorted(str(i) for i in range(10))

    if not test_dir.endswith(os.path.sep):
        test_dir += os.path.sep

    with chdir(test_dir):
        completer = PathCompleter()
        # this should complete on the cwd
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = sorted(c.text for c in completions)
        assert expected == result

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_completes_files_in_absolute_directory() -> None:
    """Test PathCompleter completes files in absolute directory."""
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    expected = sorted(str(i) for i in range(10))

    test_dir = str(Path(test_dir).resolve())
    if not test_dir.endswith(os.path.sep):
        test_dir += os.path.sep

    completer = PathCompleter()
    # force unicode
    doc_text = str(test_dir)
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completions = list(completer.get_completions(doc, event))
    result = sorted(c.text for c in completions)
    assert expected == result

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_completes_directories_with_only_directories() -> None:
    """Test PathCompleter completes only directories when configured."""
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    # create a sub directory there
    Path(test_dir, "subdir").mkdir()

    if not test_dir.endswith(os.path.sep):
        test_dir += os.path.sep

    with chdir(test_dir):
        completer = PathCompleter(only_directories=True)
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        assert result == ["subdir"]

    # check that there is no completion when passing a file
    with chdir(test_dir):
        completer = PathCompleter(only_directories=True)
        doc_text = "1"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        assert completions == []

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_respects_completions_under_min_input_len() -> None:
    """Test PathCompleter respects min_input_len setting."""
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    # min len:1 and no text
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=1)
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        assert completions == []

    # min len:1 and text of len 1
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=1)
        doc_text = "1"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        assert result == [""]

    # min len:0 and text of len 2
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=0)
        doc_text = "1"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        assert result == [""]

    # create 10 files with a 2 char long name
    for i in range(10):
        Path(test_dir, str(i) * 2).write_bytes(b"")

    # min len:1 and text of len 1
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=1)
        doc_text = "2"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = sorted(c.text for c in completions)
        assert result == ["", "2"]

    # min len:2 and text of len 1
    with chdir(test_dir):
        completer = PathCompleter(min_input_len=2)
        doc_text = "2"
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        assert completions == []

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_does_not_expanduser_by_default() -> None:
    """Test PathCompleter does not expand ~ by default."""
    completer = PathCompleter()
    doc_text = "~"
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completions = list(completer.get_completions(doc, event))
    assert completions == []


def test_pathcompleter_can_expanduser() -> None:
    """Test PathCompleter can expand ~ when configured."""
    completer = PathCompleter(expanduser=True)
    doc_text = "~"
    doc = Document(doc_text, len(doc_text))
    event = CompleteEvent()
    completions = list(completer.get_completions(doc, event))
    assert len(completions) > 0


def test_pathcompleter_can_apply_file_filter() -> None:
    """Test PathCompleter can filter files."""
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    # add a .csv file
    Path(test_dir, "my.csv").write_bytes(b"")

    def file_filter(f: str) -> bool:
        return f and f.endswith(".csv")

    with chdir(test_dir):
        completer = PathCompleter(file_filter=file_filter)
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        assert result == ["my.csv"]

    # cleanup
    shutil.rmtree(test_dir)


def test_pathcompleter_get_paths_constrains_path() -> None:
    """Test PathCompleter get_paths constrains search path."""
    # setup: create a test dir with 10 files
    test_dir = tempfile.mkdtemp()
    write_test_files(test_dir)

    # add a subdir with 10 other files with different names
    subdir = str(Path(test_dir) / "subdir")
    Path(subdir).mkdir()
    write_test_files(subdir, "abcdefghij")

    def get_paths() -> list[str]:
        return ["subdir"]

    with chdir(test_dir):
        completer = PathCompleter(get_paths=get_paths)
        doc_text = ""
        doc = Document(doc_text, len(doc_text))
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        result = [c.text for c in completions]
        expected = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        assert expected == result

    # cleanup
    shutil.rmtree(test_dir)


def test_word_completer_static_word_list() -> None:
    """Test WordCompleter with static word list."""
    completer = WordCompleter(["abc", "def", "aaa"])

    # Static list on empty input.
    completions = completer.get_completions(Document(""), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "def", "aaa"]

    # Static list on non-empty input.
    completions = completer.get_completions(Document("a"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "aaa"]

    completions = completer.get_completions(Document("A"), CompleteEvent())
    assert [c.text for c in completions] == []

    # Multiple words ending with space. (Accept all options)
    completions = completer.get_completions(Document("test "), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "def", "aaa"]

    # Multiple words. (Check last only.)
    completions = completer.get_completions(Document("test a"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "aaa"]


def test_word_completer_ignore_case() -> None:
    """Test WordCompleter with ignore_case option."""
    completer = WordCompleter(["abc", "def", "aaa"], ignore_case=True)
    completions = completer.get_completions(Document("a"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "aaa"]

    completions = completer.get_completions(Document("A"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "aaa"]


def test_word_completer_match_middle() -> None:
    """Test WordCompleter with match_middle option."""
    completer = WordCompleter(["abc", "def", "abca"], match_middle=True)
    completions = completer.get_completions(Document("bc"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "abca"]


def test_word_completer_sentence() -> None:
    """Test WordCompleter with sentence option."""
    # With sentence=True
    completer = WordCompleter(
        ["hello world", "www", "hello www", "hello there"], sentence=True
    )
    completions = completer.get_completions(Document("hello w"), CompleteEvent())
    assert [c.text for c in completions] == ["hello world", "hello www"]

    # With sentence=False
    completer = WordCompleter(
        ["hello world", "www", "hello www", "hello there"], sentence=False
    )
    completions = completer.get_completions(Document("hello w"), CompleteEvent())
    assert [c.text for c in completions] == ["www"]


def test_word_completer_dynamic_word_list() -> None:
    """Test WordCompleter with dynamic word list."""
    called = [0]

    def get_words() -> list[str]:
        called[0] += 1
        return ["abc", "def", "aaa"]

    completer = WordCompleter(get_words)

    # Dynamic list on empty input.
    completions = completer.get_completions(Document(""), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "def", "aaa"]
    assert called[0] == 1

    # Static list on non-empty input.
    completions = completer.get_completions(Document("a"), CompleteEvent())
    assert [c.text for c in completions] == ["abc", "aaa"]
    assert called[0] == 2


def test_word_completer_pattern() -> None:
    """Test WordCompleter with custom pattern."""
    # With a pattern which support '.'
    completer = WordCompleter(
        ["abc", "a.b.c", "a.b", "xyz"],
        pattern=re.compile(r"^([a-zA-Z0-9_.]+|[^a-zA-Z0-9_.\s]+)"),
    )
    completions = completer.get_completions(Document("a."), CompleteEvent())
    assert [c.text for c in completions] == ["a.b.c", "a.b"]

    # Without pattern
    completer = WordCompleter(["abc", "a.b.c", "a.b", "xyz"])
    completions = completer.get_completions(Document("a."), CompleteEvent())
    assert [c.text for c in completions] == []


def test_fuzzy_completer() -> None:
    """Test FuzzyWordCompleter functionality."""
    collection = [
        "migrations.py",
        "django_migrations.py",
        "django_admin_log.py",
        "api_user.doc",
        "user_group.doc",
        "users.txt",
        "accounts.txt",
        "123.py",
        "test123test.py",
    ]
    completer = FuzzyWordCompleter(collection)
    completions = completer.get_completions(Document("txt"), CompleteEvent())
    assert [c.text for c in completions] == ["users.txt", "accounts.txt"]

    completions = completer.get_completions(Document("djmi"), CompleteEvent())
    assert [c.text for c in completions] == [
        "django_migrations.py",
        "django_admin_log.py",
    ]

    completions = completer.get_completions(Document("mi"), CompleteEvent())
    assert [c.text for c in completions] == [
        "migrations.py",
        "django_migrations.py",
        "django_admin_log.py",
    ]

    completions = completer.get_completions(Document("user"), CompleteEvent())
    assert [c.text for c in completions] == [
        "user_group.doc",
        "users.txt",
        "api_user.doc",
    ]

    completions = completer.get_completions(Document("123"), CompleteEvent())
    assert [c.text for c in completions] == ["123.py", "test123test.py"]

    completions = completer.get_completions(Document("miGr"), CompleteEvent())
    assert [c.text for c in completions] == [
        "migrations.py",
        "django_migrations.py",
    ]

    # Multiple words ending with space. (Accept all options)
    completions = completer.get_completions(Document("test "), CompleteEvent())
    assert [c.text for c in completions] == collection

    # Multiple words. (Check last only.)
    completions = completer.get_completions(Document("test txt"), CompleteEvent())
    assert [c.text for c in completions] == ["users.txt", "accounts.txt"]


def test_nested_completer() -> None:
    """Test NestedCompleter functionality."""
    completer = NestedCompleter.from_nested_dict(
        {
            "show": {
                "version": None,
                "clock": None,
                "interfaces": None,
                "ip": {"interface": {"brief"}},
            },
            "exit": None,
        }
    )

    # Empty input.
    completions = completer.get_completions(Document(""), CompleteEvent())
    assert {c.text for c in completions} == {"show", "exit"}

    # One character.
    completions = completer.get_completions(Document("s"), CompleteEvent())
    assert {c.text for c in completions} == {"show"}

    # One word.
    completions = completer.get_completions(Document("show"), CompleteEvent())
    assert {c.text for c in completions} == {"show"}

    # One word + space.
    completions = completer.get_completions(Document("show "), CompleteEvent())
    assert {c.text for c in completions} == {"version", "clock", "interfaces", "ip"}

    # One word + space + one character.
    completions = completer.get_completions(Document("show i"), CompleteEvent())
    assert {c.text for c in completions} == {"ip", "interfaces"}

    # One space + one word + space + one character.
    completions = completer.get_completions(Document(" show i"), CompleteEvent())
    assert {c.text for c in completions} == {"ip", "interfaces"}

    # Test nested set.
    completions = completer.get_completions(
        Document("show ip interface br"), CompleteEvent()
    )
    assert {c.text for c in completions} == {"brief"}


def test_deduplicate_completer() -> None:
    """Test merge_completers with deduplicate option."""

    def create_completer(deduplicate: bool) -> Any:
        return merge_completers(
            [
                WordCompleter(["hello", "world", "abc", "def"]),
                WordCompleter(["xyz", "xyz", "abc", "def"]),
            ],
            deduplicate=deduplicate,
        )

    completions = list(
        create_completer(deduplicate=False).get_completions(
            Document(""), CompleteEvent()
        )
    )
    assert len(completions) == 8

    completions = list(
        create_completer(deduplicate=True).get_completions(
            Document(""), CompleteEvent()
        )
    )
    assert len(completions) == 5
