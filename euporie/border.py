"""Defines border styles."""

from enum import Enum
from functools import total_ordering
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from typing import Dict, List, Optional

__all__ = [
    "Invisible",
    "Ascii",
    "AsciiThick",
    "Thin",
    "ThinDoubleDashed",
    "ThinTripleDashed",
    "ThinQuadrupleDashed",
    "Rounded",
    "Thick",
    "ThinDoubleDashed",
    "ThinTripleDashed",
    "ThinQuadrupleDashed",
    "Double",
    "grid_char",
]


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
    north: "bool" = False
    east: "bool" = False
    south: "bool" = False
    west: "bool" = False


class Mask:
    """A mask which allows selection of a subset of a grid.

    Masks can be combined to construct more complex masks.
    """

    def __init__(self, mask: "Dict[GridPart, DirectionFlags]") -> "None":
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
        self, name: "str", rank: "int", parent: "Optional[LineStyle]" = None
    ) -> "None":
        """Creates a new :class:`LineStyle`.

        Args:
            name: The name of the line style
            rank: A ranking value - this is used when two adjoining cells in a table
                have differing line styles to determine which should take precedence.
                The style with the higher rank is used.
            parent: The :class:`LineStyle` from which this style should inherit if any
                characters are undefined.

        """
        self.name = name
        self.rank = rank
        self.children: "Dict[str, LineStyle]" = {}
        self.parent = parent
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

    def __dir__(self) -> "List[str]":
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
Invisible = LineStyle("Invisible", rank=0)
Ascii = LineStyle("Ascii", rank=10)
AsciiThick = LineStyle("AsciiDouble", rank=11, parent=Ascii)
Thin = LineStyle("Thin", rank=20, parent=Ascii)
Thick = LineStyle("Thick", rank=30, parent=Ascii)
Rounded = LineStyle("Rounded", rank=40, parent=Thin)
ThinDoubleDashed = LineStyle("DoubleDashed", 51, parent=Thin)
ThinTripleDashed = LineStyle("TripleDashed", 52, parent=Thin)
ThinQuadrupleDashed = LineStyle("QuadDashed", 53, parent=Thin)
ThickDoubleDashed = LineStyle("DoubleDashed", 54, parent=Thick)
ThickTripleDashed = LineStyle("TripleDashed", 35, parent=Thick)
ThickQuadrupleDashed = LineStyle("QuadDashed", 56, parent=Thick)
Double = LineStyle("Double", 50, parent=Thick)
HalfBlockUpperRight = LineStyle("HalfBlockUpperRight", 50, parent=Thin)
HalfBlockLowerLeft = LineStyle("HalfBlockLowerLeft", 50, parent=Thin)


class GridChar(NamedTuple):
    north: "LineStyle"
    east: "LineStyle"
    south: "LineStyle"
    west: "LineStyle"


