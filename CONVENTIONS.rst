Euporie Coding Conventions
==========================

This document defines the coding conventions for the Euporie project, a terminal-based interactive computing environment built on ``prompt_toolkit``.

Project Overview
----------------

Euporie is a monorepo containing multiple packages:

- ``apptk``: Extensions to ``prompt_toolkit`` via module shimming
- ``euporie-core``: Core functionality shared across applications
- ``euporie-console``: Interactive console application
- ``euporie-notebook``: Notebook editing application
- ``euporie-preview``: Notebook preview application
- ``euporie-hub``: Multi-user hub application

Python Version
--------------

Target Python 3.10+. Use modern syntax and features available in this version.

Package Management
------------------

The project uses ``uv`` for package management and ``hatch`` for builds:

.. code-block:: bash

    # Install dependencies
    uv sync

    # Run tests
    uv run pytest

    # Format code
    uv run ruff format

    # Lint code
    uv run ruff check --fix

Code Formatting
---------------

- **Indentation**: 4 spaces, no tabs
- **Line length**: 88 characters maximum
- **Formatter**: ``ruff format`` (configured in ``pyproject.toml``)
- **Linter**: ``ruff check`` with auto-fix enabled

Run ``uv run ruff format`` and ``uv run ruff check --fix`` before committing.

Imports
-------

Every Python file must begin with:

.. code-block:: python

    from __future__ import annotations

Import order (separated by blank lines):

1. Future imports (``from __future__ import annotations``)
2. Standard library imports
3. Third-party imports
4. Local imports

Rules:

- Use absolute imports
- No wildcard imports (``from module import *``)
- Import from ``apptk`` instead of ``prompt_toolkit`` when using shimmed functionality

.. code-block:: python

    from __future__ import annotations

    import os
    from collections.abc import Callable, Sequence
    from typing import TYPE_CHECKING, Any

    from apptk.application import Application
    from apptk.layout.containers import HSplit, VSplit

    from euporie.core.app import BaseApp
    from euporie.core.config import Config

    if TYPE_CHECKING:
        from apptk.key_binding import KeyBindings

Type Annotations
----------------

Always use type annotations for function signatures:

- Use built-in generics: ``list[str]``, ``dict[str, int]``, ``tuple[int, ...]``
- Use ``|`` for unions: ``str | None``, ``int | float``
- Use ``collections.abc`` for abstract types: ``Sequence``, ``Callable``, ``Mapping``
- Use ``TYPE_CHECKING`` block for import-only types to avoid circular imports

