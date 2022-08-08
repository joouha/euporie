"""Defines custom inputs and outputs, and related methods."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.data_structures import Size
from prompt_toolkit.input.base import DummyInput, _dummy_context_manager

if TYPE_CHECKING:
    from typing import Any, Callable, ContextManager, Optional

    from prompt_toolkit.data_structures import Point


class IgnoredInput(DummyInput):
    """An input which ignores input but does not immediately close the app."""

    def attach(
        self, input_ready_callback: "Callable[[], None]"
    ) -> "ContextManager[None]":
        """.Do not call the callback, so the input is never closed."""
        return _dummy_context_manager()


def patch_renderer_diff() -> "None":
    """Monkey-patches prompt-toolkit's renderer module to extend the screen height."""
    from prompt_toolkit import renderer

    # Monkey patch the screen size
    _original_output_screen_diff = renderer._output_screen_diff

    def _patched_output_screen_diff(
        *args: "Any", **kwargs: "Any"
    ) -> "tuple[Point, Optional[str]]":
        """Function used to monkey-patch the renderer to extend the application height."""
        # Remove ZWE from screen
        # from collections import defaultdict
        # args[2].zero_width_escapes = defaultdict(lambda: defaultdict(lambda: ""))

        # Tell the renderer we have one additional column. This is to prevent the use of
        # carriage returns and cursor movements to write the final character on lines,
        # which is something the prompt_toolkit does
        size = kwargs.pop("size")
        kwargs["size"] = Size(9999999, size.columns + 1)
        return _original_output_screen_diff(*args, **kwargs)

    renderer._output_screen_diff = _patched_output_screen_diff