_GRID_CHARS = {
    # NONE
    GridChar(Invisible, Invisible, Invisible, Invisible): " ",
    # Ascii
    GridChar(Ascii, Invisible, Ascii, Invisible): "|",
    GridChar(Invisible, Ascii, Invisible, Ascii): "-",
    GridChar(Ascii, Ascii, Invisible, Invisible): "+",
    GridChar(Invisible, Ascii, Ascii, Invisible): "+",
    GridChar(Invisible, Invisible, Ascii, Ascii): "+",
    GridChar(Ascii, Invisible, Invisible, Ascii): "+",
    GridChar(Ascii, Ascii, Ascii, Invisible): "+",
    GridChar(Invisible, Ascii, Ascii, Ascii): "+",
    GridChar(Ascii, Invisible, Ascii, Ascii): "+",
    GridChar(Ascii, Ascii, Invisible, Ascii): "+",
    GridChar(Ascii, Ascii, Ascii, Ascii): "+",
    # AsciiThick
    GridChar(Invisible, AsciiThick, Invisible, AsciiThick): "=",
    # Thin
    GridChar(Thin, Invisible, Invisible, Invisible): "╵",
    GridChar(Invisible, Thin, Invisible, Invisible): "╶",
    GridChar(Invisible, Invisible, Thin, Invisible): "╷",
    GridChar(Invisible, Invisible, Invisible, Thin): "╴",
    GridChar(Thin, Invisible, Thin, Invisible): "│",
    GridChar(Invisible, Thin, Invisible, Thin): "─",
    GridChar(Thin, Thin, Invisible, Invisible): "└",
    GridChar(Invisible, Thin, Thin, Invisible): "┌",
    GridChar(Invisible, Invisible, Thin, Thin): "┐",
    GridChar(Thin, Invisible, Invisible, Thin): "┘",
    GridChar(Thin, Thin, Thin, Invisible): "├",
    GridChar(Invisible, Thin, Thin, Thin): "┬",
    GridChar(Thin, Invisible, Thin, Thin): "┤",
    GridChar(Thin, Thin, Invisible, Thin): "┴",
    GridChar(Thin, Thin, Thin, Thin): "┼",
    # Thin Rounded
    GridChar(Rounded, Rounded, Invisible, Invisible): "╰",
    GridChar(Invisible, Rounded, Rounded, Invisible): "╭",
    GridChar(Invisible, Invisible, Rounded, Rounded): "╮",
    GridChar(Rounded, Invisible, Invisible, Rounded): "╯",
    # Thin Dashes
    GridChar(Invisible, ThinDoubleDashed, Invisible, ThinDoubleDashed): "╌",
    GridChar(ThinDoubleDashed, Invisible, ThinDoubleDashed, Invisible): "╎",
    GridChar(Invisible, ThinTripleDashed, Invisible, ThinTripleDashed): "┄",
    GridChar(ThinTripleDashed, Invisible, ThinTripleDashed, Invisible): "┆",
    GridChar(Invisible, ThinQuadrupleDashed, Invisible, ThinQuadrupleDashed): "┈",
    GridChar(ThinQuadrupleDashed, Invisible, ThinQuadrupleDashed, Invisible): "┊",
    # Double
    GridChar(Double, Invisible, Invisible, Invisible): "║",
    GridChar(Invisible, Double, Invisible, Invisible): "═",
    GridChar(Invisible, Invisible, Double, Invisible): "║",
    GridChar(Invisible, Invisible, Invisible, Double): "═",
    GridChar(Double, Invisible, Double, Invisible): "║",
    GridChar(Invisible, Double, Invisible, Double): "═",
    GridChar(Double, Double, Invisible, Invisible): "╚",
    GridChar(Invisible, Double, Double, Invisible): "╔",
    GridChar(Invisible, Invisible, Double, Double): "╗",
    GridChar(Double, Invisible, Invisible, Double): "╝",
    GridChar(Double, Double, Double, Invisible): "╠",
    GridChar(Invisible, Double, Double, Double): "╦",
    GridChar(Double, Invisible, Double, Double): "╣",
    GridChar(Double, Double, Invisible, Double): "╩",
    GridChar(Double, Double, Double, Double): "╬",
    # Double / Thin
    GridChar(Thin, Double, Thin, Double): "╪",
    GridChar(Double, Thin, Double, Thin): "╫",
    GridChar(Double, Thin, Invisible, Invisible): "╙",
    GridChar(Invisible, Double, Thin, Invisible): "╒",
    GridChar(Invisible, Invisible, Double, Thin): "╖",
    GridChar(Thin, Invisible, Invisible, Double): "╛",
    GridChar(Double, Invisible, Invisible, Thin): "╜",
    GridChar(Thin, Double, Invisible, Invisible): "╘",
    GridChar(Invisible, Thin, Double, Invisible): "╓",
    GridChar(Invisible, Invisible, Thin, Double): "╕",
    GridChar(Thin, Double, Thin, Invisible): "╞",
    GridChar(Invisible, Thin, Double, Thin): "╥",
    GridChar(Thin, Invisible, Thin, Double): "╡",
    GridChar(Double, Thin, Invisible, Thin): "╨",
    GridChar(Double, Thin, Double, Invisible): "╟",
    GridChar(Invisible, Double, Thin, Double): "╤",
    GridChar(Double, Invisible, Double, Thin): "╢",
    GridChar(Thin, Double, Invisible, Double): "╧",
    # Thick
    GridChar(Thick, Thick, Thick, Thick): "╋",
    GridChar(Thick, Invisible, Invisible, Invisible): "╹",
    GridChar(Invisible, Thick, Invisible, Invisible): "╺",
    GridChar(Invisible, Invisible, Thick, Invisible): "╻",
    GridChar(Invisible, Invisible, Invisible, Thick): "╸",
    GridChar(Thick, Invisible, Thick, Invisible): "┃",
    GridChar(Invisible, Thick, Invisible, Thick): "━",
    GridChar(Thick, Thick, Invisible, Invisible): "┗",
    GridChar(Invisible, Thick, Thick, Invisible): "┏",
    GridChar(Invisible, Invisible, Thick, Thick): "┓",
    GridChar(Thick, Invisible, Invisible, Thick): "┛",
    GridChar(Thick, Thick, Thick, Invisible): "┣",
    GridChar(Invisible, Thick, Thick, Thick): "┳",
    GridChar(Thick, Invisible, Thick, Thick): "┫",
    GridChar(Thick, Thick, Invisible, Thick): "┻",
    # Thick Dashes
    GridChar(Invisible, ThickDoubleDashed, Invisible, ThickDoubleDashed): "╍",
    GridChar(ThickDoubleDashed, Invisible, ThickDoubleDashed, Invisible): "╏",
    GridChar(Invisible, ThickTripleDashed, Invisible, ThickTripleDashed): "┅",
    GridChar(ThickTripleDashed, Invisible, ThickTripleDashed, Invisible): "┇",
    GridChar(Invisible, ThickQuadrupleDashed, Invisible, ThickQuadrupleDashed): "┉",
    GridChar(ThickQuadrupleDashed, Invisible, ThickQuadrupleDashed, Invisible): "┋",
    # Thick / Thin
    GridChar(Invisible, Thick, Invisible, Thin): "╼",
    GridChar(Thin, Invisible, Thick, Invisible): "╽",
    GridChar(Invisible, Thin, Invisible, Thick): "╾",
    GridChar(Thick, Invisible, Thin, Invisible): "╿",
    GridChar(Thick, Thin, Invisible, Invisible): "┖",
    GridChar(Invisible, Thick, Thin, Invisible): "┍",
    GridChar(Invisible, Invisible, Thick, Thin): "┒",
    GridChar(Thin, Invisible, Invisible, Thick): "┙",
    GridChar(Thick, Invisible, Invisible, Thin): "┚",
    GridChar(Thin, Thick, Invisible, Invisible): "┕",
    GridChar(Invisible, Thin, Thick, Invisible): "┎",
    GridChar(Invisible, Invisible, Thin, Thick): "┑",
    GridChar(Thick, Thin, Thin, Invisible): "┞",
    GridChar(Invisible, Thick, Thin, Thin): "┮",
    GridChar(Thin, Invisible, Thick, Thin): "┧",
    GridChar(Thin, Thin, Invisible, Thick): "┵",
    GridChar(Thick, Invisible, Thin, Thin): "┦",
    GridChar(Thin, Thick, Invisible, Thin): "┶",
    GridChar(Thin, Thin, Thick, Invisible): "┟",
    GridChar(Invisible, Thin, Thin, Thick): "┭",
    GridChar(Thick, Thin, Invisible, Thin): "┸",
    GridChar(Thin, Thick, Thin, Invisible): "┝",
    GridChar(Invisible, Thin, Thick, Thin): "┰",
    GridChar(Thin, Invisible, Thin, Thick): "┥",
    GridChar(Thick, Thick, Thin, Invisible): "┡",
    GridChar(Invisible, Thick, Thick, Thin): "┲",
    GridChar(Thin, Invisible, Thick, Thick): "┪",
    GridChar(Thick, Thin, Invisible, Thick): "┹",
    GridChar(Thick, Thick, Invisible, Thin): "┺",
    GridChar(Thin, Thick, Thick, Invisible): "┢",
    GridChar(Invisible, Thin, Thick, Thick): "┱",
    GridChar(Thick, Invisible, Thin, Thick): "┩",
    GridChar(Thick, Thin, Thick, Invisible): "┠",
    GridChar(Invisible, Thick, Thin, Thick): "┯",
    GridChar(Thick, Invisible, Thick, Thin): "┨",
    GridChar(Thin, Thick, Invisible, Thick): "┷",
    GridChar(Thick, Thin, Thin, Thin): "╀",
    GridChar(Thin, Thick, Thin, Thin): "┾",
    GridChar(Thin, Thin, Thick, Thin): "╁",
    GridChar(Thin, Thin, Thin, Thick): "┽",
    GridChar(Thick, Thick, Thin, Thin): "╄",
    GridChar(Thin, Thick, Thick, Thin): "╆",
    GridChar(Thin, Thin, Thick, Thick): "╅",
    GridChar(Thick, Thin, Thin, Thick): "╃",
    GridChar(Thin, Thick, Thin, Thick): "┿",
    GridChar(Thick, Thin, Thick, Thin): "╂",
    GridChar(Thick, Thick, Thick, Thin): "╊",
    GridChar(Thin, Thick, Thick, Thick): "╈",
    GridChar(Thick, Thin, Thick, Thick): "╉",
    GridChar(Thick, Thick, Thin, Thick): "╇",
    # HalfBlockUpperRight
    GridChar(HalfBlockUpperRight, Invisible, HalfBlockUpperRight, Invisible): "▐",
    GridChar(Invisible, HalfBlockUpperRight, Invisible, HalfBlockUpperRight): "▀",
    GridChar(HalfBlockUpperRight, HalfBlockUpperRight, Invisible, Invisible): "▝",
    GridChar(Invisible, HalfBlockUpperRight, HalfBlockUpperRight, Invisible): "▐",
    GridChar(Invisible, Invisible, HalfBlockUpperRight, HalfBlockUpperRight): "▜",
    GridChar(HalfBlockUpperRight, Invisible, Invisible, HalfBlockUpperRight): "▀",
    GridChar(
        HalfBlockUpperRight, HalfBlockUpperRight, HalfBlockUpperRight, Invisible
    ): "▐",
    GridChar(
        Invisible, HalfBlockUpperRight, HalfBlockUpperRight, HalfBlockUpperRight
    ): "▜",
    GridChar(
        HalfBlockUpperRight, Invisible, HalfBlockUpperRight, HalfBlockUpperRight
    ): "▜",
    GridChar(
        HalfBlockUpperRight, HalfBlockUpperRight, Invisible, HalfBlockUpperRight
    ): "▀",
    GridChar(
        HalfBlockUpperRight,
        HalfBlockUpperRight,
        HalfBlockUpperRight,
        HalfBlockUpperRight,
    ): "▜",
    # HalfBlockLowerLeft
    GridChar(HalfBlockLowerLeft, Invisible, HalfBlockLowerLeft, Invisible): "▌",
    GridChar(Invisible, HalfBlockLowerLeft, Invisible, HalfBlockLowerLeft): "▄",
    GridChar(HalfBlockLowerLeft, HalfBlockLowerLeft, Invisible, Invisible): "▙",
    GridChar(Invisible, HalfBlockLowerLeft, HalfBlockLowerLeft, Invisible): "▄",
    GridChar(Invisible, Invisible, HalfBlockLowerLeft, HalfBlockLowerLeft): "▖",
    GridChar(HalfBlockLowerLeft, Invisible, Invisible, HalfBlockLowerLeft): "▌",
    GridChar(
        HalfBlockLowerLeft, HalfBlockLowerLeft, HalfBlockLowerLeft, Invisible
    ): "▙",
    GridChar(
        Invisible, HalfBlockLowerLeft, HalfBlockLowerLeft, HalfBlockLowerLeft
    ): "▄",
    GridChar(
        HalfBlockLowerLeft, Invisible, HalfBlockLowerLeft, HalfBlockLowerLeft
    ): "▌",
    GridChar(
        HalfBlockLowerLeft, HalfBlockLowerLeft, Invisible, HalfBlockLowerLeft
    ): "▙",
    GridChar(
        HalfBlockLowerLeft, HalfBlockLowerLeft, HalfBlockLowerLeft, HalfBlockLowerLeft
    ): "▙",
    # HalfBlock Combos
    GridChar(Invisible, HalfBlockUpperRight, HalfBlockLowerLeft, Invisible): "▛",
    GridChar(HalfBlockUpperRight, Invisible, Invisible, HalfBlockLowerLeft): "▟",
    # Halfblock/Thin combos
    GridChar(HalfBlockLowerLeft, Thin, HalfBlockLowerLeft, Invisible): "▌",
    GridChar(Invisible, HalfBlockLowerLeft, Thin, HalfBlockLowerLeft): "▄",
    GridChar(HalfBlockLowerLeft, Invisible, HalfBlockLowerLeft, Thin): "▌",
    GridChar(Thin, HalfBlockLowerLeft, Invisible, HalfBlockLowerLeft): "▄",
    GridChar(HalfBlockUpperRight, Thin, HalfBlockUpperRight, Invisible): "▐",
    GridChar(Invisible, HalfBlockUpperRight, Thin, HalfBlockUpperRight): "▀",
    GridChar(HalfBlockUpperRight, Invisible, HalfBlockUpperRight, Thin): "▐",
    GridChar(Thin, HalfBlockUpperRight, Invisible, HalfBlockUpperRight): "▀",
}


