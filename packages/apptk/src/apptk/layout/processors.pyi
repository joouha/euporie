import logging
from abc import abstractmethod
from collections.abc import Callable, Hashable
from typing import TYPE_CHECKING

from apptk.cache import SimpleCache
from apptk.document import Document
from apptk.filters import FilterOrBool
from apptk.formatted_text import AnyFormattedText, StyleAndTextTuples

if TYPE_CHECKING:
    from collections.abc import Callable

    from apptk.data_structures import Point

    from .controls import BufferControl, UIContent

SourceToDisplay = Callable[[int], int]
DisplayToSource = Callable[[int], int]
log = logging.getLogger(__name__)

__all__ = [
    "AfterInput",
    "AppendAutoSuggestion",
    "BeforeInput",
    "ConditionalProcessor",
    "DisplayMultipleCursors",
    "DummyProcessor",
    "DynamicProcessor",
    "HighlightIncrementalSearchProcessor",
    "HighlightMatchingBracketProcessor",
    "HighlightSearchProcessor",
    "HighlightSelectionProcessor",
    "PasswordProcessor",
    "Processor",
    "ReverseSearchProcessor",
    "ShowArg",
    "ShowLeadingWhiteSpaceProcessor",
    "ShowTrailingWhiteSpaceProcessor",
    "TabsProcessor",
    "Transformation",
    "TransformationInput",
    "merge_processors",
]

class TransformationInput:
    buffer_control: BufferControl
    document: Document
    lineno: int
    source_to_display: SourceToDisplay
    fragments: StyleAndTextTuples
    width: int
    height: int
    get_line: Callable[[int], StyleAndTextTuples] | None
    def __init__(
        self,
        buffer_control: BufferControl,
        document: Document,
        lineno: int,
        source_to_display: SourceToDisplay,
        fragments: StyleAndTextTuples,
        width: int,
        height: int,
        get_line: Callable[[int], StyleAndTextTuples] | None = None,
    ) -> None: ...
    def unpack(
        self,
    ) -> tuple[
        BufferControl, Document, int, SourceToDisplay, StyleAndTextTuples, int, int
    ]: ...

class Transformation:
    fragments: StyleAndTextTuples
    source_to_display: SourceToDisplay | None
    display_to_source: DisplayToSource | None
    def __init__(
        self,
        fragments: StyleAndTextTuples,
        source_to_display: SourceToDisplay | None = None,
        display_to_source: DisplayToSource | None = None,
    ) -> None: ...

class Processor:
    @abstractmethod
    def apply_transformation(
        self,
        transformation_input: TransformationInput,
    ) -> Transformation: ...

def merge_processors(processors: list[Processor]) -> Processor: ...

class DummyProcessor(Processor):
    def apply_transformation(
        self,
        transformation_input: TransformationInput,
    ) -> Transformation: ...

class HighlightSearchProcessor(Processor):
    _classname = "search"
    _classname_current = "search.current"
    def _get_search_text(self, buffer_control: BufferControl) -> str: ...
    def apply_transformation(
        self,
        transformation_input: TransformationInput,
    ) -> Transformation: ...

class HighlightIncrementalSearchProcessor(HighlightSearchProcessor):
    _classname = "incsearch"
    _classname_current = "incsearch.current"
    def _get_search_text(self, buffer_control: BufferControl) -> str: ...

class HighlightSelectionProcessor(Processor):
    def apply_transformation(
        self,
        transformation_input: TransformationInput,
    ) -> Transformation: ...

class PasswordProcessor(Processor):
    char: str
    def __init__(self, char: str = "*") -> None: ...
    def apply_transformation(self, ti: TransformationInput) -> Transformation: ...

class HighlightMatchingBracketProcessor(Processor):
    _closing_braces = "])}>"
    chars: str
    max_cursor_distance: int
    _positions_cache: SimpleCache[Hashable, list[tuple[int, int]]]
    def __init__(
        self, chars: str = "[](){}<>", max_cursor_distance: int = 1000
    ) -> None: ...
    def _get_positions_to_highlight(
        self, document: Document
    ) -> list[tuple[int, int]]: ...
    def apply_transformation(
        self,
        transformation_input: TransformationInput,
    ) -> Transformation: ...

