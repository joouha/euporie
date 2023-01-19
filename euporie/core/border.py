"""Defines border styles."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache, total_ordering
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from typing import Optional


class GridPart(Enum):
    """Defines the component characters of a grid.

    Character naming works as follows:

                ╭┈┈┈┈┈┈┈┈LEFT
                ┊ ╭┈┈┈┈┈┈MID
                ┊ ┊ ╭┈┈┈┈SPLIT
                ┊ ┊ ┊ ╭┈┈RIGHT
                ∨ ∨ ∨ v
          TOP┈> ┏ ━ ┳ ┓
          MID┈> ┃   ┃ ┃
        SPLIT┈> ┣ ━ ╋ ┫
       BOTTOM┈> ┗ ━ ┻ ┛

    """

    TOP_LEFT = 0
    TOP_MID = 1
    TOP_SPLIT = 2
    TOP_RIGHT = 3
    MID_LEFT = 4
    MID_MID = 5
    MID_SPLIT = 6
    MID_RIGHT = 7
    SPLIT_LEFT = 8
    SPLIT_MID = 9
    SPLIT_SPLIT = 10
    SPLIT_RIGHT = 11
    BOTTOM_LEFT = 12
    BOTTOM_MID = 13
    BOTTOM_SPLIT = 14
    BOTTOM_RIGHT = 15


class DirectionFlags(NamedTuple):
    """Flags which indicate the connection of a grid node."""

    north: "bool" = False
    east: "bool" = False
    south: "bool" = False
    west: "bool" = False


class Mask:
    """A mask which allows selection of a subset of a grid.

    Masks can be combined to construct more complex masks.
    """

    def __init__(self, mask: "dict[GridPart, DirectionFlags]") -> "None":
        """Create a new grid mask.

        Args:
            mask: A dictionary mapping grid parts to a tuple of direction flags.
                Not all :class:`GridPart`s need to be defined - any which are not
                defined are assumed to be set entirely to :cont:`False`.

        """
        self.mask = {part: mask.get(part, DirectionFlags()) for part in GridPart}

    def __add__(self, other: "Mask") -> "Mask":
        """Adds two masks, combining direction flags for each :class:`GridPart`.

        Args:
            other: Another mask to combine with this one

        Returns:
            A new combined mask.

        """
        return Mask(
            {
                key: DirectionFlags(
                    *(self.mask[key][i] | other.mask[key][i] for i in range(4))
                )
                for key in GridPart
            }
        )


class Masks:
    """A collection of default masks."""

    top_edge = Mask(
        {
            GridPart.TOP_LEFT: DirectionFlags(False, True, False, False),
            GridPart.TOP_MID: DirectionFlags(False, True, False, True),
            GridPart.TOP_SPLIT: DirectionFlags(False, True, False, True),
            GridPart.TOP_RIGHT: DirectionFlags(False, False, False, True),
        }
    )

    middle_edge = Mask(
        {
            GridPart.SPLIT_LEFT: DirectionFlags(False, True, False, False),
            GridPart.SPLIT_MID: DirectionFlags(False, True, False, True),
            GridPart.SPLIT_SPLIT: DirectionFlags(False, True, False, True),
            GridPart.SPLIT_RIGHT: DirectionFlags(False, False, False, True),
        }
    )

    bottom_edge = Mask(
        {
            GridPart.BOTTOM_LEFT: DirectionFlags(False, True, False, False),
            GridPart.BOTTOM_MID: DirectionFlags(False, True, False, True),
            GridPart.BOTTOM_SPLIT: DirectionFlags(False, True, False, True),
            GridPart.BOTTOM_RIGHT: DirectionFlags(False, False, False, True),
        }
    )

    left_edge = Mask(
        {
            GridPart.TOP_LEFT: DirectionFlags(False, False, True, False),
            GridPart.MID_LEFT: DirectionFlags(True, False, True, False),
            GridPart.SPLIT_LEFT: DirectionFlags(True, False, True, False),
            GridPart.BOTTOM_LEFT: DirectionFlags(True, False, False, False),
        }
    )

    center_edge = Mask(
        {
            GridPart.TOP_SPLIT: DirectionFlags(False, False, True, False),
            GridPart.MID_SPLIT: DirectionFlags(True, False, True, False),
            GridPart.SPLIT_SPLIT: DirectionFlags(True, False, True, False),
            GridPart.BOTTOM_SPLIT: DirectionFlags(True, False, False, False),
        }
    )

    right_edge = Mask(
        {
            GridPart.TOP_RIGHT: DirectionFlags(False, False, True, False),
            GridPart.MID_RIGHT: DirectionFlags(True, False, True, False),
            GridPart.SPLIT_RIGHT: DirectionFlags(True, False, True, False),
            GridPart.BOTTOM_RIGHT: DirectionFlags(True, False, False, False),
        }
    )

    inner = center_edge + middle_edge
    outer = top_edge + right_edge + bottom_edge + left_edge

    grid = inner + outer

    corners = Mask(
        {
            GridPart.TOP_LEFT: DirectionFlags(False, True, True, False),
            GridPart.TOP_RIGHT: DirectionFlags(False, False, True, True),
            GridPart.BOTTOM_LEFT: DirectionFlags(True, True, False, False),
            GridPart.BOTTOM_RIGHT: DirectionFlags(True, False, False, True),
        }
    )


@total_ordering
class LineStyle:
    """Defines a line style which can be used to draw grids.

    :class:`GridStyle`s can be created from a :class:`LineStyle` by accessing an
    attribute with the name of a default mask from :class:`Masks`.
    """

    def __init__(
        self,
        name: "str",
        rank: "tuple[int, int]",
        parent: "Optional[LineStyle]" = None,
        visible: "bool" = True,
    ) -> "None":
        """Creates a new :class:`LineStyle`.

        Args:
            name: The name of the line style
            rank: A ranking value - this is used when two adjoining cells in a table
                have differing widths or styles to determine which should take precedence.
                The style with the higher rank is used. The rank consists of a tuple
                representing width and fanciness.
            parent: The :class:`LineStyle` from which this style should inherit if any
                characters are undefined.
            visible: A flag to indicate if the line is blank

        """
        self.name = name
        self.rank = rank
        self.children: "dict[str, LineStyle]" = {}
        self.parent = parent
        self.visible = visible
        if parent:
            parent.children[name] = self

    def __getattr__(self, value: "str") -> "GridStyle":
        """Defines attribute access.

        Allows dynamic access to children and :class:`GridStyle` creation via attribute
        access.

        Args:
            value: The attribute name to access

        Returns:
            The accessed attribute

        Raises:
            AttributeError: Raised if there is no such attribute

        """
        if hasattr(Masks, value):
            mask = getattr(Masks, value)
            return GridStyle(self, mask)
        else:
            raise AttributeError(f"No such attribute `{value}`")

    def __dir__(self) -> "list[str]":
        """Lists the public attributes."""
        return [x for x in Masks.__dict__ if not x.startswith("_")]

    def __lt__(self, other: "LineStyle") -> "bool":
        """Allows :class:`LineStyle`s to be sorted according to their rank."""
        if self.__class__ is other.__class__:
            return self.rank < other.rank
        elif other is None:
            return None
        return NotImplemented

    def __repr__(self) -> "str":
        """A string representation of the :class:`LineStyle`."""
        return f"LineStyle({self.name})"


# Line Styles

# Equivalent to setting the border-stype to "none"
# - borders with a style of none have the lowest priority.
NoLine = LineStyle("None", rank=(0, 0), visible=False)
# Equivalent to setting the border-stype to "hidden"
# - takes precedence over all other conflicting borders.
InvisibleLine = LineStyle("Invisible", rank=(9999, 9999), parent=NoLine, visible=False)

AsciiLine = LineStyle("Ascii", rank=(1, 0))
ThinLine = LineStyle("Thin", rank=(1, 4), parent=AsciiLine)
RoundedLine = LineStyle("Rounded", rank=(1, 5), parent=ThinLine)
ThinQuadrupleDashedLine = LineStyle("QuadDashed", (1, 1), parent=ThinLine)
ThinTripleDashedLine = LineStyle("TripleDashed", (1, 2), parent=ThinLine)
ThinDoubleDashedLine = LineStyle("DoubleDashed", (1, 3), parent=ThinLine)

UpperRightEighthLine = LineStyle("UpperRightEighthLine", (2, 1), parent=ThinLine)
LowerLeftEighthLine = LineStyle("LowerLeftEighthLine", (2, 1), parent=ThinLine)

AsciiThickLine = LineStyle("AsciiDouble", rank=(3, 0), parent=AsciiLine)
ThickLine = LineStyle("Thick", rank=(3, 4), parent=ThinLine)
DoubleLine = LineStyle("Double", (3, 5), parent=ThickLine)
ThickQuadrupleDashedLine = LineStyle("QuadDashed", (3, 1), parent=ThickLine)
ThickTripleDashedLine = LineStyle("TripleDashed", (3, 2), parent=ThickLine)
ThickDoubleDashedLine = LineStyle("DoubleDashed", (3, 3), parent=ThickLine)

UpperRightHalfLine = LineStyle("UpperRightHalfLine", (4, 1), parent=ThickLine)
LowerLeftHalfLine = LineStyle("LowerLeftHalfLine", (4, 1), parent=ThickLine)


class GridChar(NamedTuple):
    """Representation of a grid node character.

    The four compass points represent the line style joining from the given direction.
    """

    north: "LineStyle"
    east: "LineStyle"
    south: "LineStyle"
    west: "LineStyle"


# fmt: off
_GRID_CHARS = {
    # NONE
    GridChar(NoLine, NoLine, NoLine, NoLine): " ",
    # AsciiLine
    GridChar(AsciiLine, NoLine, AsciiLine, NoLine): "|",
    GridChar(NoLine, AsciiLine, NoLine, AsciiLine): "-",
    GridChar(AsciiLine, AsciiLine, NoLine, NoLine): "+",
    GridChar(NoLine, AsciiLine, AsciiLine, NoLine): "+",
    GridChar(NoLine, NoLine, AsciiLine, AsciiLine): "+",
    GridChar(AsciiLine, NoLine, NoLine, AsciiLine): "+",
    GridChar(AsciiLine, AsciiLine, AsciiLine, NoLine): "+",
    GridChar(NoLine, AsciiLine, AsciiLine, AsciiLine): "+",
    GridChar(AsciiLine, NoLine, AsciiLine, AsciiLine): "+",
    GridChar(AsciiLine, AsciiLine, NoLine, AsciiLine): "+",
    GridChar(AsciiLine, AsciiLine, AsciiLine, AsciiLine): "+",
    # AsciiThickLine
    GridChar(NoLine, AsciiThickLine, NoLine, AsciiThickLine): "=",
    # ThinLine
    GridChar(ThinLine, NoLine, NoLine, NoLine): "╵",
    GridChar(NoLine, ThinLine, NoLine, NoLine): "╶",
    GridChar(NoLine, NoLine, ThinLine, NoLine): "╷",
    GridChar(NoLine, NoLine, NoLine, ThinLine): "╴",
    GridChar(ThinLine, NoLine, ThinLine, NoLine): "│",
    GridChar(NoLine, ThinLine, NoLine, ThinLine): "─",
    GridChar(ThinLine, ThinLine, NoLine, NoLine): "└",
    GridChar(NoLine, ThinLine, ThinLine, NoLine): "┌",
    GridChar(NoLine, NoLine, ThinLine, ThinLine): "┐",
    GridChar(ThinLine, NoLine, NoLine, ThinLine): "┘",
    GridChar(ThinLine, ThinLine, ThinLine, NoLine): "├",
    GridChar(NoLine, ThinLine, ThinLine, ThinLine): "┬",
    GridChar(ThinLine, NoLine, ThinLine, ThinLine): "┤",
    GridChar(ThinLine, ThinLine, NoLine, ThinLine): "┴",
    GridChar(ThinLine, ThinLine, ThinLine, ThinLine): "┼",
    # Thin RoundedLine
    GridChar(RoundedLine, RoundedLine, NoLine, NoLine): "╰",
    GridChar(NoLine, RoundedLine, RoundedLine, NoLine): "╭",
    GridChar(NoLine, NoLine, RoundedLine, RoundedLine): "╮",
    GridChar(RoundedLine, NoLine, NoLine, RoundedLine): "╯",
    # Thin Dashes
    GridChar(NoLine, ThinDoubleDashedLine, NoLine, ThinDoubleDashedLine): "╌",
    GridChar(ThinDoubleDashedLine, NoLine, ThinDoubleDashedLine, NoLine): "╎",
    GridChar(NoLine, ThinTripleDashedLine, NoLine, ThinTripleDashedLine): "┄",
    GridChar(ThinTripleDashedLine, NoLine, ThinTripleDashedLine, NoLine): "┆",
    GridChar(NoLine, ThinQuadrupleDashedLine, NoLine, ThinQuadrupleDashedLine): "┈",
    GridChar(ThinQuadrupleDashedLine, NoLine, ThinQuadrupleDashedLine, NoLine): "┊",
    # Double
    GridChar(DoubleLine, NoLine, NoLine, NoLine): "║",
    GridChar(NoLine, DoubleLine, NoLine, NoLine): "═",
    GridChar(NoLine, NoLine, DoubleLine, NoLine): "║",
    GridChar(NoLine, NoLine, NoLine, DoubleLine): "═",
    GridChar(DoubleLine, NoLine, DoubleLine, NoLine): "║",
    GridChar(NoLine, DoubleLine, NoLine, DoubleLine): "═",
    GridChar(DoubleLine, DoubleLine, NoLine, NoLine): "╚",
    GridChar(NoLine, DoubleLine, DoubleLine, NoLine): "╔",
    GridChar(NoLine, NoLine, DoubleLine, DoubleLine): "╗",
    GridChar(DoubleLine, NoLine, NoLine, DoubleLine): "╝",
    GridChar(DoubleLine, DoubleLine, DoubleLine, NoLine): "╠",
    GridChar(NoLine, DoubleLine, DoubleLine, DoubleLine): "╦",
    GridChar(DoubleLine, NoLine, DoubleLine, DoubleLine): "╣",
    GridChar(DoubleLine, DoubleLine, NoLine, DoubleLine): "╩",
    GridChar(DoubleLine, DoubleLine, DoubleLine, DoubleLine): "╬",
    # Double / ThinLine
    GridChar(ThinLine, DoubleLine, ThinLine, DoubleLine): "╪",
    GridChar(DoubleLine, ThinLine, DoubleLine, ThinLine): "╫",
    GridChar(DoubleLine, ThinLine, NoLine, NoLine): "╙",
    GridChar(NoLine, DoubleLine, ThinLine, NoLine): "╒",
    GridChar(NoLine, NoLine, DoubleLine, ThinLine): "╖",
    GridChar(ThinLine, NoLine, NoLine, DoubleLine): "╛",
    GridChar(DoubleLine, NoLine, NoLine, ThinLine): "╜",
    GridChar(ThinLine, DoubleLine, NoLine, NoLine): "╘",
    GridChar(NoLine, ThinLine, DoubleLine, NoLine): "╓",
    GridChar(NoLine, NoLine, ThinLine, DoubleLine): "╕",
    GridChar(ThinLine, DoubleLine, ThinLine, NoLine): "╞",
    GridChar(NoLine, ThinLine, DoubleLine, ThinLine): "╥",
    GridChar(ThinLine, NoLine, ThinLine, DoubleLine): "╡",
    GridChar(DoubleLine, ThinLine, NoLine, ThinLine): "╨",
    GridChar(DoubleLine, ThinLine, DoubleLine, NoLine): "╟",
    GridChar(NoLine, DoubleLine, ThinLine, DoubleLine): "╤",
    GridChar(DoubleLine, NoLine, DoubleLine, ThinLine): "╢",
    GridChar(ThinLine, DoubleLine, NoLine, DoubleLine): "╧",
    # ThickLine
    GridChar(ThickLine, ThickLine, ThickLine, ThickLine): "╋",
    GridChar(ThickLine, NoLine, NoLine, NoLine): "╹",
    GridChar(NoLine, ThickLine, NoLine, NoLine): "╺",
    GridChar(NoLine, NoLine, ThickLine, NoLine): "╻",
    GridChar(NoLine, NoLine, NoLine, ThickLine): "╸",
    GridChar(ThickLine, NoLine, ThickLine, NoLine): "┃",
    GridChar(NoLine, ThickLine, NoLine, ThickLine): "━",
    GridChar(ThickLine, ThickLine, NoLine, NoLine): "┗",
    GridChar(NoLine, ThickLine, ThickLine, NoLine): "┏",
    GridChar(NoLine, ThickLine, ThickLine, NoLine): "┏",
    GridChar(NoLine, NoLine, ThickLine, ThickLine): "┓",
    GridChar(ThickLine, NoLine, NoLine, ThickLine): "┛",
    GridChar(ThickLine, ThickLine, ThickLine, NoLine): "┣",
    GridChar(NoLine, ThickLine, ThickLine, ThickLine): "┳",
    GridChar(ThickLine, NoLine, ThickLine, ThickLine): "┫",
    GridChar(ThickLine, ThickLine, NoLine, ThickLine): "┻",
    # ThickLine Dashes
    GridChar(NoLine, ThickDoubleDashedLine, NoLine, ThickDoubleDashedLine): "╍",
    GridChar(ThickDoubleDashedLine, NoLine, ThickDoubleDashedLine, NoLine): "╏",
    GridChar(NoLine, ThickTripleDashedLine, NoLine, ThickTripleDashedLine): "┅",
    GridChar(ThickTripleDashedLine, NoLine, ThickTripleDashedLine, NoLine): "┇",
    GridChar(NoLine, ThickQuadrupleDashedLine, NoLine, ThickQuadrupleDashedLine): "┉",
    GridChar(ThickQuadrupleDashedLine, NoLine, ThickQuadrupleDashedLine, NoLine): "┋",
    # ThickLine / ThinLine
    GridChar(NoLine,                ThickLine,              NoLine,                 ThinLine        ): "╼",
    GridChar(ThinLine,              NoLine,                 ThickLine,              NoLine          ): "╽",
    GridChar(NoLine,                ThinLine,               NoLine,                 ThickLine       ): "╾",
    GridChar(ThickLine,             NoLine,                 ThinLine,               NoLine          ): "╿",
    GridChar(ThickLine,             ThinLine,               NoLine,                 NoLine          ): "┖",
    GridChar(NoLine,                ThickLine,              ThinLine,               NoLine          ): "┍",
    GridChar(NoLine,                NoLine,                 ThickLine,              ThinLine        ): "┒",
    GridChar(ThinLine,              NoLine,                 NoLine,                 ThickLine       ): "┙",
    GridChar(ThickLine,             NoLine,                 NoLine,                 ThinLine        ): "┚",
    GridChar(ThinLine,              ThickLine,              NoLine,                 NoLine          ): "┕",
    GridChar(NoLine,                ThinLine,               ThickLine,              NoLine          ): "┎",
    GridChar(NoLine,                NoLine,                 ThinLine,               ThickLine       ): "┑",
    GridChar(ThickLine,             ThinLine,               ThinLine,               NoLine          ): "┞",
    GridChar(NoLine,                ThickLine,              ThinLine,               ThinLine        ): "┮",
    GridChar(ThinLine,              NoLine,                 ThickLine,              ThinLine        ): "┧",
    GridChar(ThinLine,              ThinLine,               NoLine,                 ThickLine       ): "┵",
    GridChar(ThickLine,             NoLine,                 ThinLine,               ThinLine        ): "┦",
    GridChar(ThinLine,              ThickLine,              NoLine,                 ThinLine        ): "┶",
    GridChar(ThinLine,              ThinLine,               ThickLine,              NoLine          ): "┟",
    GridChar(NoLine,                ThinLine,               ThinLine,               ThickLine       ): "┭",
    GridChar(ThickLine,             ThinLine,               NoLine,                 ThinLine        ): "┸",
    GridChar(ThinLine,              ThickLine,              ThinLine,               NoLine          ): "┝",
    GridChar(NoLine,                ThinLine,               ThickLine,              ThinLine        ): "┰",
    GridChar(ThinLine,              NoLine,                 ThinLine,               ThickLine       ): "┥",
    GridChar(ThickLine,             ThickLine,              ThinLine,               NoLine          ): "┡",
    GridChar(NoLine,                ThickLine,              ThickLine,              ThinLine        ): "┲",
    GridChar(ThinLine,              NoLine,                 ThickLine,              ThickLine       ): "┪",
    GridChar(ThickLine,             ThinLine,               NoLine,                 ThickLine       ): "┹",
    GridChar(ThickLine,             ThickLine,              NoLine,                 ThinLine        ): "┺",
    GridChar(ThinLine,              ThickLine,              ThickLine,              NoLine          ): "┢",
    GridChar(NoLine,                ThinLine,               ThickLine,              ThickLine       ): "┱",
    GridChar(ThickLine,             NoLine,                 ThinLine,               ThickLine       ): "┩",
    GridChar(ThickLine,             ThinLine,               ThickLine,              NoLine          ): "┠",
    GridChar(NoLine,                ThickLine,              ThinLine,               ThickLine       ): "┯",
    GridChar(ThickLine,             NoLine,                 ThickLine,              ThinLine        ): "┨",
    GridChar(ThinLine,              ThickLine,              NoLine,                 ThickLine       ): "┷",
    GridChar(ThickLine,             ThinLine,               ThinLine,               ThinLine        ): "╀",
    GridChar(ThinLine,              ThickLine,              ThinLine,               ThinLine        ): "┾",
    GridChar(ThinLine,              ThinLine,               ThickLine,              ThinLine        ): "╁",
    GridChar(ThinLine,              ThinLine,               ThinLine,               ThickLine       ): "┽",
    GridChar(ThickLine,             ThickLine,              ThinLine,               ThinLine        ): "╄",
    GridChar(ThinLine,              ThickLine,              ThickLine,              ThinLine        ): "╆",
    GridChar(ThinLine,              ThinLine,               ThickLine,              ThickLine       ): "╅",
    GridChar(ThickLine,             ThinLine,               ThinLine,               ThickLine       ): "╃",
    GridChar(ThinLine,              ThickLine,              ThinLine,               ThickLine       ): "┿",
    GridChar(ThickLine,             ThinLine,               ThickLine,              ThinLine        ): "╂",
    GridChar(ThickLine,             ThickLine,              ThickLine,              ThinLine        ): "╊",
    GridChar(ThinLine,              ThickLine,              ThickLine,              ThickLine       ): "╈",
    GridChar(ThickLine,             ThinLine,               ThickLine,              ThickLine       ): "╉",
    GridChar(ThickLine,             ThickLine,              ThinLine,               ThickLine       ): "╇",
    # UpperRightHalfLine
    GridChar(UpperRightHalfLine, NoLine, UpperRightHalfLine, NoLine): "▐",
    GridChar(NoLine, UpperRightHalfLine, NoLine, UpperRightHalfLine): "▀",
    GridChar(UpperRightHalfLine, UpperRightHalfLine, NoLine, NoLine): "▝",
    GridChar(NoLine, UpperRightHalfLine, UpperRightHalfLine, NoLine): "▐",
    GridChar(NoLine, NoLine, UpperRightHalfLine, UpperRightHalfLine): "▜",
    GridChar(UpperRightHalfLine, NoLine, NoLine, UpperRightHalfLine): "▀",
    GridChar(UpperRightHalfLine, UpperRightHalfLine, UpperRightHalfLine, NoLine): "▐",
    GridChar(NoLine, UpperRightHalfLine, UpperRightHalfLine, UpperRightHalfLine): "▜",
    GridChar(UpperRightHalfLine, NoLine, UpperRightHalfLine, UpperRightHalfLine): "▜",
    GridChar(UpperRightHalfLine, UpperRightHalfLine, NoLine, UpperRightHalfLine): "▀",
    GridChar(UpperRightHalfLine, UpperRightHalfLine, UpperRightHalfLine, UpperRightHalfLine): "▜",
    # LowerLeftHalfLine
    GridChar(LowerLeftHalfLine, NoLine, LowerLeftHalfLine, NoLine): "▌",
    GridChar(NoLine, LowerLeftHalfLine, NoLine, LowerLeftHalfLine): "▄",
    GridChar(LowerLeftHalfLine, LowerLeftHalfLine, NoLine, NoLine): "▙",
    GridChar(NoLine, LowerLeftHalfLine, LowerLeftHalfLine, NoLine): "▄",
    GridChar(NoLine, NoLine, LowerLeftHalfLine, LowerLeftHalfLine): "▖",
    GridChar(LowerLeftHalfLine, NoLine, NoLine, LowerLeftHalfLine): "▌",
    GridChar(LowerLeftHalfLine, LowerLeftHalfLine, LowerLeftHalfLine, NoLine): "▙",
    GridChar(NoLine, LowerLeftHalfLine, LowerLeftHalfLine, LowerLeftHalfLine): "▄",
    GridChar(LowerLeftHalfLine, NoLine, LowerLeftHalfLine, LowerLeftHalfLine): "▌",
    GridChar(LowerLeftHalfLine, LowerLeftHalfLine, NoLine, LowerLeftHalfLine): "▙",
    GridChar(LowerLeftHalfLine, LowerLeftHalfLine, LowerLeftHalfLine, LowerLeftHalfLine): "▙",
    # Half Combos
    GridChar(NoLine, UpperRightHalfLine, LowerLeftHalfLine, NoLine): "▛",
    GridChar(UpperRightHalfLine, NoLine, NoLine, LowerLeftHalfLine): "▟",
    GridChar(LowerLeftHalfLine, NoLine, NoLine, UpperRightHalfLine): "▘",
    GridChar(NoLine, LowerLeftHalfLine, UpperRightHalfLine, NoLine): "▗",
    # Half/ThinLine combos
    GridChar(LowerLeftHalfLine, ThinLine, LowerLeftHalfLine, NoLine): "▌",
    GridChar(NoLine, LowerLeftHalfLine, ThinLine, LowerLeftHalfLine): "▄",
    GridChar(LowerLeftHalfLine, NoLine, LowerLeftHalfLine, ThinLine): "▌",
    GridChar(ThinLine, LowerLeftHalfLine, NoLine, LowerLeftHalfLine): "▄",
    GridChar(UpperRightHalfLine, ThinLine, UpperRightHalfLine, NoLine): "▐",
    GridChar(NoLine, UpperRightHalfLine, ThinLine, UpperRightHalfLine): "▀",
    GridChar(UpperRightHalfLine, NoLine, UpperRightHalfLine, ThinLine): "▐",
    GridChar(ThinLine, UpperRightHalfLine, NoLine, UpperRightHalfLine): "▀",
    # UpperRightEighthLine
    GridChar(UpperRightEighthLine, NoLine, UpperRightEighthLine, NoLine): "▕",
    GridChar(NoLine, UpperRightEighthLine, NoLine, UpperRightEighthLine): "▔",
    GridChar(UpperRightEighthLine, UpperRightEighthLine, NoLine, NoLine): " ",
    GridChar(NoLine, UpperRightEighthLine, UpperRightEighthLine, NoLine): "▕",
    GridChar(NoLine, NoLine, UpperRightEighthLine, UpperRightEighthLine): "▕",
    GridChar(UpperRightEighthLine, NoLine, NoLine, UpperRightEighthLine): "▔",
    GridChar(UpperRightEighthLine, UpperRightEighthLine, UpperRightEighthLine, NoLine): "▕",
    GridChar(NoLine, UpperRightEighthLine, UpperRightEighthLine, UpperRightEighthLine): "▔",
    GridChar(UpperRightEighthLine,  NoLine,                 UpperRightEighthLine,   UpperRightEighthLine): "▕",
    GridChar(UpperRightEighthLine,  UpperRightEighthLine,   NoLine,                 UpperRightEighthLine): "▔",
    GridChar(UpperRightEighthLine,  UpperRightEighthLine,   UpperRightEighthLine,   UpperRightEighthLine): "▕",
    # LowerLeftEighthLine
    GridChar(LowerLeftEighthLine,   NoLine,                 LowerLeftEighthLine,    NoLine              ): "▏",
    GridChar(NoLine,                LowerLeftEighthLine,    NoLine,                 LowerLeftEighthLine ): "▁",
    GridChar(LowerLeftEighthLine,   LowerLeftEighthLine,    NoLine,                 NoLine              ): "▏",
    GridChar(NoLine,                LowerLeftEighthLine,    LowerLeftEighthLine,    NoLine              ): "▁",
    GridChar(NoLine,                NoLine,                 LowerLeftEighthLine,    LowerLeftEighthLine ): " ",
    GridChar(LowerLeftEighthLine,   NoLine,                 NoLine,                 LowerLeftEighthLine ): "▏",
    GridChar(LowerLeftEighthLine,   LowerLeftEighthLine,    LowerLeftEighthLine,    NoLine              ): "▏",
    GridChar(NoLine,                LowerLeftEighthLine,    LowerLeftEighthLine,    LowerLeftEighthLine ): "▁",
    GridChar(LowerLeftEighthLine,   NoLine,                 LowerLeftEighthLine,    LowerLeftEighthLine ): "▏",
    GridChar(LowerLeftEighthLine,   LowerLeftEighthLine,    NoLine,                 LowerLeftEighthLine ): "▁",
    GridChar(LowerLeftEighthLine,   LowerLeftEighthLine,    LowerLeftEighthLine,    LowerLeftEighthLine ): "▏",
    # Eighth Combos
    GridChar(NoLine,                LowerLeftEighthLine,    UpperRightEighthLine,   NoLine              ): " ",
    GridChar(LowerLeftEighthLine,   NoLine,                 NoLine,                 UpperRightEighthLine): " ",
    # Eighth/ThinLine combos
    GridChar(LowerLeftEighthLine,   ThinLine,               LowerLeftEighthLine,    NoLine              ): "▏",
    GridChar(NoLine,                LowerLeftEighthLine,    ThinLine,               LowerLeftEighthLine ): "▁",
    GridChar(LowerLeftEighthLine,   NoLine,                 LowerLeftEighthLine,    ThinLine            ): "▏",
    GridChar(ThinLine,              LowerLeftEighthLine,    NoLine,                 LowerLeftEighthLine ): "▁",
    GridChar(UpperRightEighthLine,  ThinLine,               UpperRightEighthLine,   NoLine              ): "▕",
    GridChar(NoLine,                UpperRightEighthLine,   ThinLine,               UpperRightEighthLine): "▔",
    GridChar(UpperRightEighthLine,  NoLine,                 UpperRightEighthLine,   ThinLine            ): "▕",
    GridChar(ThinLine,              UpperRightEighthLine,   NoLine,                 UpperRightEighthLine): "▔",
    GridChar(NoLine,                NoLine,                 UpperRightEighthLine,   LowerLeftEighthLine ): "▁",
    GridChar(LowerLeftEighthLine,   UpperRightEighthLine,   NoLine,                 NoLine              ): "▔",
}
# fmt: off

@lru_cache
def grid_char(key: "GridChar") -> "str":
    """Return the character represented by a combination of :class:`LineStyles`."""
    if key in _GRID_CHARS:
        return _GRID_CHARS[key]
    else:
        # If there is no matching character representation, replace the line style
        # whose parent has the highest ranking with the parent style until a character
        # is found
        m_key = list(key)
        while any(x.parent for x in m_key):
            parent_ranks = {(9999,) if line.parent == NoLine else line.parent.rank: i for i, line in enumerate(m_key) if line.parent}
            idx = parent_ranks[max(parent_ranks)]
            if parent := m_key[idx].parent:
                m_key[idx] = parent
                char = _GRID_CHARS.get(GridChar(*m_key))
                if char:
                    return char
        # If all else fails, return a space
        else:
            return " "


class GridStyle:
    """A collection of characters which can be used to draw a grid."""

    class _BorderLineChars(NamedTuple):
        LEFT: "str"
        MID: "str"
        SPLIT: "str"
        RIGHT: "str"

    def __init__(
        self, line_style: "LineStyle" = InvisibleLine, mask: "Mask" = Masks.grid
    ) -> "None":
        """Creates a new :py:class:`GridStyle` instance.

        Args:
            line_style: The line style to use to construct the grid
            mask: A mask which can be used to exclude certain character from the grid
        """
        self.grid = {
            part: GridChar(
                *((line_style if x else NoLine) for x in mask.mask[part])
            )
            for part in GridPart
        }
        self.mask = mask

    @property
    def TOP(self) -> "_BorderLineChars":
        """Allow dotted attribute access to the top grid row."""
        return self._BorderLineChars(
            grid_char(self.grid[GridPart.TOP_LEFT]),
            grid_char(self.grid[GridPart.TOP_MID]),
            grid_char(self.grid[GridPart.TOP_SPLIT]),
            grid_char(self.grid[GridPart.TOP_RIGHT]),
        )

    @property
    def MID(self) -> "_BorderLineChars":
        """Allow dotted attribute access to the mid grid row."""
        return self._BorderLineChars(
            grid_char(self.grid[GridPart.MID_LEFT]),
            grid_char(self.grid[GridPart.MID_MID]),
            grid_char(self.grid[GridPart.MID_SPLIT]),
            grid_char(self.grid[GridPart.MID_RIGHT]),
        )

    @property
    def SPLIT(self) -> "_BorderLineChars":
        """Allow dotted attribute access to the split grid row."""
        return self._BorderLineChars(
            grid_char(self.grid[GridPart.SPLIT_LEFT]),
            grid_char(self.grid[GridPart.SPLIT_MID]),
            grid_char(self.grid[GridPart.SPLIT_SPLIT]),
            grid_char(self.grid[GridPart.SPLIT_RIGHT]),
        )

    @property
    def BOTTOM(self) -> "_BorderLineChars":
        """Allow dotted attribute access to the bottom grid row."""
        return self._BorderLineChars(
            grid_char(self.grid[GridPart.BOTTOM_LEFT]),
            grid_char(self.grid[GridPart.BOTTOM_MID]),
            grid_char(self.grid[GridPart.BOTTOM_SPLIT]),
            grid_char(self.grid[GridPart.BOTTOM_RIGHT]),
        )

    @property
    def HORIZONTAL(self) -> "str":
        """For compatibility with :class:`prompt_toolkit.widgets.base.Border`."""
        return self.SPLIT_MID

    @property
    def VERTICAL(self) -> "str":
        """For compatibility with :class:`prompt_toolkit.widgets.base.Border`."""
        return self.MID_SPLIT

    def __getattr__(self, value: "str") -> "str":
        """Allows the parts of the grid to be accessed as attributes by name."""
        key = getattr(GridPart, value)
        return grid_char(self.grid[key])

    def __dir__(self) -> "list":
        """List the public attributes of the grid style."""
        return [x.name for x in GridPart] + ["TOP", "MID", "SPLIT", "BOTTOM"]

    def __add__(self, other: "GridStyle") -> "GridStyle":
        """Combine two grid styles."""
        grid_style = GridStyle()
        grid_style.grid = {}
        for part in GridPart:
            grid_style.grid[part] = GridChar(
                *(max(self.grid[part][i], other.grid[part][i]) for i in range(4))
            )
        return grid_style

    def __repr__(self) -> "str":
        """Returns a string representation of the grid style."""
        return "\n".join(
            "".join(
                grid_char(char_key)
                for char_key in list(self.grid.values())[i * 4 : (i + 1) * 4]
            )
            for i in range(4)
        )


ThinGrid = ThinLine.grid

InnerEigthGrid = (
    LowerLeftEighthLine.top_edge
    + LowerLeftEighthLine.right_edge
    + UpperRightEighthLine.left_edge
    + UpperRightEighthLine.bottom_edge
    + ThinLine.inner
)

OuterEigthGrid = (
    LowerLeftEighthLine.top_edge
    + UpperRightEighthLine.right_edge
    + UpperRightEighthLine.bottom_edge
    + LowerLeftEighthLine.left_edge
    + ThinLine.inner
)

OuterHalfGrid = (
    UpperRightHalfLine.top_edge
    + UpperRightHalfLine.right_edge
    + LowerLeftHalfLine.left_edge
    + LowerLeftHalfLine.bottom_edge
    + ThinLine.inner
)

InnerHalfGrid = (
    LowerLeftHalfLine.top_edge
    + LowerLeftHalfLine.right_edge
    + UpperRightHalfLine.left_edge
    + UpperRightHalfLine.bottom_edge
    + ThinLine.inner
)


class DiLineStyle(NamedTuple):
    """A description of a cell border: a :class:`LineStyle` for each edge."""

    top: "LineStyle" = NoLine
    right: "LineStyle" = NoLine
    bottom: "LineStyle" = NoLine
    left: "LineStyle" = NoLine

    @classmethod
    def from_value(cls, value: "LineStyle") -> "DiLineStyle":
        """Construct an instance from a single value."""
        return cls(top=value, right=value, bottom=value, left=value)