def grid_char(key: "GridChar") -> "str":
    """Return the character represented by a combination of :class:`LineStyles`."""
    if key in _GRID_CHARS:
        return _GRID_CHARS[key]
    else:
        # If there is not matching character representation, replacing each line style
        # with its parent style in turn and using the result until a matching character
        # is found
        m_key = list(key)
        while any(x.parent for x in m_key):
            for part in sorted(
                {x for x in m_key if x.parent}, key=lambda x: x.rank, reverse=True
            ):
                m_key = [
                    (part.parent or x) if x is part and x.parent else x for x in m_key
                ]
                char = _GRID_CHARS.get(GridChar(*m_key))
                if char:
                    return char
        # If all else fails, return a space
        else:
            return " "


class GridStyle:
    class _BorderLineChars(NamedTuple):
        LEFT: "str"
        MID: "str"
        SPLIT: "str"
        RIGHT: "str"

    def __init__(self, line_style: "LineStyle" = Invisible, mask: "Mask" = Masks.grid):
        self.grid = {
            part: GridChar(*((line_style if x else Invisible) for x in mask.mask[part]))
            for part in GridPart
        }

    @property
    def TOP(self) -> "_BorderLineChars":
        return self._BorderLineChars(
            grid_char(self.grid[GridPart.TOP_LEFT]),
            grid_char(self.grid[GridPart.TOP_MID]),
            grid_char(self.grid[GridPart.TOP_SPLIT]),
            grid_char(self.grid[GridPart.TOP_RIGHT]),
        )

    @property
    def MID(self) -> "_BorderLineChars":
        return self._BorderLineChars(
            grid_char(self.grid[GridPart.MID_LEFT]),
            grid_char(self.grid[GridPart.MID_MID]),
            grid_char(self.grid[GridPart.MID_SPLIT]),
            grid_char(self.grid[GridPart.MID_RIGHT]),
        )

    @property
    def SPLIT(self) -> "_BorderLineChars":
        return self._BorderLineChars(
            grid_char(self.grid[GridPart.SPLIT_LEFT]),
            grid_char(self.grid[GridPart.SPLIT_MID]),
            grid_char(self.grid[GridPart.SPLIT_SPLIT]),
            grid_char(self.grid[GridPart.SPLIT_RIGHT]),
        )

    @property
    def BOTTOM(self) -> "_BorderLineChars":
        return self._BorderLineChars(
            grid_char(self.grid[GridPart.BOTTOM_LEFT]),
            grid_char(self.grid[GridPart.BOTTOM_MID]),
            grid_char(self.grid[GridPart.BOTTOM_SPLIT]),
            grid_char(self.grid[GridPart.BOTTOM_RIGHT]),
        )

    # For compatibility with :class:`prompt_toolkit.widgets.base.Border`
    @property
    def HORIZONTAL(self) -> "str":
        return self.SPLIT_MID

    @property
    def VERTICAL(self) -> "str":
        return self.MID_SPLIT

    def __getattr__(self, value: "str") -> "str":
        """Allows the parts of the grid to be accessed as attributes by name."""
        key = getattr(GridPart, value)
        return grid_char(self.grid[key])

    def __dir__(self) -> "List":
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
