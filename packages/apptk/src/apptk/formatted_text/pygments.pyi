from typing import TYPE_CHECKING

from .base import StyleAndTextTuples

if TYPE_CHECKING:
    from pygments.token import Token

__all__ = [
    "PygmentsTokens",
]

class PygmentsTokens:
    token_list: list[tuple[Token, str]]
    def __init__(self, token_list: list[tuple[Token, str]]) -> None: ...
    def __pt_formatted_text__(self) -> StyleAndTextTuples: ...
