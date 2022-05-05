"""Defines style properties for formatted text elements."""

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from typing import Optional

    from euporie.border import LineStyle


class WeightedLineStyle(NamedTuple):
    """A :class:`LineStyle` with a weight."""

    weight: "int"
    value: "LineStyle"


class WeightedInt(NamedTuple):
    """An :class:`int` with a weight."""

    weight: "int"
    value: "int"


class BorderLineStyle(NamedTuple):
    """A description of a cell border: a :class:`LineStyle` for each edge."""

    top: "Optional[LineStyle]" = None
    right: "Optional[LineStyle]" = None
    bottom: "Optional[LineStyle]" = None
    left: "Optional[LineStyle]" = None


class WeightedBorderLineStyle(NamedTuple):
    """A weighted description of a cell border: weighted values for each edge."""

    top: "WeightedLineStyle"
    right: "WeightedLineStyle"
    bottom: "WeightedLineStyle"
    left: "WeightedLineStyle"


class Padding(NamedTuple):
    """A weighted description of a cell padding: weighted values for each edge."""

    top: "Optional[int]"
    right: "Optional[int]"
    bottom: "Optional[int]"
    left: "Optional[int]"


class WeightedPadding(NamedTuple):
    """A description of a cell padding: :class:`LineStyle`s for each edge."""

    top: "WeightedInt"
    right: "WeightedInt"
    bottom: "WeightedInt"
    left: "WeightedInt"
