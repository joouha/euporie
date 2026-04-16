from collections.abc import Sequence

from apptk.formatted_text import AnyFormattedText
from apptk.layout.containers import AnyContainer
from apptk.layout.dimension import AnyDimension

from .base import Box, Button, Shadow

__all__ = [
    "Dialog",
]

class Dialog:
    body: AnyContainer
    title: AnyFormattedText
    container: Box | Shadow
    def __init__(
        self,
        body: AnyContainer,
        title: AnyFormattedText = "",
        buttons: Sequence[Button] | None = None,
        modal: bool = True,
        width: AnyDimension = None,
        with_background: bool = False,
    ) -> None: ...
    def __pt_container__(self) -> AnyContainer: ...
