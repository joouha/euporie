from typing import TYPE_CHECKING

from .style import Style

if TYPE_CHECKING:
    from pygments.style import Style as PygmentsStyle
    from pygments.token import Token

__all__ = [
    "pygments_token_to_classname",
    "style_from_pygments_cls",
    "style_from_pygments_dict",
]

def style_from_pygments_cls(pygments_style_cls: type[PygmentsStyle]) -> Style: ...
def style_from_pygments_dict(pygments_dict: dict[Token, str]) -> Style: ...
def pygments_token_to_classname(token: Token) -> str: ...
