"""Miscellaneous control fields."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.layout.controls import UIContent, UIControl

if TYPE_CHECKING:
    from prompt_toolkit.formatted_text import (
        StyleAndTextTuples,
    )


class DummyControl(UIControl):
    """A dummy control object that doesn't paint any content."""

    def create_content(self, width: int, height: int) -> UIContent:
        """Return one blank line only."""

        def get_line(i: int) -> StyleAndTextTuples:
            return []

        return UIContent(get_line=get_line, line_count=1)


class FocusableDummyControl(DummyControl):
    """A dummy control object that doesn't paint any content."""

    def is_focusable(self) -> bool:
        """Make this control focusable."""
        return True
