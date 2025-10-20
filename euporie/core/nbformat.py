"""A simple, fast, version of `nbformat` which avoids validation at start-up.

Implements fast versions of `new_notebook` and `new_code_cell` functions which do not
perform validation, so do not require `jsonschema` to be imported.

Other functions are provided as shims which lazily import from the `nbformat`
library, so they do not affect application start-up time.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from importlib.util import find_spec
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from pathlib import Path
    from typing import IO, Any

log = logging.getLogger(__name__)


NOTEBOOK_EXTENSIONS = [".ipynb"]
if find_spec("jupytext") is not None:
    NOTEBOOK_EXTENSIONS.extend(
        [
            ".md",
            ".markdown",
            ".Rmd",
            ".py",
            ".coco",
            ".R",
            ".r",
            ".jl",
            ".cpp",
            ".ss",
            ".clj",
            ".scm",
            ".sh",
            ".ps1",
            ".q",
            ".m",
            ".wolfram",
            ".pro",
            ".js",
            ".ts",
            ".scala",
            ".rs",
            ".robot",
            ".resource",
            ".cs",
            ".fsx",
            ".fs",
            ".sos",
            ".java",
            ".groovy",
            ".sage",
            ".ml",
            ".hs",
            ".tcl",
            ".mac",
            ".gp",
            ".do",
            ".sas",
            ".xsh",
            ".lgt",
            ".logtalk",
            ".lua",
            ".go",
            ".qmd",
            ".myst",
            ".mystnb",
            ".mnb",
        ]
    )

# ################################# Fast Implementations #################################


class NotebookNode(dict):
    """A dict-like node with attribute-access.

    A reimplementation of :py:class:`nbformat.NotebookNode` which does not
    trigger validation.
    """

    def __getattr__(self, name: str) -> Any:
        """Get an attribute."""
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name: str, value: Any) -> None:
        """Set an attribute."""
        self[name] = value

    def __setitem__(self, key: str, value: Any) -> None:
        """Set an item."""
        if isinstance(value, Mapping) and not isinstance(value, NotebookNode):
            value = self._from_dict(value)
        super().__setitem__(key, value)

    def update(self, *args: Any, **kwargs: Any) -> None:
        """Update the notebook node from a dictionary."""
        if len(args) > 1:
            raise TypeError(f"update expected at most 1 arguments, got {len(args)}")
        if args:
            other = args[0]
            if isinstance(other, Mapping) or hasattr(other, "keys"):
                for key in other:
                    self[key] = other[key]
            else:
                for key, value in other:
                    self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    @classmethod
    def _from_dict(cls, d: Any) -> Any:
        """Recursively convert a dictionary to a NotebookNode."""
        if isinstance(d, dict):
            return cls({k: cls._from_dict(v) for k, v in d.items()})
        if isinstance(d, (tuple, list)):
            return [cls._from_dict(i) for i in d]
        return d


def _rejoin_mimebundle(data: dict[str, Any]) -> dict[str, Any]:
    """Rejoin the multi-line string fields in a mimebundle in-place."""
    for key, value in list(data.items()):
        if (
            key != "application/json"
            and not (key.startswith("application/") and key.endswith("+json"))
            and isinstance(value, list)
            and all(isinstance(line, str) for line in value)
        ):
            data[key] = "".join(value)
    return data


def _rejoin_lines(nb: NotebookNode) -> NotebookNode:
    """Rejoin multiline text into strings, reversing effects of :py:func:`split_lines`."""
    for cell in nb.cells:
        if "source" in cell and isinstance(cell.source, list):
            cell.source = "".join(cell.source)

        attachments = cell.get("attachments", {})
        for _, attachment in attachments.items():
            _rejoin_mimebundle(attachment)

        if cell.get("cell_type", None) == "code":
            for output in cell.get("outputs", []):
                output_type = output.get("output_type", "")
                if output_type in {"execute_result", "display_data"}:
                    _rejoin_mimebundle(output.get("data", {}))
                elif output_type and isinstance(output.get("text", ""), list):
                    output.text = "".join(output.text)
    return nb


def _strip_transient(nb: NotebookNode) -> NotebookNode:
    """Strip transient values that shouldn't be stored in files.

    This should be called in *both* read and write.
    """
    nb.metadata.pop("orig_nbformat", None)
    nb.metadata.pop("orig_nbformat_minor", None)
    nb.metadata.pop("signature", None)
    for cell in nb.cells:
        cell.metadata.pop("trusted", None)
    return nb


def read(
    fp: IO[str],
    as_version: int,
    capture_validation_error: dict | None = None,
    **kwargs: Any,
) -> NotebookNode:
    """Read a notebook from a file, without validation."""
    try:
        nb_dict = json.load(fp, **kwargs)

        # Fallback for non-v4 notebooks
        if nb_dict.get("nbformat") != 4:
            raise ValueError("Not a v4 notebook")

        nb = NotebookNode._from_dict(nb_dict)
        nb = _rejoin_lines(nb)
        nb = _strip_transient(nb)
        return nb
    except Exception:
        try:
            from jupytext import read as read_orig
        except ModuleNotFoundError:
            from nbformat import read as read_orig

        # Reset file pointer and use original implementation
        fp.seek(0)
        return read_orig(fp, as_version, capture_validation_error, **kwargs)


def new_notebook(**kwargs: Any) -> NotebookNode:
    """Create a new notebook, without validation."""
    nb = NotebookNode(
        nbformat=4,
        nbformat_minor=5,
        metadata=NotebookNode(),
        cells=[],
    )
    nb.update(kwargs)
    return nb


def new_code_cell(source: str = "", **kwargs: Any) -> NotebookNode:
    """Create a new code cell, without validation."""
    cell = NotebookNode(
        id=uuid4().hex[:8],
        cell_type="code",
        metadata=NotebookNode(),
        execution_count=None,
        source=source,
        outputs=[],
    )
    cell.update(kwargs)
    return cell


# ############################ Lazy-loaded nbformat shims ############################


def write(nb: NotebookNode, fp: IO[str] | str | Path, **kwargs: Any) -> None:
    """Write a notebook to a file."""
    try:
        from jupytext import write as write_orig
    except ModuleNotFoundError:
        from nbformat import write as write_orig

    write_orig(nb, fp, **kwargs)


def from_dict(d: Any) -> Any:
    """Convert a dictionary to a NotebookNode."""
    from nbformat import from_dict as from_dict_orig

    return from_dict_orig(d)


def new_markdown_cell(source: str = "", **kwargs: Any) -> NotebookNode:
    """Create a new markdown cell."""
    from nbformat.v4 import new_markdown_cell as new_markdown_cell_orig

    return new_markdown_cell_orig(source=source, **kwargs)


def new_raw_cell(source: str = "", **kwargs: Any) -> NotebookNode:
    """Create a new raw cell."""
    from nbformat.v4 import new_raw_cell as new_raw_cell_orig

    return new_raw_cell_orig(source=source, **kwargs)


def new_output(
    output_type: str, data: Any | None = None, **kwargs: Any
) -> NotebookNode:
    """Create a new output."""
    from nbformat.v4 import new_output as new_output_orig

    return new_output_orig(output_type, data=data, **kwargs)


def output_from_msg(msg: dict[str, Any]) -> NotebookNode:
    """Create a NotebookNode for an output from a kernel's IOPub message."""
    from nbformat.v4 import output_from_msg as output_from_msg_orig

    return output_from_msg_orig(msg)
