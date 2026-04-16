from abc import abstractmethod
from typing import TYPE_CHECKING

from apptk.formatted_text import (
    HTML,
    AnyFormattedText,
    StyleAndTextTuples,
)
from apptk.layout.dimension import AnyDimension

if TYPE_CHECKING:
    from .base import ProgressBar, ProgressBarCounter

__all__ = [
    "Bar",
    "Formatter",
    "IterationsPerSecond",
    "Label",
    "Percentage",
    "Progress",
    "Rainbow",
    "SpinningWheel",
    "Text",
    "TimeElapsed",
    "TimeLeft",
    "create_default_formatters",
]

def create_default_formatters() -> list[Formatter]: ...

class Formatter:
    @abstractmethod
    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText: ...
    def get_width(self, progress_bar: ProgressBar) -> AnyDimension: ...

class Text(Formatter):
    text: AnyFormattedText
    def __init__(self, text: AnyFormattedText, style: str = "") -> None: ...
    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText: ...
    def get_width(self, progress_bar: ProgressBar) -> AnyDimension: ...

class Label(Formatter):
    width: AnyDimension
    suffix: str
    def __init__(self, width: AnyDimension = None, suffix: str = "") -> None: ...
    def _add_suffix(self, label: AnyFormattedText) -> StyleAndTextTuples: ...
    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText: ...
    def get_width(self, progress_bar: ProgressBar) -> AnyDimension: ...

class Percentage(Formatter):
    template = HTML("<percentage>{percentage:>5}%</percentage>")
    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText: ...
    def get_width(self, progress_bar: ProgressBar) -> AnyDimension: ...

class Bar(Formatter):
    template = HTML(
        "<bar>{start}<bar-a>{bar_a}</bar-a><bar-b>{bar_b}</bar-b><bar-c>{bar_c}</bar-c>{end}</bar>"
    )
    start: str
    end: str
    sym_a: str
    sym_b: str
    sym_c: str
    unknown: str
    def __init__(
        self,
        start: str = "[",
        end: str = "]",
        sym_a: str = "=",
        sym_b: str = ">",
        sym_c: str = " ",
        unknown: str = "#",
    ) -> None: ...
    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText: ...
    def get_width(self, progress_bar: ProgressBar) -> AnyDimension: ...

class Progress(Formatter):
    template = HTML("<current>{current:>3}</current>/<total>{total:>3}</total>")
    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText: ...
    def get_width(self, progress_bar: ProgressBar) -> AnyDimension: ...

class TimeElapsed(Formatter):
    template = HTML("<time-elapsed>{time_elapsed}</time-elapsed>")
    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText: ...
    def get_width(self, progress_bar: ProgressBar) -> AnyDimension: ...

class TimeLeft(Formatter):
    template = HTML("<time-left>{time_left}</time-left>")
    unknown = "?:??:??"
    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText: ...
    def get_width(self, progress_bar: ProgressBar) -> AnyDimension: ...

class IterationsPerSecond(Formatter):
    template = HTML(
        "<iterations-per-second>{iterations_per_second:.2f}</iterations-per-second>"
    )
    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText: ...
    def get_width(self, progress_bar: ProgressBar) -> AnyDimension: ...

class SpinningWheel(Formatter):
    template = HTML("<spinning-wheel>{0}</spinning-wheel>")
    characters = r"/-\|"
    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText: ...
    def get_width(self, progress_bar: ProgressBar) -> AnyDimension: ...

class Rainbow(Formatter):
    colors = ["#{:02x}{:02x}{:02x}".format(*_hue_to_rgb(h / 100.0)) for h in range(100)]
    formatter: Formatter
    def __init__(self, formatter: Formatter) -> None: ...
    def format(
        self,
        progress_bar: ProgressBar,
        progress: ProgressBarCounter[object],
        width: int,
    ) -> AnyFormattedText: ...
    def get_width(self, progress_bar: ProgressBar) -> AnyDimension: ...
