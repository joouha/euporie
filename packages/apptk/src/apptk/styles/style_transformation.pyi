from abc import abstractmethod
from collections.abc import Callable, Hashable, Sequence

from apptk.filters import FilterOrBool
from apptk.utils import AnyFloat

from .base import Attrs

OPPOSITE_ANSI_COLOR_NAMES = {
    "ansidefault": "ansidefault",
    "ansiblack": "ansiwhite",
    "ansired": "ansibrightred",
    "ansigreen": "ansibrightgreen",
    "ansiyellow": "ansibrightyellow",
    "ansiblue": "ansibrightblue",
    "ansimagenta": "ansibrightmagenta",
    "ansicyan": "ansibrightcyan",
    "ansigray": "ansibrightblack",
    "ansiwhite": "ansiblack",
    "ansibrightred": "ansired",
    "ansibrightgreen": "ansigreen",
    "ansibrightyellow": "ansiyellow",
    "ansibrightblue": "ansiblue",
    "ansibrightmagenta": "ansimagenta",
    "ansibrightcyan": "ansicyan",
    "ansibrightblack": "ansigray",
}

__all__ = [
    "AdjustBrightnessStyleTransformation",
    "ConditionalStyleTransformation",
    "DummyStyleTransformation",
    "DynamicStyleTransformation",
    "ReverseStyleTransformation",
    "SetDefaultColorStyleTransformation",
    "StyleTransformation",
    "SwapLightAndDarkStyleTransformation",
    "merge_style_transformations",
]

class StyleTransformation:
    @abstractmethod
    def transform_attrs(self, attrs: Attrs) -> Attrs: ...
    def invalidation_hash(self) -> Hashable: ...

def merge_style_transformations(
    style_transformations: Sequence[StyleTransformation],
) -> StyleTransformation: ...
def get_opposite_color(colorname: str | None) -> str | None: ...

class SwapLightAndDarkStyleTransformation(StyleTransformation):
    def transform_attrs(self, attrs: Attrs) -> Attrs: ...

class ReverseStyleTransformation(StyleTransformation):
    def transform_attrs(self, attrs: Attrs) -> Attrs: ...

class SetDefaultColorStyleTransformation(StyleTransformation):
    fg: str | Callable[[], str]
    bg: str | Callable[[], str]
    def __init__(
        self, fg: str | Callable[[], str], bg: str | Callable[[], str]
    ) -> None: ...
    def transform_attrs(self, attrs: Attrs) -> Attrs: ...
    def invalidation_hash(self) -> Hashable: ...

class AdjustBrightnessStyleTransformation(StyleTransformation):
    min_brightness: AnyFloat
    max_brightness: AnyFloat
    def __init__(
        self,
        min_brightness: AnyFloat = 0.0,
        max_brightness: AnyFloat = 1.0,
    ) -> None: ...
    def transform_attrs(self, attrs: Attrs) -> Attrs: ...
    def _color_to_rgb(self, color: str) -> tuple[float, float, float]: ...
    def _interpolate_brightness(
        self,
        value: float,
        min_brightness: float,
        max_brightness: float,
    ) -> float: ...
    def invalidation_hash(self) -> Hashable: ...

class DummyStyleTransformation(StyleTransformation):
    def transform_attrs(self, attrs: Attrs) -> Attrs: ...
    def invalidation_hash(self) -> Hashable: ...

class DynamicStyleTransformation(StyleTransformation):
    get_style_transformation: Callable[[], StyleTransformation | None]
    def __init__(
        self,
        get_style_transformation: Callable[[], StyleTransformation | None],
    ) -> None: ...
    def transform_attrs(self, attrs: Attrs) -> Attrs: ...
    def invalidation_hash(self) -> Hashable: ...

class ConditionalStyleTransformation(StyleTransformation):
    style_transformation: StyleTransformation
    filter: FilterOrBool
    def __init__(
        self,
        style_transformation: StyleTransformation,
        filter: FilterOrBool,
    ) -> None: ...
    def transform_attrs(self, attrs: Attrs) -> Attrs: ...
    def invalidation_hash(self) -> Hashable: ...

class _MergedStyleTransformation(StyleTransformation):
    style_transformations: Sequence[StyleTransformation]
    def __init__(
        self, style_transformations: Sequence[StyleTransformation]
    ) -> None: ...
    def transform_attrs(self, attrs: Attrs) -> Attrs: ...
    def invalidation_hash(self) -> Hashable: ...