.. code-block:: python

    from __future__ import annotations

    from collections.abc import Callable, Sequence
    from typing import TYPE_CHECKING, Any

    if TYPE_CHECKING:
        from apptk.layout import Container

    def process_items(
        items: Sequence[str],
        callback: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Process a sequence of items."""
        ...

    def create_layout(children: list[Container]) -> Container:
        """Create a layout from children."""
        ...

Naming Conventions
------------------

- **Functions/methods/variables**: ``snake_case``
- **Classes**: ``PascalCase``
- **Constants**: ``UPPER_SNAKE_CASE``
- **Private members**: Single underscore prefix (``_private_method``)
- **Type variables**: ``_T``, ``_U``, ``_KT``, ``_VT``

.. code-block:: python

    from typing import TypeVar

    _T = TypeVar("_T")

    MAX_BUFFER_SIZE = 1024

    class DataProcessor:
        def __init__(self) -> None:
            self._cache: dict[str, Any] = {}

        def process(self, data: _T) -> _T:
            return self._transform(data)

        def _transform(self, data: _T) -> _T:
            ...

Docstrings
----------

Use Google-style docstrings. Include:

- Brief one-line description (imperative mood)
- Extended description if needed (blank line after brief)
- ``Args:`` section (omit types, they're in annotations)
- ``Returns:`` section
- ``Raises:`` section if applicable

.. code-block:: python

    def merge_configs(
        base: dict[str, Any],
        override: dict[str, Any],
        *,
        deep: bool = True,
    ) -> dict[str, Any]:
        """Merge two configuration dictionaries.

        Combines base and override configs, with override taking precedence.
        Nested dictionaries are merged recursively when deep=True.

        Args:
            base: The base configuration dictionary.
            override: Configuration values to override.
            deep: Whether to recursively merge nested dicts.

        Returns:
            A new dictionary with merged configuration.

        Raises:
            TypeError: If inputs are not dictionaries.
        """
        ...

Class docstrings should describe the class purpose and list public attributes:

.. code-block:: python

    class NotebookCell:
        """Represents a single cell in a notebook.

        A cell contains source code or markdown content and may have
        associated outputs from execution.

        Args:
            cell_type: The type of cell ("code" or "markdown").
            source: The cell's source content.

        Attributes:
            cell_type: The type of this cell.
            source: The source content.
            outputs: List of cell outputs (code cells only).
            execution_count: Execution counter (code cells only).
        """

        def __init__(self, cell_type: str, source: str) -> None:
            """Initialize the cell."""
            self.cell_type = cell_type
            self.source = source
            self.outputs: list[dict[str, Any]] = []
            self.execution_count: int | None = None

Classes and Inheritance
-----------------------

- Prefer composition over inheritance
- Use ``**kwargs`` with ``setdefault`` for flexible initialization
- Call ``super().__init__()`` appropriately

.. code-block:: python

    class ConsoleApp(BaseApp):
        """Console application for interactive computing."""

        def __init__(self, **kwargs: Any) -> None:
            """Initialize the console application."""
            kwargs.setdefault("title", "euporie-console")
            kwargs.setdefault("full_screen", False)
            super().__init__(**kwargs)

NamedTuple and Data Classes
---------------------------

Use ``NamedTuple`` for immutable data structures:

.. code-block:: python

    from typing import NamedTuple

    class DiInt(NamedTuple):
        """A pair of integers representing dimensions."""

        width: int
        height: int

    class GridChar(NamedTuple):
        """Character and style for grid rendering."""

        char: str
        style: str = ""

Module Shimming (apptk)
-----------------------

The ``apptk`` package extends ``prompt_toolkit`` using ``modshim``. This allows overriding and extending functionality without modifying the original library.

**Key principle**: Import from ``apptk`` instead of ``prompt_toolkit`` throughout the codebase.

To extend a ``prompt_toolkit`` class:

1. Create a file in ``packages/apptk/src/apptk/`` mirroring the ``prompt_toolkit`` structure
2. Import the original module as an alias
3. Subclass and extend

.. code-block:: python

    # packages/apptk/src/apptk/layout/containers.py
    from __future__ import annotations

    from apptk.layout import containers as ptk_containers

    class HSplit(ptk_containers.HSplit):
        """Extended HSplit with cached children."""

        @property
        def _all_children(self) -> list[Container]:
            """List of child objects, including padding."""

            def get() -> list[Container]:
                # Custom implementation with caching
                ...

            return self._cache.get("children", get)

The shimmed module combines original ``prompt_toolkit`` functionality with extensions.

Configuration System
--------------------

Use the ``Config`` class for application settings:

.. code-block:: python

    from euporie.core.config import Config

    Config.add_setting(
        "color_scheme",
        default="dark",
        help_="Color scheme for the interface",
        choices=["dark", "light", "auto"],
    )

Commands and Key Bindings
-------------------------

Use the ``Command`` class to create actions that can be bound to keys or menus:

.. code-block:: python

    from apptk.filters import has_focus
    from euporie.core.commands import Command

    @Command(
        title="Save Notebook",
        description="Save the current notebook to disk",
    )
    def save_notebook() -> None:
        """Save the current notebook."""
        app = get_app()
        app.save()

    # Add key binding
    save_notebook.add_keys(
        "c-s",
        filter=has_focus(notebook_control),
    )

Layout Components
-----------------

Use ``apptk`` layout containers for UI composition:

.. code-block:: python

    from apptk.layout.containers import HSplit, VSplit
    from apptk.layout.dimension import Dimension as D

    from euporie.core.widgets.layout import Box

    layout = HSplit([
        VSplit([
            Box(sidebar, width=D(preferred=30)),
            Box(main_content, width=D(weight=1)),
        ]),
        Box(statusbar, height=D.exact(1)),
    ])

Error Handling
--------------

- Use specific exception types
- Provide informative error messages
- Use ``raise ... from`` for exception chaining

.. code-block:: python

    def load_notebook(path: Path) -> NotebookNode:
        """Load a notebook from disk.

        Args:
            path: Path to the notebook file.

        Returns:
            The loaded notebook.

        Raises:
            FileNotFoundError: If the notebook doesn't exist.
            ValueError: If the file is not valid JSON.
        """
        if not path.exists():
            raise FileNotFoundError(f"Notebook not found: {path}")

        try:
            with path.open() as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid notebook format: {path}") from e

        return NotebookNode(data)

Caching
-------

Use ``SimpleCache`` for thread-safe memoization:

.. code-block:: python

    from apptk.cache import SimpleCache

    class MyControl:
        def __init__(self) -> None:
            self._cache = SimpleCache()

        def get_content(self) -> str:
            def compute() -> str:
                # Expensive computation
                ...

            return self._cache.get("content", compute)

Testing
-------

- Use ``pytest`` for all tests
- Place tests in ``tests/`` directories within each package
- Name test files ``test_*.py``
- Name test functions ``test_*``

.. code-block:: python

    import pytest

    from euporie.core.utils import dict_merge

    def test_dict_merge_simple() -> None:
        """Test basic dictionary merging."""
        target = {"a": 1, "b": 2}
        input_dict = {"b": 3, "c": 4}
        dict_merge(target, input_dict)
        assert target == {"a": 1, "b": 3, "c": 4}

    def test_dict_merge_nested() -> None:
        """Test nested dictionary merging."""
        target = {"a": {"x": 1}}
        input_dict = {"a": {"y": 2}}
        dict_merge(target, input_dict)
        assert target == {"a": {"x": 1, "y": 2}}

Run tests with:

.. code-block:: bash

    uv run pytest
    uv run pytest tests/test_specific.py -v

Pre-commit Hooks
----------------

The project uses pre-commit hooks (configured in ``.pre-commit-config.yaml``):

- Code formatting (``ruff format``)
- Linting (``ruff check``)
- Spell checking (``codespell``)
- YAML/TOML validation
- Tests (run only when Python files change)

Install hooks:

.. code-block:: bash

    uv run pre-commit install

Run manually:

.. code-block:: bash

    uv run pre-commit run --all-files

Version Control
---------------

- Write descriptive commit messages in imperative mood
- Keep commits atomic (one logical change per commit)
- Use towncrier for changelog management

Changelog Management
--------------------

The project uses `towncrier <https://towncrier.readthedocs.io/>`_ to manage changelog entries. Instead of editing ``CHANGELOG.rst`` directly, create news fragment files in the ``changelog.d/`` directory.

**Creating a changelog entry:**

1. Create a file in ``changelog.d/`` named ``<issue_number>.<type>.rst``
2. Write a brief description of the change in the file

Fragment types:

- ``added`` - New features
- ``changed`` - Changes in existing functionality
- ``deprecated`` - Features that will be removed in future versions
- ``removed`` - Features that have been removed
- ``fixed`` - Bug fixes
- ``security`` - Security-related changes

Example:

.. code-block:: bash

    # For a new feature related to issue #123
    echo "Added support for custom color schemes" > changelog.d/123.added.rst

    # For a bug fix related to issue #456
    echo "Fixed crash when opening empty notebooks" > changelog.d/456.fixed.rst

    # For changes without an issue number, use a unique identifier
    echo "Improved startup performance" > changelog.d/+perf-startup.changed.rst

**Compiling the changelog:**

The changelog is automatically compiled during the release process using ``scripts/release.py``. You can also preview it manually:

.. code-block:: bash

    # Preview without modifying files
    uv run towncrier build --draft

    # Build and update CHANGELOG.rst (done automatically during release)
    uv run towncrier build --version X.Y.Z

Common Patterns
---------------

**Getting the current application:**

.. code-block:: python

    from euporie.core.app.current import get_app

    def do_something() -> None:
        app = get_app()
        app.refresh()

**Working with formatted text:**

.. code-block:: python

    from apptk.formatted_text import StyleAndTextTuples
    from apptk.formatted_text.utils import fragment_list_width

    def render_line(fragments: StyleAndTextTuples) -> int:
        """Render fragments and return width."""
        width = fragment_list_width(fragments)
        ...
        return width

**Creating UI content:**

.. code-block:: python

    from apptk.layout.controls import UIContent

    def create_content() -> UIContent:
        return UIContent(
            get_line=lambda i: [...],
            line_count=10,
        )

File Organization
-----------------

Each package follows this structure:

.. code-block:: text

    packages/
    └── package-name/
        ├── src/
        │   └── package_name/
        │       ├── __init__.py
        │       ├── module.py
        │       └── subpackage/
        │           └── __init__.py
        ├── tests/
        │   └── test_module.py
        └── pyproject.toml

Summary
-------

Key points for contributors:

1. Always use ``from __future__ import annotations``
2. Import from ``apptk`` instead of ``prompt_toolkit``
3. Use type annotations on all function signatures
4. Write Google-style docstrings
5. Run ``uv run ruff format`` and ``uv run ruff check --fix`` before committing
6. **ALWAYS** create changelog entries in ``changelog.d/`` for user-visible changes
7. Write tests for new functionality