class DisplayMultipleCursors(Processor):
    def apply_transformation(
        self,
        transformation_input: TransformationInput,
    ) -> Transformation: ...

class BeforeInput(Processor):
    text: AnyFormattedText
    style: str
    def __init__(self, text: AnyFormattedText, style: str = "") -> None: ...
    def apply_transformation(self, ti: TransformationInput) -> Transformation: ...
    def __repr__(self) -> str: ...

class ShowArg(BeforeInput):
    def __init__(self) -> None: ...
    def _get_text_fragments(self) -> StyleAndTextTuples: ...
    def __repr__(self) -> str: ...

class AfterInput(Processor):
    text: AnyFormattedText
    style: str
    def __init__(self, text: AnyFormattedText, style: str = "") -> None: ...
    def apply_transformation(self, ti: TransformationInput) -> Transformation: ...
    def __repr__(self) -> str: ...

class AppendAutoSuggestion(Processor):
    style: str
    def __init__(self, style: str = "class:auto-suggestion") -> None: ...
    def apply_transformation(self, ti: TransformationInput) -> Transformation: ...

class ShowLeadingWhiteSpaceProcessor(Processor):
    style: str
    get_char: Callable[[], str] | None
    def __init__(
        self,
        get_char: Callable[[], str] | None = None,
        style: str = "class:leading-whitespace",
    ) -> None: ...
    def apply_transformation(self, ti: TransformationInput) -> Transformation: ...

class ShowTrailingWhiteSpaceProcessor(Processor):
    style: str
    get_char: Callable[[], str] | None
    char: str
    def __init__(
        self,
        char: str = "·",
        style: str = "class:trailing-whitespace",
    ) -> None: ...
    def apply_transformation(self, ti: TransformationInput) -> Transformation: ...

class TabsProcessor(Processor):
    char1: str | Callable[[], str]
    char2: str | Callable[[], str]
    tabstop: int | Callable[[], int]
    style: str
    def __init__(
        self,
        tabstop: int | Callable[[], int] = 4,
        char1: str | Callable[[], str] = "|",
        char2: str | Callable[[], str] = "┈",
        style: str = "class:tab",
    ) -> None: ...
    def apply_transformation(self, ti: TransformationInput) -> Transformation: ...

class ReverseSearchProcessor(Processor):
    _excluded_input_processors: list[type[Processor]] = [
        HighlightSearchProcessor,
        HighlightSelectionProcessor,
        BeforeInput,
        AfterInput,
    ]
    def _get_main_buffer(
        self, buffer_control: BufferControl
    ) -> BufferControl | None: ...
    def _content(
        self,
        main_control: BufferControl,
        ti: TransformationInput,
    ) -> UIContent: ...
    def apply_transformation(self, ti: TransformationInput) -> Transformation: ...

class ConditionalProcessor(Processor):
    processor: Processor
    filter: FilterOrBool
    def __init__(self, processor: Processor, filter: FilterOrBool) -> None: ...
    def apply_transformation(
        self,
        transformation_input: TransformationInput,
    ) -> Transformation: ...
    def __repr__(self) -> str: ...

class DynamicProcessor(Processor):
    get_processor: Callable[[], Processor | None]
    def __init__(self, get_processor: Callable[[], Processor | None]) -> None: ...
    def apply_transformation(self, ti: TransformationInput) -> Transformation: ...

class _MergedProcessor(Processor):
    processors: list[Processor]
    def __init__(self, processors: list[Processor]) -> None: ...
    def apply_transformation(self, ti: TransformationInput) -> Transformation: ...

class AppendLineAutoSuggestion(AppendAutoSuggestion):
    def apply_transformation(self, ti: TransformationInput) -> Transformation: ...

class CursorProcessor(Processor):
    char: str
    style: str
    get_cursor_position: Callable[[], Point]
    def __init__(
        self,
        get_cursor_position: Callable[[], Point],
        char: str = "🮰",
        style: str = "class:mouse",
    ) -> None: ...
    def apply_transformation(self, ti: TransformationInput) -> Transformation: ...
