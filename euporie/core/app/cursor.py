"""Define configurable cursors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.cursor_shapes import CursorShape, CursorShapeConfig

from euporie.core.filters import insert_mode, replace_mode

if TYPE_CHECKING:
    from typing import Any

    from prompt_toolkit.application.application import Application


class CursorConfig(CursorShapeConfig):
    """Determine which cursor mode to use."""

    def get_cursor_shape(self, app: Application[Any]) -> CursorShape:
        """Return the cursor shape to be used in the current state."""
        from euporie.core.app.app import BaseApp

        if isinstance(app, BaseApp) and app.config.set_cursor_shape:
            if insert_mode():
                if app.config.cursor_blink:
                    return CursorShape.BLINKING_BEAM
                else:
                    return CursorShape.BEAM
            elif replace_mode():
                if app.config.cursor_blink:
                    return CursorShape.BLINKING_UNDERLINE
                else:
                    return CursorShape.UNDERLINE
        return CursorShape.BLOCK
