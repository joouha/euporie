Euporie Coding Conventions
==========================

This document outlines the coding conventions and style guidelines for the Euporie project. Adhering to these conventions ensures consistency across the codebase and makes it easier for contributors to understand and maintain the code.

Python Version
--------------

Euporie is developed using Python 3.7+. Make sure your code is compatible with this version and later.

Code Formatting
---------------

- Use 4 spaces for indentation. Do not use tabs.
- Limit all lines to a maximum of 88 characters.
- Use the configured `hatch fmt` for code formatting. Run `hatch fmt` before committing changes.

Imports
-------

- Use `from __future__ import annotations` at the beginning of each file to enable postponed evaluation of annotations.
- Group imports in the following order, separated by a blank line:
  1. Future imports
  2. Standard library imports
  3. Third-party library imports
  4. Local application/library specific imports
- Use absolute imports when possible.
- Avoid wildcard imports (`from module import *`).

Example:

.. code-block:: python

    from __future__ import annotations

    import os
    from collections.abc import Sequence

    import numpy as np
    from prompt_toolkit.application import Application

    from euporie.core.app import BaseApp
    from euporie.core.config import Config

Naming Conventions
------------------

- Use `snake_case` for function names, method names, and variables.
- Use `PascalCase` for class names.
- Use `UPPER_CASE` for constants.
- Prefix private attributes and methods with a single underscore.

Example:

.. code-block:: python

    GLOBAL_CONSTANT = 42

    class MyClass:
        def __init__(self):
            self._private_attribute = 10

        def public_method(self):
            pass

        def _private_method(self):
            pass

    def my_function():
        local_variable = 5

Type Annotations
----------------

Use type annotations for function arguments and return values. Use built-in types instead of deprecated type aliases from the `typing` module. For complex types, consider using type aliases or the `collections.abc` module.

Example:

.. code-block:: python

    from collections.abc import Sequence

    def process_data(data: list[dict[str, int]]) -> int | None:
        # Function implementation
        pass

    def calculate_average(numbers: Sequence[float]) -> float:
        # Function implementation
        pass

Docstrings
----------

Use Google-style docstrings for all modules, classes, and functions. Include a brief description, Args, Returns, and Raises sections where applicable. Do not include argument types if arguments are type annotated.

Example:

.. code-block:: python

    def calculate_average(numbers: List[float]) -> float:
        """Calculate the average of a list of numbers.

        Args:
            numbers: A list of numbers to average.

        Returns:
            The average of the input numbers.

        Raises:
            ValueError: If the input list is empty.
        """
        if not numbers:
            raise ValueError("Cannot calculate average of an empty list")
        return sum(numbers) / len(numbers)

Error Handling
--------------

- Use explicit exception types when raising or catching exceptions.
- Provide informative error messages.

Example:

.. code-block:: python

    def divide(a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

Comments
--------

- Use comments sparingly. Strive for self-documenting code.
- When necessary, use inline comments to explain complex logic or non-obvious decisions.

Testing
-------

- Write unit tests for all new functionality.
- Use `pytest` for running tests.
- Aim for high test coverage, but prioritize meaningful tests over coverage percentage.

Version Control
---------------

- Use descriptive commit messages that explain the purpose of the change.
- Keep commits focused and atomic (i.e., each commit should represent a single logical change).
- Always update CHANGELOG.rst when making changes that would be noticeable to users.
  Add entries under the "Upcoming" section in the appropriate category (Added/Changed/Fixed).

API Design
----------

- Follow the principle of least astonishment (POLA) when designing APIs.
- Use keyword arguments for optional parameters to improve readability and maintainability.
- Prefer composition over inheritance when designing class hierarchies.

Example:

.. code-block:: python

    class ConsoleApp(BaseApp):
        def __init__(self, **kwargs: Any) -> None:
            kwargs.setdefault("title", "euporie-console")
            kwargs.setdefault("full_screen", False)
            super().__init__(**kwargs)

Performance Considerations
--------------------------

- Use profiling tools to identify performance bottlenecks.
- Prefer list comprehensions and generator expressions over `map()` and `filter()` for better readability and performance.
- Use `functools.lru_cache` for memoization when appropriate.

Example:

.. code-block:: python

    from functools import lru_cache

    @lru_cache(maxsize=None)
    def fibonacci(n: int) -> int:
        if n < 2:
            return n
        return fibonacci(n-1) + fibonacci(n-2)

Conclusion
----------

These conventions are designed to promote consistency and maintainability in the Euporie project. When in doubt, consult existing code or ask for clarification from other contributors. Remember that readability and clarity should always be prioritized over clever or overly concise code.
